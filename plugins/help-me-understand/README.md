# help-me-understand

Claude's research findings, answers and work summaries are often too long or too tangled to follow. This plugin adds one command that turns such a text into a single web page built to be easy to take in and quick to start: the whole idea as a picture with the bottom line under it, then a few short stops that each lead with a visual, in plain English. Nothing from the original is dropped; supporting detail is collapsed into one drawer instead.

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
| a file path or URL | The contents of that file or page. |

The skill only runs when you invoke it; Claude never starts it on its own.

You get a link to the page, its bottom line in one sentence and one next action. Running it again for the same topic in the same conversation updates the same page, so the link stays the same.

## How it works

1. **Find the source.** Claude reads a file itself; a Haiku subagent extracts the text of a URL.
2. **Pick a page type:** concept, research, work summary or how-to. Each has its own section order (see `skills/help-me-understand/references/page-types.md`).
3. **Write a page spec.** The session model lists every point in the source, draws the gist, maps each point to a stop or to the reference drawer, and turns sentences that deliver a number, a share, a mechanism or a per-option judgement into the matching visual.
4. **Render.** `scripts/build_page.py` checks every word limit (naming the field that breaks one), turns the spec into one self-contained HTML file from the bundled template, and prints how many first-read words sit in prose and how many in visuals. It costs no tokens and takes well under a second.
5. **Check.** Two Haiku subagents run in parallel: one lists any source point the page left out and anything the page added that the source does not say, and one answers three questions using only the page text. Problems are fixed and the page is re-rendered once.
6. **Publish** with the Artifact tool, or leave the file if the tool is unavailable.

## What the page contains

- The title, then one panel with the gist picture and the bottom line (25 words at most). The gist is a chain from cause to outcome, a verdict of the winner against the alternatives, or a status of tallies with state icons.
- One quiet line saying the reader may stop there, with the number of stops and the reading time (about 200 words per minute, counting only what shows without opening a collapsed block).
- A route of up to five numbered stops that marks the stop in view, and a scroll progress bar.
- Stops that each lead with a visual and keep prose to 60 words: big figures, icon arrays for proportions, chains, cards with pros and cons or states, numbered stepper (Back, Next, Start over), comparison table, bar chart, dot chart, flow diagram, timeline, before and after pair, "Check yourself" click-to-reveal prompts (concept pages only), glossary strip, and a slot for a bespoke SVG diagram. Icons come from a closed built-in set and always sit next to a text label.
- One collapsed "Full detail" drawer for reference material, then "Also worth knowing", a collapsed block for tangents.
- One "Next action" card and the sources.

Light and dark themes, a text column of about 65 characters per line, keyboard access with visible focus, no autoplaying motion, and no external scripts, fonts or images. With JavaScript off, every stepper step is visible and the route is a plain list of links; when printed, every step and every collapsed block is shown.

## Defaults

| Default | Why |
|---|---|
| A picture of the whole idea first, and a visual in every stop | A plain first screen that looks short makes readers more willing to start, and pictures of structure, quantity and sequence help comprehension. |
| Word limits on every field, enforced by the renderer | Written guidance alone did not shorten the pages; limits that fail the render did. |
| About four items visible per group, the rest collapsed | Small groups fit in working memory; collapsing keeps everything one click away. |
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

The page opens with a verdict picture of arq against the other two libraries, each with the reason it lost, then short stops for when the verdict holds, the measurements and a comparison table with arq's column highlighted; the evidence per library sits in the Full detail drawer.

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
├── scripts/build_page.py        spec to HTML renderer, with --selftest
├── references/page-types.md     gist kind and stops per page type
├── references/spec-schema.md    the spec format, limits, block types, icons and a complete example
├── references/evidence.md       the rules and their sources
└── evals/                       three test cases with input files
```
