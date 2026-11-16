---
name: help-me-understand
description: Turn a long or tangled answer, research finding, work summary, file or web page into a published HTML page built to be easy to take in, with the bottom line first, small chunks, a visual wherever one carries the point, and plain English. Use only when the user invokes /help-me-understand:help-me-understand, optionally with a topic, a file path or a URL.
argument-hint: "[topic | file path | URL]  (empty = the last substantial answer in this conversation)"
disable-model-invocation: true
---

# Help me understand

The user asked for this because something in the conversation, or a file or page, is too long or too tangled to follow. Your job is to turn it into one page they can take in quickly and remember: the bottom line first, one idea per section, a visual wherever a visual carries the point, and nothing they need left out.

Scripts live in `${CLAUDE_SKILL_DIR}/scripts/` (if that variable is not set, they are next to this file under `scripts/`). The page template is in `assets/page-template.html`; never edit it per page, because the script fills it.

References, read only when the step says so:
- `references/page-types.md`: the section layout for each page type. Read it in step 2, every time.
- `references/spec-schema.md`: every field of the page spec, the block types, the rules for bespoke SVG, and one complete example. Read it in step 3 before you write the spec, and again when the script rejects a field.
- `references/evidence.md`: the research behind the rules below. Read it only if the user asks why the page looks the way it does.

## Write in full plain English

Write full, plain English in the page and in every subagent brief, regardless of any active terse or caveman mode. The reader came here because the original was hard to follow, and compressed fragments would make it harder again. Apply the rules of `/humanizer:humanizer` to all page text. If that skill is not installed, follow its rules inline: no "not X but Y" contrasts, no forced triads, no dash-heavy sentences, no inflated or salesy claims, no stock AI words, no bold labels used as filler, no one-line closers. Section headings count as page text, so check them too.

Also:
- Give a concrete example before the general rule. A reader who has seen one real case can hang the rule on it.
- Define each term once, in a glossary strip or where it first appears, then keep using exactly that word. A synonym makes the reader wonder whether it is a second thing.
- Keep sentences short and in the active voice, and keep paragraphs to two or three sentences, because long paragraphs are where readers lose their place.
- Leave out jokes, story hooks, fun facts and decorative asides. Interesting but off-topic material measurably lowers what readers remember.

## 1. Find the source

- **No argument:** use the last substantial answer in this conversation, meaning the most recent reply of yours that explains, reports or summarises something (skip short confirmations and questions). If there is none, ask the user what to explain and stop.
- **A topic:** use what this conversation already says about it. If the conversation says little, research it the way you normally would, then continue.
- **A file path:** read the file yourself. You need its exact text to write the page, so a subagent would only add a round trip.
- **A URL:** delegate the fetch to a Haiku subagent (see "Subagents" below), because a raw web page would fill your context with navigation and markup. Ask it to return the full content as plain text: every claim, number, step, option, caveat and open question, in the original order, with headings kept. Ask for extraction, not a summary, because the source check later compares against this text. If the fetch fails, tell the user and stop.

Make a scratch directory for this topic (`$WORK`, inside your scratchpad when you have one) and save the full source text as `$WORK/source.txt`. The checks in step 5 read it from there. On a re-run for the same topic in this conversation, reuse the same directory and file names so the page republishes to the same link.

## 2. Pick a page type

Read `references/page-types.md` and choose the type that fits the source:
- **concept:** explains how something works or what it means. A diagnosis ("why is this happening, and what do we do") is a concept page: the reader has to understand the cause before the fixes make sense.
- **research:** answers a question by comparing options or weighing evidence.
- **work-summary:** reports what was done, what changed and what is left.
- **how-to:** tells the reader how to do something, in order.

Each type has its own section order because readers look for different things first in each: the idea in a concept, the verdict in research, the current state in a work summary, the first step in a how-to.

## 3. Write the page spec

Read `references/spec-schema.md` and write `$WORK/spec.json`. You write the spec yourself rather than delegating it, because deciding what matters and which visual fits needs the whole conversation and real judgment.

