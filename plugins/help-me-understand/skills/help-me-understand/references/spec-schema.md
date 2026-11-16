# Page spec format

The page spec is one JSON file. `scripts/build_page.py <spec.json> <out.html>` validates it, renders the page, prints the page's visible text to stdout and prints a word balance line to stderr. If the spec is invalid, the script exits with status 1 and names the bad field, for example `invalid spec: spec.sections[1].blocks[0].nodes[2].arrow: keep it to 3 words or fewer (got 4)`. Fix that field and run it again.

Every limit on this page is enforced by the script. When a field will not fit, do not squeeze the words into another field: turn the sentence into a visual block, or move it into the top-level `reference` list, which has no word limits.

All text is HTML-escaped. Inside any text except chart, flow and icon-array labels (which are drawn as SVG and show markup literally) you may use two kinds of inline markup: `` `code` `` for commands, paths and identifiers, and `**bold**` for the one term a paragraph defines. A blank line inside a `text` value starts a new paragraph. Text may not contain `{{` or `}}`. Word counts split on spaces, so `` `ALTER TABLE orders` `` counts as three words.

## Top level

| Field | Required | What it holds |
|---|---|---|
| `title` | yes | The page name, two to four words. It becomes the browser tab and gallery title. |
| `page_type` | yes | `concept`, `research`, `work-summary` or `how-to`. It sets the wording of the line under the bottom line and is not shown as a label. |
| `gist` | yes | The opening picture, drawn under the title. See "The gist" below. |
| `bottom_line` | yes | One or two short sentences, 25 words at most: the single thing to remember. Drawn inside the opening panel, under the gist. |
| `sections` | yes | One to five stops: `{ "heading", "short", "blocks" }`. See "Sections" below. |
| `reference` | no | List of `{ "title", "text" and/or "items" }`. Rendered after the sections as one collapsed "Full detail" drawer showing its entry count; each entry is a plain heading with a paragraph or a bullet list. No word limits. This is where exact figures, method, quotes, caveats and the second half of anything that did not fit go. |
| `also_worth_knowing` | no | List of strings, 30 words each at most: tangents and side notes, in a collapsed block after the reference drawer. |
| `next_action` | yes | `{ "text", "detail" }`. `text` (22 words at most) is one concrete action the reader can take now; `detail` (optional, 25 words at most) says why or how. |
| `sources` | no | List of `{ "label", "url" }`. `url` is optional and must be `http://` or `https://`. These are the only links the page may contain. Leave the key out, or use `[]`, when there are none. |

The script adds the rest: under the bottom line, one quiet line telling the reader they may stop there, with the stop count and the reading time (for example "That is the whole idea. 4 short stops below show why, about 3 minutes."); a route strip of numbered dots linking to each stop, which marks the stop in view; and the scroll progress bar. Reading time is about 200 words per minute over the first read, which leaves out collapsed text.

## The gist

The gist is the first thing the reader sees, so it should state the whole idea as a picture. It is built from fields, never raw SVG. Choose `kind` by the page:

| `kind` | Fields | Use it for |
|---|---|---|
| `chain` | `nodes`: 2 to 4 of `{ "icon", "label", "arrow", "outcome" }` | A cause and its effect, or a short strip of steps. `label` is 4 words at most. `arrow` (3 words at most) labels the arrow leading into that node, so the first node has none. Mark at most one node `"outcome": true`; it is drawn filled. Left to right on wide screens, top to bottom on narrow ones. |
| `verdict` | `winner`: `{ "name", "reason" }`, `alternatives`: 1 to 3 of `{ "name", "why_not" }` | Research and option pages. `name` is 4 words at most, `reason` 6, `why_not` 5. |
| `status` | `tallies`: 2 to 4 of `{ "count", "label", "state" }` | Work summaries. `count` is a whole number from 0 to 9,999, `label` 3 words at most, `state` one of `done`, `open`, `blocked`, `info`. Drawn as large numerals, each with a state icon. |

## Sections

Each section is a "stop" with a number. The script rejects a section that breaks any of these:

- `heading`: 9 words at most. Write the idea it states, not a topic label.
- `short`: the label under the stop's dot in the route strip, 3 words and 24 characters at most.
- At least one visual block. A visual is any block except `text`, `list`, `details`, `check` and `glossary`: the first three are reading text, a check is a question, and a glossary is a list of definitions, so none of them shows structure, quantity or sequence.
- Prose, meaning the words of `text` blocks plus the visible items of `list` blocks, is 60 words at most. A single `text` block is 40 words at most, and a section has at most 2 `text` blocks.
- At most 1 `details` block and at most 1 `check` block.

## Blocks

Every block has a `type`. Optional fields can be left out. On every block, `title` and `caption` are 18 words at most and `unit` 3.

