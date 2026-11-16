# Page types

Every page starts with the title, the reading time and the bottom-line card, and ends with "Also worth knowing" (when there are tangents), the next action and the sources. The script adds those. What changes between types is the order and kind of sections in between, because readers look for different things first.

Section headings below are patterns. Write each real heading as the idea it states, in the source's own words.

## concept

For explaining how something works or what it means.

1. **The idea in one example.** Start with one concrete case the reader can picture, then state the general idea it illustrates. A glossary strip goes here if the page relies on three or more unfamiliar terms.
2. **How it works.** The mechanism, as a `stepper` when it happens in order, or a `flow` or bespoke `svg` when the parts and their connections matter more than the order.
3. **One `check` prompt** right after the mechanism, testing the part most likely to be misunderstood.
4. **Where it matters.** When to use it, when not to, and the trade-off, with a `table` or `before_after` if there are two clear alternatives.
5. **Limits and edge cases**, collapsed in `details` unless the reader needs them to act.

Use one or two `check` prompts in total. More than that turns the page into a quiz.

## research

For answering a question by comparing options or weighing evidence.

1. **The verdict.** Which option wins, for whom, and the one reason. The bottom line already states it; this section adds the conditions under which it holds.
2. **The options side by side.** A `table` with one column per option and one row per criterion, the recommended option highlighted. Use a `bar_chart` or `dot_chart` when a criterion is a number.
3. **The evidence for each option.** One short section per serious option: what supports it, what counts against it, and how strong the evidence is. Weak or disputed evidence is said to be weak.
4. **What would change the verdict.** The assumptions it rests on, stated as conditions ("if traffic grows past X, choose B").
5. **Options ruled out**, collapsed in `details`, each with the reason it was dropped.

No `check` prompts. The reader is deciding, not learning a concept.

## work-summary

For reporting what was done, what changed and what is left.

1. **What works now.** The concrete result, stated as something the reader can see or try ("Login with magic links works; open `/login` to try it"). Visible progress comes first because it is the part most easily buried.
2. **What changed.** Grouped by area, about four items visible per group. Use `before_after` for one important behaviour change, or a `timeline` when the order of events matters.
3. **Decisions made**, with the reason for each, so nobody has to reconstruct them later.
4. **Open items.** Every unfinished task, known bug and open question, each with its owner or next step when known. Never drop an open item; collapse the minor ones in `details`.

The next action is the single most useful open item to do next. No `check` prompts.

## how-to

For telling the reader how to do something.

1. **Before you start.** What the reader needs ready: access, tools, files, time. A short `list`.
2. **The steps.** One `stepper`, one bounded action per step, with the exact command, path or setting in `code`. Put a step's expected result in its text ("You should see `Connected`"), so the reader knows the step worked.
3. **If something goes wrong.** The likely failures and their fixes, collapsed in `details` per failure.
4. **How to tell it worked.** The final check.

The next action is the first step, stated so it can be done right now. No `check` prompts.
