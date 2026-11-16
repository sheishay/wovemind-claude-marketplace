# help-me-understand

Claude's research findings, answers and work summaries are often too long or too tangled to follow. This plugin adds one command that reorganises such a text into a single web page built to be easy to take in: the whole idea as a picture with the bottom line under it, then numbered stops that each lead with a visual, in plain English. The page does not summarise. It holds the same information as the original, including every table row, list item and code listing, and each detail sits in the stop it belongs to.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install help-me-understand@wovemind
```

## Requirements

- **The Artifact tool**, to publish the page as a private claude.ai artifact and get a link. Without it, the skill leaves the HTML file on disk and gives you its full path; the file opens in any browser.
- **Python 3.8 or later** for the bundled renderer. It uses the standard library only.
- **The `humanizer` plugin is optional.** When `/humanizer:humanizer` is installed, its writing rules are applied to the page text; otherwise the skill follows a short inline version of the same rules.

No environment variables or settings.

## Usage

```
/help-me-understand:help-me-understand [topic | file path | URL]
```

| Argument | What gets explained |
|---|---|
| none | The last substantial answer in this conversation. |
| a topic | What this conversation says about it, researched further if the conversation says little. |
| a file path, a URL or a claude.ai artifact link | The contents of that file, page or artifact. |

The skill only runs when you invoke it; Claude never starts it on its own.

You get a link to the page, its bottom line in one sentence and one next action. Running it again for the same topic in the same conversation updates the same page, so the link stays the same.

## How it works

1. **Find the source.** Claude reads a file or a claude.ai artifact itself; a Haiku subagent extracts the text of any other URL. Tables and code listings are kept whole.
2. **Pick a page type:** concept, research, work summary or how-to. Each has its own section order (see `skills/help-me-understand/references/page-types.md`).
3. **Write a page spec.** The session model inventories every paragraph, table, list and code listing in the source, draws the gist, maps each item to a stop, and gives each stop a lead visual followed by all of that stop's detail in its original shape.
4. **Render.** `scripts/build_page.py` checks the length limits on labels and headings (naming the field that breaks one) and turns the spec into one self-contained HTML file from the bundled template. Its `--coverage` mode then lists every number and identifier that is in the source but missing from the page. Both cost no tokens and take well under a second.
5. **Check.** Two Haiku subagents run in parallel: one lists any source point, table row, list item or code line the page left out and anything the page added that the source does not say, and one answers three questions using only the page text. Problems are fixed and the page is re-rendered once.
6. **Publish** with the Artifact tool, or leave the file if the tool is unavailable.

## What the page contains

- The title, then one panel with the gist picture and the bottom line (25 words at most). The gist is a chain from cause to outcome, a verdict of the winner against the alternatives, or a status of tallies with state icons.
- One quiet line saying the reader may stop there, with the number of stops and the reading time (about 200 words per minute, counting only what shows without opening a collapsed block).
- A route of up to twelve numbered stops that marks the stop in view, and a scroll progress bar.
- Stops, each drawn as its own sheet, that lead with a visual and then give the stop's full detail under sub-headings, including tables of any length and verbatim code listings. The visuals are big figures, icon arrays for proportions, chains, cards with pros and cons or states, numbered stepper (Back, Next, Start over), comparison table, bar chart, dot chart, flow diagram, timeline, before and after pair, "Check yourself" click-to-reveal prompts (concept pages only), glossary strip, and a slot for a bespoke SVG diagram. Icons come from a closed built-in set and always sit next to a text label.
- Collapsed notes inside a stop for bulky verbatim material such as a long listing, each labelled with what it holds. A collapsed "Full detail" drawer only for material that belongs to no single stop, then "Also worth knowing", a collapsed block for asides.
- One "Next action" card and the sources.

Light and dark themes, running text held to about 65 characters per line while tables, cards, chains and charts use the full page width, keyboard access with visible focus, no autoplaying motion, and no external scripts, fonts or images. With JavaScript off, every stepper step is visible and the route is a plain list of links; when printed, every step and every collapsed block is shown.

## Defaults

| Default | Why |
|---|---|
| A picture of the whole idea first, and a visual in every stop | A plain first screen makes readers more willing to start, and pictures of structure, quantity and sequence help comprehension. |
| Same information as the source, checked by a coverage pass | A page that says less than its source sends the reader back to the original. |
| Length limits on labels and headings only, enforced by the renderer | Short labels keep the layout readable. Limits on how much a page may hold forced detail off the page, so those are set high. |
| Detail visible by default, under sub-headings in its stop | A reader looking for a detail finds it where the idea is explained; only bulky listings are collapsed, with a label saying what is inside. |
| Bars and dots only, labelled directly, bar axes from zero | Position and length are read most accurately, and labels on the mark avoid a legend. |
| Animation only as a reader-controlled stepper | Motion that plays on its own runs past a reader who is still thinking. |
| No decoration, fun facts or story hooks | Off-topic material lowers what readers remember. |
| Full plain English, even when a terse or caveman mode is active | The reader asked for this because the original was hard to follow. |

## Evidence

The rules come from research on multimedia learning, cognitive load, animation, chart reading, first impressions of web pages and reading with ADHD. `skills/help-me-understand/references/evidence.md` lists each rule with its sources and the numbers that were checked.

Two limits are worth knowing. Effects of design principles are smaller on self-paced pages like these than in lab settings. And no controlled study tests headings, chunking, progress bars or time estimates in adults with ADHD, so the ADHD-specific choices (reading time, progress bar, collapsed tangents, one next action) are reasonable extrapolations from working-memory research, not tested findings.

The ADHD-specific choices adapt the output rules of [i-have-adhd](https://github.com/ayghri/i-have-adhd) (MIT licence), rewritten for a page instead of a chat reply.

## Example

After a long answer comparing three queue libraries, run:

```
/help-me-understand:help-me-understand
```

The reply is a link to a research page, plus:

> Bottom line: use arq, because it is the only one of the three that is async and already runs on your Redis.
> Next: add `arq` to `requirements.txt` and run `arq --check worker.WorkerSettings`.

The page opens with a verdict picture of arq against the other two libraries, each with the reason it lost, then stops for when the verdict holds, the measurements and a comparison table with arq's column highlighted; the evidence for each library sits under its own sub-heading in the stop that discusses it.

To explain a file or a page instead:

```
/help-me-understand:help-me-understand docs/architecture.md
/help-me-understand:help-me-understand https://example.com/long-article
```

## Files

```
skills/help-me-understand/
├── SKILL.md                     the workflow
├── assets/page-template.html    styles, themes and the stepper, route and progress scripts
├── scripts/build_page.py        spec to HTML renderer, with --coverage and --selftest
├── references/page-types.md     gist kind and stops per page type
├── references/spec-schema.md    the spec format, limits, block types, icons and a complete example
├── references/evidence.md       the rules and their sources
└── evals/                       three test cases with input files
```
