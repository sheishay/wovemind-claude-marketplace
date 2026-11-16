# Page spec format

The page spec is one JSON file. `scripts/build_page.py <spec.json> <out.html>` validates it, renders the page, and prints the page's visible text to stdout. If the spec is invalid, the script exits with status 1 and names the bad field, for example `invalid spec: spec.sections[1].blocks[0].items[2].value: expected a number`. Fix that field and run it again.

All text is HTML-escaped. Inside any text except chart and flow labels (which are drawn as SVG and show markup literally) you may use two kinds of inline markup: `` `code` `` for commands, paths and identifiers, and `**bold**` for the one term a paragraph defines. A blank line inside a `text` value starts a new paragraph. Text may not contain `{{` or `}}`.

## Top level

| Field | Required | What it holds |
|---|---|---|
| `title` | yes | The page name, two to four words. It becomes the browser tab and gallery title. |
| `page_type` | yes | `concept`, `research`, `work-summary` or `how-to`. Shown above the title. |
| `bottom_line` | yes | One or two short sentences, 35 words at most: the single thing to remember. Rendered as the bottom-line card under the title. |
| `sections` | yes | List of `{ "heading": "...", "blocks": [ ... ] }`. One main idea per section. Each section appears in the "On this page" nav. |
| `also_worth_knowing` | no | List of short strings: tangents and side notes, shown in a collapsed block after the last section. |
| `next_action` | yes | `{ "text": "...", "detail": "..." }`. `text` is one concrete action the reader can take now; `detail` (optional) says why or how. |
| `sources` | no | List of `{ "label": "...", "url": "https://..." }`. `url` is optional and must be `http://` or `https://`. These are the only links the page may contain. Leave the key out, or use `[]`, when there are none. |

The script adds the reading time (about 200 words per minute over the first read, which leaves out collapsed text), the scroll progress bar and the section nav itself.

## Blocks

Every block has a `type`. Optional fields can be left out.