| `type` | Fields and limits | Use it for |
|---|---|---|
| `text` | `text` (40 words) | Prose: the glue between visuals. Two or three short sentences. |
| `list` | `items` (1 to 6 strings, 16 words each), `ordered` (bool) | Parallel points. The first four show; the rest go into a collapsed "N more". |
| `stats` | `items`: 1 to 3 of `{ "value", "label", "note", "icon" }` | A sentence that exists to deliver a number. `value` is 12 characters at most ("8 million", "3%", "5 h"), `label` 6 words, `note` 8 words and gives the comparison or denominator ("of 40 million rows"). |
| `icon_array` | `count`, `total`, `label` (10 words) | A proportion ("3 percent of users"). Draws all `total` dots, at most 100, with `count` of them filled. Both are whole numbers. |
| `chain` | `nodes`: 2 to 5 of `{ "icon", "label", "arrow", "note", "outcome" }`, `title`, `caption` | A mechanism or cause and effect in a line. The same drawing as the gist chain, plus an optional `note` of 12 words under each node. `label` (4 words) and `arrow` (3 words) have the same limits as in the gist. Use `flow` instead when it branches. |
| `cards` | `cards`: 1 to 4 of `{ "title", "state", "text", "points" }`, `caption` | Per-option judgements, status boards and fix lists. `title` is 5 words, `text` 14, `state` one of `good`, `bad`, `warn`, `info`, `done`, `open`, `blocked` (drawn as an icon), and `points` up to 3 of `{ "sign": "+" or "-", "text" }` with 8 words each. |
| `stepper` | `steps`: 1 to 5 of `{ "title", "text", "block" }` | A process or a change over time, one step at a time with Back, Next and Start over. `title` is 8 words, `text` 28. `block` is optional and must be a visual other than a stepper. Every step shows when printed or without JavaScript. |
| `table` | `columns` (1 to 5), `rows` (1 to 6, each as long as `columns`), `highlight_column`, `caption` | Options compared across the same criteria. Each cell is 14 words at most. `columns[0]` may be `""` when the first column holds row labels. Highlight the recommended option's column. |
| `bar_chart` | `items`: 1 to 6 of `{ "label", "value" }`, `title`, `unit`, `caption` | Quantities that compare by size. Values are zero or more, with at least one above zero; the axis starts at zero. `label` is 8 words. |
| `dot_chart` | `items`: 1 to 6 of `{ "label", "value" }`, `min`, `max`, `title`, `unit`, `caption` | Values on a shared scale that need not start at zero. `min` and `max` default to the smallest and largest value; `max` must be greater than `min`, and every value must lie between them. |
| `flow` | `nodes`: 1 to 8 of `{ "id", "label" }`, `edges`: `[{ "from", "to", "label" }]`, `title`, `caption` | Boxes and arrows with branching, laid out top to bottom. Node `label` is 8 words, edge `label` 4. Ids must be unique, edges must name existing ids, and loops are rejected. |
| `timeline` | `items`: 1 to 5 of `{ "when", "title", "text" }` | Dated or ordered events. `when` is 4 words, `title` 8, `text` (optional) 18. |
| `before_after` | `before` and `after`: `{ "label", "text" }`, `caption` | One thing in two states. `label` (4 words) defaults to Before and After; `text` is 25 words. |
| `check` | `question` (25 words), `answer` | A click-to-reveal "Check yourself" prompt. Concept pages only. The answer stays collapsed and has no limit. |
| `details` | `summary` (10 words), `text` and/or `items` | One collapsed note that belongs inside this stop. The body has no limit. Detail that is not tied to one stop goes in `reference`. |
| `glossary` | `terms`: 1 to 4 of `{ "term", "definition" }` | The terms the page relies on, each defined once. `term` is 4 words, `definition` 16. |
| `svg` | `svg` (one `<svg>` element as a string), `caption` (required) | A bespoke diagram the other blocks cannot draw. |

### Icons

`icon` fields take one name from this closed set; any other name is rejected with the list. An icon is always drawn next to its text label and is hidden from screen readers, so it never carries meaning alone.

`arrow-down`, `arrow-up`, `ban`, `bolt`, `bug`, `calendar`, `chart`, `check`, `check-circle`, `circle`, `clock`, `cloud`, `code`, `cross`, `cross-circle`, `database`, `file`, `filter`, `flag`, `gear`, `info`, `key`, `lightbulb`, `link`, `lock`, `mail`, `minus`, `money`, `pause`, `plus`, `question`, `repeat`, `rocket`, `search`, `server`, `shield`, `table`, `trash`, `user`, `users`, `warning`.

States are drawn as icons in their own colour, so they differ in shape as well as colour: `good` and `done` a ticked circle, `bad` a crossed circle, `warn` a warning triangle, `info` an "i", `open` an empty circle, `blocked` a barred circle.

### Rules for the `svg` block

The script rejects the fragment, naming the problem, if it breaks any of these:

