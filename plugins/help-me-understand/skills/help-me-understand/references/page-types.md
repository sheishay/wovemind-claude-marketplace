# Page types

Every page opens with the title, the gist picture and the bottom line in one panel, then a line saying the reader may stop there, then the route of numbered stops. It ends with the "Full detail" drawer (only when some material belongs to no single stop), "Also worth knowing" (when there are tangents), the next action and the sources. The script adds all of those. What changes between types is the gist kind and the order and kind of stops in between, because readers look for different things first.

Each stop is drawn as its own sheet and leads with a visual that uses the full page width, with a sentence or two saying what to notice. Under that lead comes everything the source says about the stop's idea, each group under a `title`: tables with all their rows, lists with all their items, code verbatim, and short paragraphs. The stops listed for each type below are the usual ones and their usual order. A source with more ideas gets more stops, up to twelve, and every section of the source lands in one of them.

Section headings below are patterns. Write each real heading as the idea it states, in the source's own words.

## concept

For explaining how something works or what it means.

**Gist:** `chain`, from the cause to the outcome, with the outcome node marked. For a diagnosis, the chain is the causal path that produces the symptom.

1. **The idea in one example.** One concrete case the reader can picture, then the general idea. A `chain` for the life cycle of the thing, a `before_after` for a single change, a `glossary` if the page relies on three or more unfamiliar terms.
2. **How it works.** The mechanism: `chain` when it runs in a line, `stepper` when the reader should step through it, `flow` or bespoke `svg` when it branches. End this stop with one `check` prompt testing the part most likely to be misunderstood; a check is not a visual, so it never makes a stop of its own.
3. **The numbers that matter**, as `stats` (a threshold, a count, a duration) or `icon_array` (a share).
4. **Where it matters or what to do.** `cards` for alternatives with their pros and cons, `table` for options across the same criteria, `stepper` for ordered fixes.

Limits and edge cases stay in the stop they qualify. Use one or two `check` prompts in total; more turns the page into a quiz.

## research

For answering a question by comparing options or weighing evidence.

**Gist:** `verdict`, the recommended option against up to three alternatives, each with the reason it lost.

1. **When the verdict holds.** `cards` with one card per condition ("Choose X now", "Y only if ..."), stated only as the source states them.
2. **The deciding measurements.** `bar_chart` or `dot_chart` for each measured criterion, `stats` for a striking single figure.
3. **The options side by side.** A `table` with one column per option and one row per criterion, the recommended option highlighted.
4. **Open questions**, as `cards` with `"state": "open"`, when the source leaves something unresolved.

Evidence detail per option, licences and options ruled out stay in the stop that discusses them, under a `title` naming the option or topic. How the comparison was measured may go into `reference` when it applies to the whole page. Weak or disputed evidence is said to be weak. No `check` prompts: the reader is deciding, not learning a concept.

## work-summary

For reporting what was done, what changed and what is left.

**Gist:** `status`, with tallies such as done, still open, needing a decision (`warn`) and blocking.

1. **What works now.** The concrete result the reader can see or try. A `chain` for a new flow, `stats` for a number that describes it.
2. **What changed and why.** `cards` with `"state": "done"` per change, `before_after` for one important behaviour change, `icon_array` for a share that justified a decision, `timeline` when the order of events matters.
3. **Open items.** `cards`, one per unfinished task, bug or question, with its state (`blocked`, `open`, `warn` for one that needs the reader's decision) and its owner or next step when known. Never drop an open item.

Branch names, issue numbers, file paths and how each fix was done stay with the change or open item they belong to, in a table or list under the cards. The next action is the single most useful open item to do next. No `check` prompts.

## how-to

For telling the reader how to do something.

**Gist:** `chain` of the main steps (up to four), with the finished result as the outcome node.

1. **Before you start.** What the reader needs ready, as `cards` with `"state": "done"` or a short `list` beside a visual.
2. **The steps.** One `stepper`, one bounded action per step, with the exact command, path or setting in `code` and the expected result in the step's text ("You should see `Connected`").
3. **If something goes wrong.** `cards` with `"state": "warn"`, one per likely failure, its fix as a point. Longer troubleshooting follows the cards in the same stop, as lists and `code` blocks.
4. **How to tell it worked.** The final check, as a `before_after` or `stats`.

The next action is the first step, stated so it can be done right now. No `check` prompts.
