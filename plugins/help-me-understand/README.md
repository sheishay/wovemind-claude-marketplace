# help-me-understand

Claude's research findings, answers and work summaries are often too long or too tangled to follow. This plugin adds one command that turns such a text into a single web page built to be easy to take in: the bottom line first, one idea per section, a visual wherever a visual carries the point, and plain English. Nothing from the original is dropped; minor points are collapsed instead.

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

1. **Find the source.** A Haiku subagent extracts the text of a file or URL.
2. **Pick a page type:** concept, research, work summary or how-to. Each has its own section order (see `skills/help-me-understand/references/page-types.md`).
3. **Write a page spec.** The session model lists every point in the source, maps each to a section, and chooses a visual by the shape of the content.
4. **Render.** `scripts/build_page.py` turns the spec into one self-contained HTML file from the bundled template. It costs no tokens and takes well under a second.
5. **Check.** Two Haiku subagents run in parallel: one lists any source point the page left out, and one answers three questions using only the page text. Problems are fixed and the page is re-rendered once.
6. **Publish** with the Artifact tool, or leave the file if the tool is unavailable.

## What the page contains

- Title, page type and reading time (about 200 words per minute), then the bottom-line card.
- A small "On this page" section list and a scroll progress bar.
- Sections with these components, each used only where it carries content: numbered stepper (Back, Next, Start over), comparison table, bar chart, dot chart, flow diagram, timeline, before and after pair, "Check yourself" click-to-reveal prompts (concept pages only), collapsed details, glossary strip, and a slot for a bespoke SVG diagram.
- "Also worth knowing", a collapsed block for tangents.
- One "Next action" card and the sources.

Light and dark themes, a text column of about 65 characters per line, keyboard access with visible focus, no autoplaying motion, and no external scripts, fonts or images. With JavaScript off or when printed, every stepper step is visible.

## Defaults

| Default | Why |
|---|---|
| About four items visible per group, the rest collapsed | Small groups fit in working memory; collapsing keeps everything one click away. |
| Bars and dots only, labelled directly, bar axes from zero | Position and length are read most accurately, and labels on the mark avoid a legend. |
| Animation only as a reader-controlled stepper | Motion that plays on its own runs past a reader who is still thinking. |
| No decoration, fun facts or story hooks | Off-topic material lowers what readers remember. |
| Full plain English, even when a terse or caveman mode is active | The reader asked for this because the original was hard to follow. |

## Evidence

The rules come from research on multimedia learning, cognitive load, animation, chart reading and reading with ADHD. `skills/help-me-understand/references/evidence.md` lists each rule with its sources and the numbers that were checked.

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

The page opens with that verdict, shows a comparison table with arq's column highlighted, gives one short section of evidence per library, says what would change the verdict, and collapses the ruled-out options.

To explain a file or a page instead:

```
/help-me-understand:help-me-understand docs/architecture.md
/help-me-understand:help-me-understand https://example.com/long-article
```

## Files

```
skills/help-me-understand/
├── SKILL.md                     the workflow
├── assets/page-template.html    styles, themes and the stepper and progress scripts
├── scripts/build_page.py        spec to HTML renderer, with --selftest
├── references/page-types.md     section order per page type
├── references/spec-schema.md    the spec format, block types and a complete example
├── references/evidence.md       the rules and their sources
└── evals/                       three test cases with input files
```