| `type` | Fields | Use it for |
|---|---|---|
| `text` | `text` | Prose. Keep paragraphs to two or three sentences. |
| `list` | `items` (strings), `ordered` (bool, optional) | Parallel points. The first four show; the rest go into a collapsed "N more" automatically. |
| `stepper` | `steps`: `[{ "title", "text", "block" (optional, any block) }]` | A process or a change over time. Shows one step at a time with Back, Next and Start over. All steps show when printed or without JavaScript. |
| `table` | `columns` (strings), `rows` (lists of strings, same length as `columns`); `columns[0]` may be `""` when the first column holds row labels; each cell is 14 words at most, `highlight_column` (index, optional), `caption` (optional) | Comparing options across the same criteria. The first cell of each row is the row header. Highlight the recommended option's column. |
| `bar_chart` | `items`: `[{ "label", "value" }]`, `title`, `unit`, `caption` (all optional except `items`) | Quantities that compare by size. Values must be zero or more, with at least one above zero; the axis starts at zero. Each bar is labelled directly. |
| `dot_chart` | `items`: `[{ "label", "value" }]`, `min`, `max`, `title`, `unit`, `caption` | Values on a shared scale that need not start at zero, such as scores, rates or values that can be negative. `min` and `max` default to the smallest and largest value; `max` must be greater than `min`, and every value must lie between them. |
| `flow` | `nodes`: `[{ "id", "label" }]`, `edges`: `[{ "from", "to", "label" }]`, `title`, `caption` | Boxes and arrows, laid out top to bottom by the script. Handles chains and simple branching. Node ids must be unique and every edge must name existing ids. Loops are rejected: use a `stepper` or an `svg` block for those. Label the arrows with what moves or happens. |
| `timeline` | `items`: `[{ "when", "title", "text" (optional) }]` | Dated or ordered events. |
| `before_after` | `before`: `{ "label", "text" }`, `after`: `{ "label", "text" }`, `caption` | One thing in two states. `label` defaults to Before and After. |
| `check` | `question`, `answer` | A click-to-reveal "Check yourself" prompt. Concept pages only. |
| `details` | `summary`, `text` and/or `items` | Collapsed detail the main line does not need. |
| `glossary` | `terms`: `[{ "term", "definition" }]` | A strip of the terms the page relies on, each defined once. |
| `svg` | `svg` (one `<svg>` element as a string), `caption` (required) | A bespoke diagram the other blocks cannot draw. |

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
  "bottom_line": "A connection pool keeps a few database connections open and lends them out, so each request skips the slow step of opening a new one.",
  "sections": [
    {
      "heading": "What a pool saves you",
      "blocks": [
        {"type": "text", "text": "Opening a database connection takes about 30 milliseconds: a network round trip, a login, and some setup on the server. Running a simple query on an open connection takes about 2 milliseconds.\n\nA **connection pool** opens a handful of connections once, then hands one to each request and takes it back when the request is done."},
        {"type": "bar_chart", "title": "Time per request", "unit": " ms", "items": [
          {"label": "New connection every time", "value": 32},
          {"label": "Borrowed from the pool", "value": 2}
        ], "caption": "Most of the time without a pool goes into opening the connection, not running the query."},
        {"type": "glossary", "terms": [
          {"term": "Connection", "definition": "An open, logged-in link between your app and the database."},
          {"term": "Pool", "definition": "A fixed set of connections your app reuses."},
          {"term": "Pool size", "definition": "How many connections the pool keeps open at most."}
        ]}
      ]
    },
    {
      "heading": "What happens to one request",
      "blocks": [
        {"type": "stepper", "steps": [
          {"title": "The request asks for a connection", "text": "Your code calls `pool.acquire()` instead of opening a connection."},
          {"title": "The pool lends an idle one", "text": "If a connection is free, the pool hands it over at once. If all are busy, the request waits in line."},
          {"title": "The query runs", "text": "The request uses the connection exactly as it would use one it had opened itself."},
          {"title": "The connection goes back", "text": "`pool.release()` returns the connection, still open, for the next request."}
        ]},
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
          {"from": "wait", "to": "db", "label": "when one frees up"}
        ], "caption": "A request only waits when every connection in the pool is already lent out."},
        {"type": "check", "question": "The pool size is 10 and 10 requests are running. What happens to the eleventh?", "answer": "It waits until one of the ten releases its connection. The pool does not open an eleventh connection."}
      ]
    },
    {
      "heading": "Choosing a pool size",
      "blocks": [
        {"type": "text", "text": "A bigger pool is not always faster. The database can only run so many queries at once, and every extra connection uses memory on the server."},
        {"type": "before_after",
          "before": {"label": "Pool of 200", "text": "Requests never wait for a connection, but the database spends its time switching between 200 queries and each one gets slower."},
          "after": {"label": "Pool of 20", "text": "A few requests wait a millisecond or two, and the database runs each query at full speed."},
          "caption": "Same traffic, two pool sizes."},
        {"type": "table", "columns": ["Setting", "Too small", "About right", "Too large"], "rows": [
          ["Waiting for a connection", "Often", "Rare and short", "Never"],
          ["Database load", "Low", "Steady", "Overloaded"],
          ["Memory on the server", "Low", "Moderate", "High"]
        ], "highlight_column": 2, "caption": "Start small and raise the size only when requests are seen waiting."},
        {"type": "list", "items": [
          "Start with about twice the number of CPU cores on the database server.",
          "Watch how long requests wait for a connection.",
          "Raise the size only if waits are frequent and the database is not busy.",
          "Lower it if the database is busy and queries are slowing down.",
          "Remember that every app instance has its own pool, so the totals add up."
        ]}
      ]
    }
  ],
  "also_worth_knowing": [
    "Serverless functions often cannot keep a pool between calls; a separate pooler such as PgBouncer fills that gap.",
    "A connection that sat idle for a long time can be closed by a firewall; most pools check connections before lending them."
  ],
  "next_action": {
    "text": "Find the pool size setting in your app's database config and write down its current value.",
    "detail": "With that number and your instance count, you can see how many connections the database is really holding open."
  },
  "sources": [
    {"label": "PostgreSQL documentation: connection settings", "url": "https://www.postgresql.org/docs/current/runtime-config-connection.html"}
  ]
}
```