1. **List every point in the source first.** Every claim, number, step, option, caveat and open item becomes a line in your working list. Map each one to a section, to a collapsed details block, or to "Also worth knowing". Nothing is dropped, because a page that silently loses a caveat is worse than the long original.
2. **Bottom line.** One or two short sentences, 35 words at most (the script rejects more): what the reader should remember if they read nothing else. Readers with attention or working-memory limits recall fewer central ideas, so state the central idea outright at the top.
3. **One main idea per section**, with a heading that says the idea ("A bigger pool is not always faster"), not a topic label ("Pool size"). Headings that state the point let a skimming reader get the argument from the nav alone.
4. **Cap what is displayed, never what is kept.** Show about four items per group; put the rest in a collapsed `details` block or rely on the `list` block, which collapses items past four by itself. Small visible groups fit in working memory, and collapsing keeps the rest one click away.
5. **Make the first read much shorter than the source.** The first read is everything visible without opening a collapsed block. For a source over about 400 words, aim for half its length or less. The user came here because the original was too long, so a page that keeps every point at full length in the main line has solved nothing. Get there by letting a table, chart or stepper replace the sentences it makes redundant, by stating each point once, and by moving supporting detail (exact figures behind a conclusion, method, minor caveats, reference numbers) into `details` blocks. The script reports the first-read word count when it renders. Never meet the budget by dropping a visual: a stepper or chart costs few words, and it is the part the original lacked.
6. **Say only what the source says.** Do not add claims, numbers, conditions or commands of your own, because the reader cannot tell your addition from the original and will trust both equally. A worked example or analogy you add to explain an idea is fine when it is plainly an illustration. If a figure is your own arithmetic from the source's numbers, show the arithmetic.
7. **Tangents go in `also_worth_knowing`.** Side issues interrupt the main line, but the reader may still need them later.
8. **One `next_action`:** a concrete thing the reader can do in a few minutes, such as "Open `config/db.yml` and check the pool size". Take it from the source when the source names a next step; otherwise use the smallest first move towards what the source recommends. Knowing something and acting on it are different steps, and a small first step is the one that gets taken.
9. **Sources:** add a `sources` entry for each file or URL the content came from. For a file, the label is the file name and there is no `url`; for conversation content, leave `sources` out. These are the only links the page may contain.

### Choose visuals by the shape of the content

Start with the hardest idea in the source, the one a reader is most likely to get lost in, and give it the visual that fits its shape. A page of well-organised text with no picture of its hardest idea has only tidied the original. Then add a visual to any other section whose content has one of the shapes below. Each visual must carry content the reader needs; if you cannot say what a visual shows that the text does not, leave it out.

| Content shape | Visual |
|---|---|
| A process or sequence | `stepper` (the reader steps through), or `flow` when the branching matters more than the order |
| Quantities to compare | `bar_chart` for sizes from zero, `dot_chart` for values on a shared scale that need not start at zero |
| Options compared on the same criteria | `table`, with the recommended option's column highlighted. Cells hold a few words or a number (14 words at most); a table of sentences is harder to read than the paragraphs it replaced |
| Change over time | `timeline` for dated events, `stepper` for stages of one thing changing |
| One thing before and after | `before_after` |
| Structure or relationships | `flow`, or a bespoke `svg` when boxes and arrows in layers cannot show it |

- Use bars and dots only, labelled directly, because position and length are the encodings people read most accurately and labels next to the mark avoid looking back and forth to a legend. Never use pie charts, area charts or colour alone to carry a value.
- Label every arrow in a `flow` with what moves or happens, because an unlabelled arrow only says "related somehow".
- Use `check` ("Check yourself") prompts on concept pages only, one or two per page, placed right after the idea they test. Trying to answer before seeing the answer improves memory of that idea; on summaries and how-tos there is nothing to test.
- Use `glossary` when the page relies on three or more terms the reader may not know.
- Write a bespoke `svg` only when no other block fits, and follow the rules in `references/spec-schema.md`.
- If nothing fits a section, use no visual. Text alone beats a decorative picture.
- Never add motion that plays on its own. The `stepper` is the only animation: the reader controls it with Back, Next and Start over, so it shows a change one frame at a time and never runs past a reader who is still thinking.

