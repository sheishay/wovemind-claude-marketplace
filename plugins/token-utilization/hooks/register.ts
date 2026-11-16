import type { Hook, PromptOrigin, Register } from 'claude-code'

type $ = Parameters<Hook<'turn.start'>>[0]
type Kind = 'five_hour' | 'seven_day'
type Limit = { kind: Kind; percent: number }
type Reading = { kind: string; percentUsed: number }
// Per session, in the store, so a reload keeps it.
type State = {
  limits: Limit[]
  mode: 'immediate' | 'wrap-up'
  phase: 'armed' | 'wrapping' | 'stopped'
  ceiling?: Limit // the window that tripped, at percent + 5 (max 100); cleared when it fires
  wrapTurnId?: string // the main turn whose final message is the handoff
  inject?: string // main-agent wrap-up text, attached to the main loop's next tool result
  warned?: boolean // the "no reading" warning was written
  stoppedIds?: string[] // subagents this mod stopped: their notifications are dropped
  messagedIds?: string[] // subagents sent the wrap-up text: their reports pass
}

const NAME: Record<Kind, string> = { five_hour: 'session', seven_day: 'weekly' }
const TOKEN = String.raw`(?<![\w./-])\/(session|weekly)-token-utilization(?![\w-])`
// "until /session-token-utilization gets to 90%": "until" through the percentage.
const CLAUSE = new RegExp(String.raw`(?:\buntil\s+)?${TOKEN}(?:[^\n/%]*?(\d+(?:\.\d+)?)\s*%)?`, 'gi')
const FORM = 'token-utilization: name a percentage from 1 to 100, e.g. "until /session-token-utilization gets to 90%". Prompt not sent.'
const IMMEDIATE = 'Stop immediately'
const WRAP = 'Wrap up first'
const YES = 'Yes, run it'
const ACTIVE = ['pending', 'running', 'waiting']

function parse(text: string) {
  const limits: Limit[] = []
  let bad = false
  const marked = text.replace(CLAUSE, (_m, window: string, n?: string) => {
    const percent = Number(n)
    if (!n || !(percent >= 1 && percent <= 100)) bad = true
    limits.push({ kind: window.toLowerCase() === 'session' ? 'five_hour' : 'seven_day', percent })
    return '\0'
  })
  const rest = marked
    .replace(/\0(?:\s*,?\s*(?:\bor\b|\band\b)?\s*\0)+/gi, '\0') // "… or /weekly-…": one gap
    .replace(/\s*\0\s*([.,;:!?])/g, '$1')
    .replace(/\0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return { limits, rest, bad }
}

const now = (readings: Reading[], kind: string) => readings.find(w => w.kind === kind)?.percentUsed
const at = (l: Limit, readings: Reading[]) => {
  const p = now(readings, l.kind)
  return `${NAME[l.kind]} ${l.percent}% (${p === undefined ? 'no reading yet' : `now ${p}%`})`
}

function statusText(s: State | undefined, readings: Reading[]) {
  if (!s) return undefined
  if (s.phase === 'armed') return `stop at ${s.limits.map(l => at(l, readings)).join(' or ')}, ${s.mode}`
  if (s.phase === 'wrapping') return `wrapping up, cut off at ${at(s.ceiling!, readings)}`
  return s.ceiling ? `stopped, subagents cut off at ${at(s.ceiling, readings)}` : 'stopped at the usage limit'
}

const stateKey = async ($: $) => `s:${await $.session.id()}`
const turnKey = async ($: $) => `t:${await $.session.id()}`
const readingsOf = async ($: $) => (await $.session.usage()).rateLimits as Reading[]
const debug = ($: $, text: string) => $.ui.log(`token-utilization: ${text}`, { to: 'debug' })
const handoffPath = async ($: $) => `.claude/handoffs/HANDOFF-${(await $.session.id()).slice(0, 8)}.md`

async function load($: $) {
  return (await $.store.get(await stateKey($))) as State | undefined
}

async function save($: $, s: State | undefined, readings?: Reading[]) {
  const key = await stateKey($)
  if (s) await $.store.set(key, s)
  else await $.store.delete(key)
  $.ui.status(statusText(s, readings ?? (await readingsOf($))))
}

const activeAgents = async ($: $) => (await $.agent.list()).filter(a => ACTIVE.includes(a.status))

// Cancels the main turn and stops every running subagent; the state is saved first, so the
// notifications those stops raise are recognised as the mod's own.
async function stopAll($: $, s: State, readings?: Reading[]) {
  const agents = await activeAgents($)
  Object.assign(s, { phase: 'stopped', ceiling: undefined, inject: undefined, wrapTurnId: undefined })
  s.stoppedIds = [...(s.stoppedIds ?? []), ...agents.map(a => a.id)]
  await save($, s, readings)
  const turnId = (await $.store.get(await turnKey($))) as string | undefined
  if (turnId) await $.turn.abort({ turnId }).catch(err => debug($, `abort failed: ${err}`))
  for (const a of agents) {
    const r = await $.tool.call({ tool: 'TaskStop', task_id: a.id }).catch(err => ({ deny: String(err) }))
    if ('deny' in r && r.deny !== undefined) debug($, `TaskStop ${a.id} failed: ${r.deny}`)
  }
}

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)