- It must be exactly one `<svg>` element with nothing after it.
- Allowed elements: `svg`, `g`, `defs`, `marker`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `path`, `text`, `tspan`, `linearGradient`, `radialGradient`, `stop`, `use`, `symbol`, `clipPath`, `mask`, `pattern`. No `script`, `style`, `foreignObject`, `a`, `image`, `title` or `desc`, and no comments, CDATA or declarations (anything starting with `<!`).
- No `on...` event attributes and no `style` attribute (use presentation attributes such as `fill` and `font-size`). `href` and `xlink:href` must start with `#`. `url(...)` may only point at `#id`. No URLs anywhere, and no backslashes in attribute values.
- Write `<` in text as `&lt;`; a literal `<` is rejected.

Draw strokes and text in `currentColor` so the diagram follows the light and dark themes. Set a `viewBox` and leave out `width` and `height`. Add `role="img"` and an `aria-label` that states what the picture shows; use `aria-label` rather than a `<title>` element. `xmlns` attributes are removed automatically.

## Complete example

```json
{
  "title": "How Connection Pooling Works",
  "page_type": "concept",
  "gist": {"kind": "chain", "nodes": [
    {"icon": "user", "label": "Request needs the database"},
    {"icon": "repeat", "label": "Pool lends a connection", "arrow": "acquire"},
    {"icon": "bolt", "label": "Query in 2 ms", "arrow": "skips the login", "outcome": true}
  ]},
  "bottom_line": "A connection pool keeps a few database connections open and lends them out, so each request skips the slow step of opening one.",
  "sections": [
    {"heading": "Opening a connection is the slow part", "short": "What it saves", "blocks": [
      {"type": "text", "text": "Opening a connection takes a network round trip, a login and some setup on the server. A **connection pool** opens a few once and reuses them."},
      {"type": "bar_chart", "title": "Time per request", "unit": " ms", "items": [
        {"label": "New connection every time", "value": 32},
        {"label": "Borrowed from the pool", "value": 2}
      ], "caption": "Most of the time without a pool goes into opening the connection."},
      {"type": "glossary", "terms": [
        {"term": "Connection", "definition": "An open, logged-in link between your app and the database."},
        {"term": "Pool size", "definition": "How many connections the pool keeps open at most."}
      ]}
    ]},
    {"heading": "A request borrows, uses and returns a connection", "short": "One request", "blocks": [
      {"type": "flow", "title": "Where a request goes", "nodes": [
        {"id": "req", "label": "Request"},
        {"id": "pool", "label": "Pool"},
        {"id": "idle", "label": "Idle connection"},
        {"id": "wait", "label": "Wait in line"},
        {"id": "db", "label": "Database"}
      ], "edges": [
        {"from": "req", "to": "pool", "label": "acquire"},
        {"from": "pool", "to": "idle", "label": "one is free"},
        {"from": "pool", "to": "wait", "label": "all busy"},
        {"from": "idle", "to": "db", "label": "query"},
        {"from": "wait", "to": "db", "label": "when one frees"}
      ], "caption": "A request only waits when every connection is already lent out."},
      {"type": "text", "text": "Your code calls `pool.acquire()` instead of opening a connection, and `pool.release()` hands it back, still open, for the next request."},
      {"type": "check", "question": "The pool size is 10 and 10 requests are running. What happens to the eleventh?", "answer": "It waits until one of the ten releases its connection. The pool does not open an eleventh."}
    ]},
    {"heading": "A bigger pool is not always faster", "short": "Pool size", "blocks": [
      {"type": "cards", "cards": [
        {"title": "Pool of 200", "state": "bad", "points": [{"sign": "+", "text": "Requests never wait for a connection"}, {"sign": "-", "text": "The database juggles 200 queries"}]},
        {"title": "Pool of 20", "state": "good", "points": [{"sign": "+", "text": "Each query runs at full speed"}, {"sign": "-", "text": "A few requests wait briefly"}]}
      ], "caption": "Same traffic, two pool sizes."},
      {"type": "stats", "items": [
        {"value": "2 × cores", "label": "A common starting pool size", "icon": "server", "note": "cores of the database server"}
      ]},
      {"type": "text", "text": "Raise the size only when requests are seen waiting and the database is not busy."}
    ]}
  ],
  "reference": [
    {"title": "Tuning the size", "items": [
      "Watch how long requests wait for a connection.",
      "Lower the size if the database is busy and queries are slowing down.",
      "Every app instance has its own pool, so the totals add up across instances."
    ]}
  ],
  "also_worth_knowing": [
    "Serverless functions often cannot keep a pool between calls; a separate pooler such as PgBouncer fills that gap."
  ],
  "next_action": {
    "text": "Find the pool size setting in your app's database config and write down its current value.",
    "detail": "With that number and your instance count, you can see how many connections the database really holds."
  },
  "sources": [
    {"label": "PostgreSQL documentation: connection settings", "url": "https://www.postgresql.org/docs/current/runtime-config-connection.html"}
  ]
}
```