## 4. Render

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/build_page.py" "$WORK/spec.json" "$WORK/<slug>.html" > "$WORK/page.txt"
```

Use a short slug from the title, such as `connection-pooling`. If the script exits with "invalid spec", it names the field: fix that field and run it again. On success, `page.txt` holds the page's text, including the text inside collapsed blocks; the naive-reader check reads it. The script also prints a line such as `first read: 420 words; collapsed: 310 words`. Compare the first-read count with `wc -w "$WORK/source.txt"`: if the first read is not clearly shorter than the source, move detail into `details` blocks or cut repetition, then render again.

## 5. Check with two Haiku subagents

Spawn both checks in one message so they run in parallel. Each checks a fixed recipe with an answer you can verify, which is what Haiku does reliably and cheaply.

1. **Source check.** Brief: "You are checking a page against its source. Read the source text at <absolute path of source.txt> and the page spec at <absolute path of spec.json>. Reply with two lists. MISSING: every point in the source (a claim, number, step, option, caveat or open item) that the page does not state anywhere, including inside collapsed blocks; quote each from the source. ADDED: every claim, number, condition or command on the page that the source does not state; quote each from the spec. Do not list the labels under `sources`, arithmetic that the page shows worked out from the source's own numbers, or the wording of `next_action`. Write NONE under a list that is empty."
2. **Naive-reader check.** Before spawning, write three questions whose correct answers you know and which the page should answer: one about the bottom line, one about the hardest idea, one about the next action. Brief: "Read only the file <absolute path of page.txt> and answer these three questions using only what it says. If the page does not answer a question, say so. Questions: <three questions>."

Give the subagents file paths rather than pasted text. Pasting is slow, and a paraphrase pasted in place of the real page means the check tests your paraphrase. A subagent knows nothing about this conversation, so the brief must stand on its own. The replies arrive as messages when each subagent finishes; they come one at a time, so end your turn and wait until both are in instead of sleeping or polling.

Then judge the replies yourself:
- A missing point that is really in the source goes into the spec, in a `details` block, a caption or "Also worth knowing", so the fix does not push the first read back over its budget.
- An added item that is not a plain illustration or shown arithmetic comes out of the spec.
- A wrong or "not answered" reply means the page is unclear on that point: rewrite that part, often by moving it higher, adding an example, or giving it a visual.

If anything changed, re-render once (step 4). Do not run the checks a second time; one fix pass catches most problems without turning into a loop. A check that fails to run, returns something that is not an answer to its brief, or contradicts the source in an obvious way is retried once with `model: "sonnet"` instead of being trusted.

## 6. Publish

Load the `artifact-design` skill before the first publish, because it holds the page contract the Artifact tool enforces. Then call `Artifact` with:
- `file_path`: `$WORK/<slug>.html`;
- `icon`: one generic word for the subject, such as `book`, `chart` or `list`;
- `description`: one sentence saying what the page explains.

Pass no `capabilities`: the page only needs to be read. If the user runs this skill again for the same topic in this conversation, write to the same file path and publish it again, so the link stays the same.

If the `Artifact` tool is unavailable, skip publishing and give the user the full absolute path of the HTML file; it opens in any browser.

## 7. Reply in chat

Reply with three things only: the link (or the file path), the bottom line in one sentence, and the one next action. Do not paste the page into chat, because a second copy in chat is exactly the long text the user asked to get away from.

## Subagents

Use `Agent` with `model: "haiku"` for the mechanical work: fetching a URL in step 1, and the two checks in step 5. Keep everything that needs judgment on the session model: choosing what the page says, its type, its visuals and its wording, and deciding what to do with the check results. Write every brief in full plain English, give the absolute path of every file the subagent must read, and ask for the exact output format you want. A failed or suspicious Haiku run is retried once with `model: "sonnet"`; subagents never write the spec, render or publish.