function mainText(label: string, interrupted: boolean, subagents: boolean, path: string, cutoff: number) {
  const first = interrupted
    ? `You were interrupted because ${label}, the limit set for this task.`
    : `${cap(label)}, the limit set for this task.`
  return [
    `${first} Wrap up now:`,
    '',
    '- If only a little work is left, finish it.',
    '- Otherwise stop here and leave the work easy to continue.',
    '',
    `Do not start new work.${subagents ? ' Subagents received the same instruction; collect what they report.' : ''}`,
    'End with handoff notes as your final message: what is done, what is in progress, what is left,',
    `and the exact next step. That message is saved to ${path}; to resume later, read that file first. Usage is cut off at ${cutoff}%.`,
  ].join('\n')
}

const subText = (label: string, cutoff: number) =>
  `${cap(label)}, the limit set for this task. Wrap up now: if only a little work is ` +
  'left, finish it. Otherwise stop here and report what is done, what is in progress and what is ' +
  `left. Do not start new work. Usage is cut off at ${cutoff}%.`

async function trip($: $, s: State, limit: Limit, readings: Reading[]) {
  const label = `${NAME[limit.kind]} usage reached ${limit.percent}%`
  if (s.mode === 'immediate') {
    await stopAll($, s, readings)
    $.ui.log(`token-utilization: ${label}, stopped`)
    return
  }
  const ceiling = { kind: limit.kind, percent: Math.min(100, limit.percent + 5) }
  const turnId = (await $.store.get(await turnKey($))) as string | undefined
  const agents = await activeAgents($)
  const path = await handoffPath($)
  if (!agents.length) {
    if (!turnId) {
      await save($, { ...s, phase: 'stopped' }, readings)
      $.ui.log(`token-utilization: ${label}, stopped`)
      return
    }
    await save($, { ...s, phase: 'wrapping', ceiling }, readings)
    await $.turn.abort({ turnId }).catch(err => debug($, `abort failed: ${err}`))
    void $.prompt.submit({ text: mainText(label, true, false, path, ceiling.percent) }).catch(err => debug($, `submit failed: ${err}`))
    $.ui.log(`token-utilization: ${label}, wrapping up; cut off at ${ceiling.percent}%`)
    return
  }
  // Subagents running: message everyone, interrupt nobody.
  const next: State = { ...s, ceiling, messagedIds: [...(s.messagedIds ?? []), ...agents.map(a => a.id)] }
  if (turnId) Object.assign(next, { phase: 'wrapping', wrapTurnId: turnId, inject: mainText(label, false, true, path, ceiling.percent) })
  else next.phase = 'stopped'
  await save($, next, readings)
  for (const a of agents) {
    const r = await $.session.send({ to: { agentId: a.id }, text: subText(label, ceiling.percent) }).catch(err => ({ isDelivered: false, reason: String(err) }))
    if (!r.isDelivered) debug($, `wrap-up message to ${a.id} not delivered: ${r.reason}`)
  }
  $.ui.log(`token-utilization: ${label}, ${turnId ? 'wrapping up' : 'stopped; subagents wrapping up'}; cut off at ${ceiling.percent}%`)
}

// A prompt or command line naming a limit: undefined when it names none, else the text without
// the limit phrase, or the reason to refuse it.
async function arm($: $, text: string): Promise<{ rest: string } | { drop: string } | undefined> {
  const { limits, rest, bad } = parse(text)
  if (!limits.length) return undefined
  if (bad) return { drop: FORM }
  const readings = await readingsOf($)
  for (const l of limits) {
    const p = now(readings, l.kind)
    if (p !== undefined && p >= l.percent) {
      return { drop: `token-utilization: ${NAME[l.kind]} usage is already at ${p}%, past the ${l.percent}% limit. Prompt not sent.` }
    }
  }
  const answer = await $.ui.ask('What should happen when the limit is reached?', [IMMEDIATE, WRAP]).catch(() => undefined)
  if (answer !== IMMEDIATE && answer !== WRAP) return { drop: 'token-utilization: no stop mode chosen. Prompt not sent.' }
  await save($, { limits, mode: answer === IMMEDIATE ? 'immediate' : 'wrap-up', phase: 'armed' }, readings)
  return { rest }
}

const isTyped = (o: PromptOrigin) => o.kind === 'composer' || o.kind === 'bridge'
// A -p prompt naming a limit is handled like a typed one (and dropped, as nobody can be asked).
const mayArm = (o: PromptOrigin) => isTyped(o) || o.kind === 'sdk'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'token-utilization',
      description: 'Show the usage limit set for this session, or remove it with off',
      argumentHint: '[off]',
    })
    await save($, await load($)) // redraw the status after a reload or a resume
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    if (e.agentId === undefined) {
      await $.store.set(await turnKey($), e.turnId)
      const s = await load($)
      if (s?.phase === 'wrapping' && !s.wrapTurnId) await save($, { ...s, wrapTurnId: e.turnId })
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId !== undefined) return r
    const key = await turnKey($)
    if ((await $.store.get(key)) === e.turnId) await $.store.delete(key)
    const s = await load($)
    if (s?.wrapTurnId === e.turnId) {
      await save($, { ...s, phase: 'stopped', wrapTurnId: undefined, inject: undefined })
      const path = await handoffPath($)
      const root = await $.session.root()
      try {
        await $.fs.write(`${root}/${path}`, r.text)
        await $.fs.write(`${root}/.claude/handoffs/.gitignore`, '*\n')
        $.ui.log(`token-utilization: handoff notes saved to ${path}`)
      } catch (err) {
        $.ui.log(`token-utilization: handoff notes not saved to ${path}: ${err}`)
      }
    } else if (s?.phase === 'armed' && !s.warned) {
      const readings = await readingsOf($)
      const missing = s.limits.filter(l => now(readings, l.kind) === undefined)
      if (missing.length) {
        $.ui.log(`token-utilization: no ${missing.map(l => NAME[l.kind]).join(' or ')} usage reading yet, so the limit cannot take effect`)
        await save($, { ...s, warned: true }, readings)
      }
    }
    return r
  })

  // The main agent's wrap-up text while subagents run: read with its next tool result, once.
  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId !== undefined || e.tool === 'AskUserQuestion' || ('deny' in r && r.deny !== undefined)) return r
    const s = await load($)
    if (!s?.inject) return r
    await save($, { ...s, inject: undefined })
    return { ...r, context: [...(r.context ?? []), s.inject] } as typeof r
  })

  on('prompt.submit', async ($, e, next) => {
    const o = e.origin
    if ((o.kind === 'plugin' && o.name === $.plugin.name) || e.command?.name === 'token-utilization') return next(e)
    // A slash command's limit is handled at command.run, which runs first.
    if (!e.command && mayArm(o)) {
      const r = await arm($, e.text)
      if (r && 'drop' in r) return { drop: r.drop }
      if (r) return next({ ...e, text: r.rest })
    }
    const s = await load($)
    if (!s) return next(e)
    if (isTyped(o)) {
      if (s.phase !== 'armed') await save($, undefined) // a typed prompt ends the wrap-up or the stop
      return next(e)
    }
    if (s.phase !== 'stopped') return next(e)
    if (o.kind === 'task-notification') {
      // ponytail: reads the id from the notification's text format; if that format changes, these
      // notifications fall back to the restart question. Use a structured task id if the event gains one.
      const id = /<task-id>([^<]+)<\/task-id>/.exec(e.text)?.[1]
      if (id && s.stoppedIds?.includes(id)) return { drop: 'token-utilization: dropped the notification of a subagent it stopped.' }
      if (id && s.messagedIds?.includes(id)) return next(e)
    }
    try {
      const sent = await $.ui.notify('An automatic prompt is waiting for your answer', { title: 'token-utilization' })
      if (!sent.isSent) debug($, `notification not sent: ${sent.reason}`)
    } catch (err) {
      debug($, `notification not sent: ${err}`)
    }
    const answer = await $.ui.ask('The usage limit was reached. Run this automatic prompt?', [YES, 'No']).catch(() => undefined)
    if (answer !== YES) return { drop: 'token-utilization: automatic prompt not run, the usage limit was reached.' }
    await save($, undefined)
    return next(e)
  })

  on('command.run', async ($, e, next) => {
    if (e.command === 'token-utilization') {
      const arg = e.args.trim().toLowerCase()
      if (arg === 'off') {
        await save($, undefined)
        return { text: 'token-utilization: limit removed.' }
      }
      if (arg) return { text: 'Usage: /token-utilization [off]' }
      const s = await load($)
      if (!s) return { text: 'token-utilization: no limit is set.' }
      const readings = await readingsOf($)
      return { text: `token-utilization: ${s.limits.map(l => at(l, readings)).join(' or ')}, mode ${s.mode}, ${s.phase}.` }
    }
    if (mayArm(e.origin)) {
      const r = await arm($, e.args)
      if (r && 'drop' in r) return { text: r.drop }
      if (r) return next({ ...e, args: r.rest })
    }
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    const s = await load($)
    const readings = e.rateLimits as Reading[]
    const reached = (l: Limit) => (now(readings, l.kind) ?? -1) >= l.percent
    if (s?.phase === 'armed') {
      const hit = s.limits.find(reached)
      if (hit) await trip($, s, hit, readings)
      else await save($, s, readings)
    } else if (s?.ceiling && reached(s.ceiling)) {
      const c = s.ceiling
      await stopAll($, s, readings)
      $.ui.log(`token-utilization: ${NAME[c.kind]} usage reached ${c.percent}% during the wrap-up, stopped`)
    } else if (s) await save($, s, readings)
    return next(e)
  })
}
