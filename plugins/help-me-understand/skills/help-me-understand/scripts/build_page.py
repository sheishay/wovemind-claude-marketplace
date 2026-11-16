#!/usr/bin/env python3
"""Render a help-me-understand page spec into one self-contained HTML file.

Usage:
    build_page.py <spec.json> <out.html>
    build_page.py --selftest

The spec format is described in references/spec-schema.md. All spec text is
HTML-escaped; the only raw passthrough is the "svg" block, which is parsed and
checked against an element and attribute allowlist first. Charts, chains, icon
arrays and flow diagrams are drawn here as inline SVG or HTML, and icons come
from a closed built-in set, so the page needs no library and no external file.

Every text field has a word limit, enforced here with an error that names the
field, because limits written only as guidance did not change what got written.

After writing the page, the script prints the page's visible text to stdout,
so the naive-reader check can be given exactly what a reader would see, and a
one-line word balance to stderr. Standard library only; runs on Python 3.8+.
"""

import json
import math
import os
import re
import sys
import tempfile
from html import escape as _escape
from html.parser import HTMLParser

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "page-template.html")
WORDS_PER_MINUTE = 200
VISIBLE_ITEMS = 4
PAGE_TYPES = ("concept", "research", "work-summary", "how-to")
# What the line under the bottom line says, per page type: that this is the whole point, and what the stops add.
STOP_LINE = {"concept": ("That is the whole idea.", "why"), "research": ("That is the answer.", "why"),
             "work-summary": ("That is the whole picture.", "the detail"), "how-to": ("That is the whole task.", "how")}

# Word limits, by the field they apply to. Each is enforced with an error naming the field.
LIMITS = {
    "bottom_line": 25, "heading": 9, "short": 3, "caption": 18, "title": 18, "unit": 3,
    "section_prose": 60, "text": 40, "step_title": 8, "step_text": 28, "term": 4, "definition": 16,
    "question": 25, "ba_text": 25, "ba_label": 4, "tl_when": 4, "tl_title": 8, "tl_text": 18, "item": 16,
    "cell": 14, "next_text": 22, "next_detail": 25, "also": 30, "summary": 10, "chart_label": 8,
    "flow_label": 8, "edge_label": 4, "node_label": 4, "arrow": 3, "node_note": 12, "winner_name": 4,
    "winner_reason": 6, "alt_name": 4, "why_not": 5, "tally_label": 3, "stat_label": 6, "stat_note": 8,
    "ia_label": 10, "card_title": 5, "card_text": 14, "point": 8,
}
MAX_SECTIONS, MAX_TEXT_BLOCKS, MAX_DETAILS = 5, 2, 1
MAX_LIST_ITEMS, MAX_TERMS, MAX_COLS, MAX_ROWS = 6, 4, 5, 6
STAT_CHARS, ICON_ARRAY_TOTAL = 12, 100
# Blocks that are reading text or collapsed; every other block is a visual, and each section needs one.
NOT_VISUAL = {"text", "list", "details", "check", "glossary"}
STATES = {"good": "check-circle", "bad": "cross-circle", "warn": "warning", "info": "info",
          "done": "check-circle", "open": "circle", "blocked": "ban"}
TALLY_STATES = ("done", "open", "blocked", "info")
# Keys whose values are never shown as reading text.
NOT_TEXT = ("type", "id", "from", "to", "url", "svg", "page_type", "kind", "icon", "state", "sign")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

# A closed set of 24-unit line icons, drawn with the current text colour. Names are looked up here and never
# interpolated into markup, so the spec cannot inject SVG through an icon name.
ICONS = {
    "arrow-down": '<path d="M12 4v16M5.5 13.5 12 20l6.5-6.5"/>',
    "arrow-up": '<path d="M12 20V4M5.5 10.5 12 4l6.5 6.5"/>',
    "ban": '<circle cx="12" cy="12" r="9"/><path d="M5.7 5.7l12.6 12.6"/>',
    "bolt": '<path d="M13 2.5 4.5 14H11l-1 7.5L18.5 10H12l1-7.5z"/>',
    "bug": '<rect x="7" y="7" width="10" height="13" rx="5"/><path d="M12 11v9M7 12H3.5M20.5 12H17M7 16.5H4M20 16.5h-3M9.5 7 8 4M14.5 7 16 4"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "chart": '<path d="M3.5 3.5v17h17"/><path d="M8 16.5v-4M12.5 16.5V8M17 16.5v-6"/>',
    "check": '<path d="M4.5 12.5l5 5 10-11"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.8 2.8L16.3 9.3"/>',
    "circle": '<circle cx="12" cy="12" r="9"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    "cloud": '<path d="M7 19a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 9.2 4.5 4.5 0 0 1 17.5 19H7z"/>',
    "code": '<path d="M8.5 7l-5 5 5 5M15.5 7l5 5-5 5"/>',
    "cross": '<path d="M6 6l12 12M18 6 6 18"/>',
    "cross-circle": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/><path d="M4.5 5.5v13c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-13"/><path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/>',
    "file": '<path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8l-5-5z"/><path d="M14 3v5h5"/>',
    "filter": '<path d="M3.5 4.5h17l-6.5 8v6l-4 2v-8l-6.5-8z"/>',
    "flag": '<path d="M5.5 21V3.5M5.5 4h12l-2.5 4.5 2.5 4.5h-12"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="6.5"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.4"/>',
    "key": '<circle cx="8" cy="15.5" r="4.5"/><path d="M11.3 12.2 20 3.5M16.5 7l2.5 2.5M14.3 9.2l2 2"/>',
    "lightbulb": '<path d="M9.5 18h5M10.5 21.5h3M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.5.4.8 1 .8 1.7v.5h6V16c0-.7.3-1.3.8-1.7A6.5 6.5 0 0 0 12 2.5z"/>',
    "link": '<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1"/><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="10" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
    "minus": '<path d="M5 12h14"/>',
    "money": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 9.5v5M18 9.5v5"/>',
    "pause": '<circle cx="12" cy="12" r="9"/><path d="M10 9v6M14 9v6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.5a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .9-1 1.6v.6M12 16.8v.4"/>',
    "repeat": '<path d="M4 11V9.5A3.5 3.5 0 0 1 7.5 6H20M16.5 2.5 20 6l-3.5 3.5M20 13v1.5a3.5 3.5 0 0 1-3.5 3.5H4M7.5 21.5 4 18l3.5-3.5"/>',
    "rocket": '<path d="M12 2.5c2.8 2.3 4.3 5.6 4.3 9.5l-1.8 3.8h-5L7.7 12c0-3.9 1.5-7.2 4.3-9.5z"/><circle cx="12" cy="10" r="1.8"/><path d="M7.9 12.5 5 15.5v3l4-1.7M16.1 12.5l2.9 3v3l-4-1.7M10.3 19l1.7 2.5 1.7-2.5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20.5 20.5l-4.5-4.5"/>',
    "server": '<rect x="3.5" y="3.5" width="17" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="17" height="7" rx="1.5"/><path d="M7.5 7h.01M7.5 17h.01"/>',
    "shield": '<path d="M12 2.5 4.5 5.5v6c0 4.8 3.2 8.4 7.5 10 4.3-1.6 7.5-5.2 7.5-10v-6L12 2.5z"/>',
    "table": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10"/>',
    "trash": '<path d="M4 6.5h16M9.5 6.5V4h5v2.5M6 6.5l1 14h10l1-14M10 10.5v6M14 10.5v6"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.5a3.5 3.5 0 0 1 0 7M18 14.2c2.1.7 3.5 2.8 3.5 5.8"/>',
    "warning": '<path d="M12 3.5 2.5 20h19L12 3.5z"/><path d="M12 10v4.5M12 17.3v.4"/>',
}


class SpecError(ValueError):
    pass


# ---------------------------------------------------------------- validation

def need(obj, key, path, kind=str, optional=False):
    """Return obj[key] after checking its type; raise SpecError naming the field."""
    where = "%s.%s" % (path, key)
    if not isinstance(obj, dict):
        raise SpecError("%s: expected an object" % path)
    if key not in obj or obj[key] is None:
        if optional:
            return None
        raise SpecError("%s: missing" % where)
    val = obj[key]
    if kind is float:
        # The bound check also rejects NaN, infinity and integers too large for a float.
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not abs(val) <= sys.float_info.max:
            raise SpecError("%s: expected a number" % where)
    elif kind is list:
        if not isinstance(val, list) or not val:
            raise SpecError("%s: expected a non-empty list" % where)
    elif kind is dict:
        if not isinstance(val, dict):
            raise SpecError("%s: expected an object" % where)
    elif kind is bool:
        if not isinstance(val, bool):
            raise SpecError("%s: expected true or false" % where)
    elif kind is str:
        text_at(val, where)
    return val


def text_at(val, where, limit=None):
    """Check one text value, such as a list item, and its word limit when it has one."""
    if not isinstance(val, str) or not val.strip():
        raise SpecError("%s: expected non-empty text" % where)
    if "{{" in val or "}}" in val:
        raise SpecError("%s: text may not contain '{{' or '}}'" % where)
    if limit is not None and len(val.split()) > limit:
        raise SpecError("%s: keep it to %d words or fewer (got %d); move the rest into a details block or the "
                        "top-level reference list" % (where, limit, len(val.split())))
    return val


def capped(obj, key, path, limit, optional=False):
    """need() for a text field with a word limit; limit is a key of LIMITS."""
    val = need(obj, key, path, optional=optional)
    return None if val is None else text_at(val, "%s.%s" % (path, key), LIMITS[limit])


def sized(obj, key, path, lo, hi):
    """need() for a list whose length must lie between lo and hi."""
    val = need(obj, key, path, list)
    if not lo <= len(val) <= hi:
        raise SpecError("%s.%s: expected %d to %d entries (got %d)" % (path, key, lo, hi, len(val)))
    return val


def whole(obj, key, path, lo, hi):
    """need() for a whole number between lo and hi."""
    val = need(obj, key, path, float)
    if val != int(val) or not lo <= val <= hi:
        raise SpecError("%s.%s: expected a whole number from %d to %d" % (path, key, lo, hi))
    return int(val)


def check_url(url, path):
    # \Z rather than $, which would also accept a trailing newline.
    if not re.match(r"https?://[^\s\"'<>]+\Z", url):
        raise SpecError("%s: source links must be http:// or https:// URLs" % path)
    return url


def icon(name, where):
    """Return the inline SVG for a built-in icon; reject any name outside the set."""
    if not isinstance(name, str) or name not in ICONS:
        raise SpecError("%s: unknown icon %r (expected one of %s)" % (where, name, ", ".join(sorted(ICONS))))
    return '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false">%s</svg>' % ICONS[name]


def state_of(obj, path, allowed, optional=True):
    st = need(obj, "state", path, optional=optional)
    if st is not None and st not in allowed:
        raise SpecError("%s.state: expected one of %s" % (path, ", ".join(allowed)))
    return st


# ---------------------------------------------------------------- text helpers

def esc(text):
    return _escape(text, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def inline(text):
    """Escape text, then allow `code` and **bold** as the only inline markup."""
    # Odd parts are code spans, which stay literal so ** inside code is not turned bold.
    parts = re.split(r"`([^`]+)`", esc(text))
    return "".join("<code>%s</code>" % s if i % 2 else re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
                   for i, s in enumerate(parts))


def paras(text):
    return "".join("<p>%s</p>" % inline(p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip())


def wrap(text, width):
    """Greedy word wrap for SVG labels; a word longer than width is split so it stays inside the box."""
    lines, cur = [], ""
    for word in (w[i:i + width] for w in text.split() for i in range(0, len(w), width)):
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(cur)
    return lines


def fmt(n):
    """Format a chart value with thousands separators, so 8000000 reads as 8,000,000."""
    if float(n).is_integer():
        return "{:,d}".format(int(n))
    # Two significant digits below 1, so 0.004 does not round to 0.
    places = max(2, 1 - int(math.floor(math.log10(abs(n)))))
    return "{:,.{}f}".format(n, places).rstrip("0").rstrip(".")


def figure(inner, caption, cls):
    cap = "<figcaption>%s</figcaption>" % inline(caption) if caption else ""
    return '<figure class="%s">%s%s</figure>' % (cls, inner, cap)


def sr(text):
    return '<span class="sr">%s</span>' % esc(text)


# ---------------------------------------------------------------- components

def r_text(b, p):
    return paras(capped(b, "text", p, "text"))


def r_list(b, p):
    items = sized(b, "items", p, 1, MAX_LIST_ITEMS)
    lis = ["<li>%s</li>" % inline(text_at(it, "%s.items[%d]" % (p, n), LIMITS["item"])) for n, it in enumerate(items)]
    tag = "ol" if b.get("ordered") else "ul"
    html = "<%s class=\"list\">%s</%s>" % (tag, "".join(lis[:VISIBLE_ITEMS]), tag)
    if len(lis) > VISIBLE_ITEMS:
        rest = len(lis) - VISIBLE_ITEMS
        start = ' start="%d"' % (VISIBLE_ITEMS + 1) if tag == "ol" else ""
        html += '<details class="more"><summary>%d more</summary><%s class="list"%s>%s</%s></details>' % (
            rest, tag, start, "".join(lis[VISIBLE_ITEMS:]), tag)
    return html


def r_stepper(b, p):
    steps = need(b, "steps", p, list)
    out = []
    for n, s in enumerate(steps):
        sp = "%s.steps[%d]" % (p, n)
        body = paras(capped(s, "text", sp, "step_text"))
        if s.get("block") is not None:
            body += render_block(need(s, "block", sp, dict), sp + ".block")
        out.append('<li class="step"><h4><span class="num">%d</span>%s</h4>%s</li>' % (
            n + 1, inline(capped(s, "title", sp, "step_title")), body))
    return '<div class="stepper" data-stepper><ol class="steps">%s</ol></div>' % "".join(out)


def r_table(b, p):
    cols = sized(b, "columns", p, 1, MAX_COLS)
    rows = sized(b, "rows", p, 1, MAX_ROWS)
    hl = b.get("highlight_column")
    if hl is not None and (isinstance(hl, bool) or not isinstance(hl, int) or not 0 <= hl < len(cols)):
        raise SpecError("%s.highlight_column: expected a column index from 0 to %d" % (p, len(cols) - 1))

    def cell_text(text, path):
        if isinstance(text, str) and len(text.split()) > LIMITS["cell"]:
            raise SpecError("%s: keep table cells to %d words or fewer; put sentences in a text block" % (path, LIMITS["cell"]))
        return text_at(text, path)

    def cell(tag, text, i, path):
        cls = ' class="hl"' if i == hl else ""
        scope = ' scope="col"' if tag == "th" else ""
        return "<%s%s%s>%s</%s>" % (tag, cls, scope, inline(cell_text(text, path)), tag)

    corner = '<th scope="col"></th>' if cols[0] == "" else None
    head = "".join(corner if i == 0 and corner else cell("th", c, i, "%s.columns[%d]" % (p, i)) for i, c in enumerate(cols))
    body = []
    for r, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(cols):
            raise SpecError("%s.rows[%d]: expected a list of %d cells" % (p, r, len(cols)))
        tds = []
        for i, c in enumerate(row):
            path = "%s.rows[%d][%d]" % (p, r, i)
            if i == 0:
                tds.append('<th scope="row"%s>%s</th>' % (' class="hl"' if hl == 0 else "", inline(cell_text(c, path))))
            else:
                tds.append(cell("td", c, i, path))
        body.append("<tr>%s</tr>" % "".join(tds))
    table = '<div class="scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, "".join(body))
    return figure(table, b.get("caption"), "tablefig")


def chart_items(b, p):
    items = need(b, "items", p, list)
    return [(capped(it, "label", "%s.items[%d]" % (p, n), "chart_label"), need(it, "value", "%s.items[%d]" % (p, n), float))
            for n, it in enumerate(items)]


ROW = 46  # pixel height of one chart row: a label line above its mark


def r_bar_chart(b, p):
    items = chart_items(b, p)
    if any(v < 0 for _, v in items):
        raise SpecError("%s.items: bar values must be zero or more (use a dot chart for negative values)" % p)
    top = max(v for _, v in items)
    if top == 0:
        raise SpecError("%s.items: at least one bar value must be above zero" % p)
    unit = b.get("unit") or ""
    rows = []
    for n, (label, v) in enumerate(items):
        y = n * ROW
        w = 82.0 * v / top  # leaves room on the right for the value label
        # A long bar carries its value inside its end, so a long number cannot run past a narrow screen's edge.
        inside = w > 60
        rows.append(
            '<text class="lbl" x="0" y="%d">%s</text>'
            '<rect class="bar" x="0" y="%d" width="%.2f%%" height="14" rx="2"></rect>'
            '<text class="val%s" x="%.2f%%" y="%d" dx="%d"%s>%s</text>'
            % (y + 14, esc(label), y + 22, w, " in" if inside else "", w, y + 34, -6 if inside else 6,
               ' text-anchor="end"' if inside else "", esc(fmt(v) + unit)))
    h = len(items) * ROW
    svg = ('<svg class="chart" width="100%%" height="%d" role="img" aria-label="%s">%s'
           '<line class="axis" x1="0" y1="18" x2="0" y2="%d"></line></svg>') % (
        h, esc(b.get("title") or "Bar chart"), "".join(rows), h - 6)
    return figure(title_html(b) + svg, b.get("caption"), "chartfig")


def r_dot_chart(b, p):
    items = chart_items(b, p)
    lo, hi = need(b, "min", p, float, optional=True), need(b, "max", p, float, optional=True)
    lo = min(v for _, v in items) if lo is None else lo
    hi = max(v for _, v in items) if hi is None else hi
    if hi <= lo:
        raise SpecError("%s: max must be greater than min (set min and max when all values are equal)" % p)
    if any(v < lo or v > hi for _, v in items):
        raise SpecError("%s.items: every value must lie between min and max" % p)
    unit = b.get("unit") or ""
    rows, row_h = [], 58  # label line, value line above the dot, then the track
    for n, (label, v) in enumerate(items):
        y = n * row_h
        x = 2 + 90.0 * (v - lo) / (hi - lo)
        anchor = "start" if x < 10 else ("end" if x > 84 else "middle")
        rows.append(
            '<text class="lbl" x="0" y="%d">%s</text>'
            '<text class="val" x="%.2f%%" y="%d" text-anchor="%s">%s</text>'
            '<line class="track" x1="2%%" y1="%d" x2="92%%" y2="%d"></line>'
            '<circle class="dot" cx="%.2f%%" cy="%d" r="6"></circle>'
            % (y + 14, esc(label), x, y + 32, anchor, esc(fmt(v) + unit), y + 44, y + 44, x, y + 44))
    h = len(items) * row_h
    scale = ('<text class="tick" x="2%%" y="%d">%s</text><text class="tick" x="92%%" y="%d" text-anchor="end">%s</text>'
             % (h + 10, esc(fmt(lo) + unit), h + 10, esc(fmt(hi) + unit)))
    svg = '<svg class="chart" width="100%%" height="%d" role="img" aria-label="%s">%s%s</svg>' % (
        h + 16, esc(b.get("title") or "Dot chart"), "".join(rows), scale)
    return figure(title_html(b) + svg, b.get("caption"), "chartfig")


def title_html(b):
    t = b.get("title")
    return '<div class="figtitle">%s</div>' % inline(t) if t else ""


NODE_W, LINE_H, GAP_X, GAP_Y, PAD = 168, 16, 36, 56, 8


def r_flow(b, p):
    nodes = need(b, "nodes", p, list)
    edges = b.get("edges") or []
    if not isinstance(edges, list):
        raise SpecError("%s.edges: expected a list" % p)
    ids, labels = [], {}
    for n, nd in enumerate(nodes):
        np_ = "%s.nodes[%d]" % (p, n)
        nid = need(nd, "id", np_)
        if nid in labels:
            raise SpecError("%s.id: duplicate node id %r" % (np_, nid))
        ids.append(nid)
        labels[nid] = wrap(capped(nd, "label", np_, "flow_label"), 20)
    out = {i: [] for i in ids}
    indeg = {i: 0 for i in ids}
    for n, e in enumerate(edges):
        ep = "%s.edges[%d]" % (p, n)
        a, z = need(e, "from", ep), need(e, "to", ep)
        for key, v in (("from", a), ("to", z)):
            if v not in labels:
                raise SpecError("%s.%s: no node with id %r" % (ep, key, v))
        capped(e, "label", ep, "edge_label", optional=True)
        out[a].append(z)
        indeg[z] += 1
    # Layer each node by its longest path from a start node (Kahn's algorithm).
    layer = {i: 0 for i in ids}
    queue = [i for i in ids if indeg[i] == 0]
    seen = 0
    while queue:
        cur = queue.pop(0)
        seen += 1
        for nxt in out[cur]:
            layer[nxt] = max(layer[nxt], layer[cur] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen != len(ids):
        raise SpecError("%s.edges: the flow has a loop; draw loops with a stepper or an svg block" % p)
    rows = {}
    for i in ids:
        rows.setdefault(layer[i], []).append(i)
    widest = max(len(r) for r in rows.values())
    width = widest * NODE_W + (widest - 1) * GAP_X + 2 * PAD
    heights = {i: len(labels[i]) * LINE_H + 20 for i in ids}
    pos, y = {}, PAD
    for lv in sorted(rows):
        row = rows[lv]
        rh = max(heights[i] for i in row)
        span = len(row) * NODE_W + (len(row) - 1) * GAP_X
        x = (width - span) / 2.0
        for i in row:
            pos[i] = (x, y + (rh - heights[i]) / 2.0)
            x += NODE_W + GAP_X
        y += rh + GAP_Y
    height = y - GAP_Y + PAD
    # ponytail: straight edges; an edge that skips a layer can cross a node. Use the svg block for dense graphs.
    parts = []
    for e in edges:
        (ax, ay), (zx, zy) = pos[e["from"]], pos[e["to"]]
        x1, y1 = ax + NODE_W / 2.0, ay + heights[e["from"]]
        x2, y2 = zx + NODE_W / 2.0, zy - 4
        parts.append('<line class="edge" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" marker-end="url(#%s-arrow)"></line>'
                     % (x1, y1, x2, y2, b["_id"]))
        if e.get("label"):
            # Put the label on the arrow's outer side, away from the diagram's centre line, so it does not sit on a sibling arrow.
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            left = mx < width / 2.0 - 1
            parts.append('<text class="elbl" x="%.1f" y="%.1f" dx="%d" text-anchor="%s">%s</text>'
                         % (mx, my + 4, -8 if left else 8, "end" if left else "start", esc(e["label"])))
    for i in ids:
        x, y0 = pos[i]
        parts.append('<rect class="node" x="%.1f" y="%.1f" width="%d" height="%d" rx="6"></rect>' % (x, y0, NODE_W, heights[i]))
        for k, line in enumerate(labels[i]):
            parts.append('<text class="nlbl" x="%.1f" y="%.1f" text-anchor="middle">%s</text>'
                         % (x + NODE_W / 2.0, y0 + 10 + LINE_H * (k + 1) - 3, esc(line)))
    defs = ('<defs><marker id="%s-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="head"></path></marker></defs>' % b["_id"])
    # A wide flow shrinks to at most three quarters of its size, so labels stay readable, and scrolls sideways past that.
    svg = ('<div class="scroll"><svg class="flow" viewBox="0 0 %d %d" style="max-width:%dpx;min-width:%dpx" role="img" aria-label="%s">%s%s</svg></div>'
           % (width, height, width, width * 3 // 4, esc(b.get("title") or "Flow diagram"), defs, "".join(parts)))
    return figure(title_html(b) + svg, b.get("caption"), "flowfig")


def r_timeline(b, p):
    items = need(b, "items", p, list)
    lis = []
    for n, it in enumerate(items):
        ip = "%s.items[%d]" % (p, n)
        when, title = capped(it, "when", ip, "tl_when"), capped(it, "title", ip, "tl_title")
        text = capped(it, "text", ip, "tl_text", optional=True)
        lis.append('<li><span class="when">%s</span><div class="what"><strong>%s</strong>%s</div></li>'
                   % (inline(when), inline(title), paras(text) if text else ""))
    return '<ol class="timeline">%s</ol>' % "".join(lis)


def r_before_after(b, p):
    sides = []
    for key, default in (("before", "Before"), ("after", "After")):
        side = need(b, key, p, dict)
        sp = "%s.%s" % (p, key)
        label = capped(side, "label", sp, "ba_label", optional=True) or default
        sides.append('<div class="ba-%s"><div class="ba-label">%s</div>%s</div>'
                     % (key, inline(label), paras(capped(side, "text", sp, "ba_text"))))
    return figure('<div class="ba">%s</div>' % "".join(sides), b.get("caption"), "bafig")


def r_check(b, p):
    return ('<details class="check"><summary><span class="ck">Check yourself</span><span class="q">%s</span></summary>'
            '<div class="answer">%s</div></details>') % (inline(capped(b, "question", p, "question")), paras(need(b, "answer", p)))


def r_details(b, p):
    inner = ""
    if b.get("text") is not None:
        inner += paras(need(b, "text", p))
    if b.get("items") is not None:
        inner += "<ul class=\"list\">%s</ul>" % "".join(
            "<li>%s</li>" % inline(text_at(it, "%s.items[%d]" % (p, n))) for n, it in enumerate(need(b, "items", p, list)))
    if not inner:
        raise SpecError("%s: needs text or items" % p)
    return '<details class="more"><summary>%s</summary>%s</details>' % (inline(capped(b, "summary", p, "summary")), inner)


def r_glossary(b, p):
    terms = sized(b, "terms", p, 1, MAX_TERMS)
    out = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (
        inline(capped(t, "term", "%s.terms[%d]" % (p, n), "term")),
        inline(capped(t, "definition", "%s.terms[%d]" % (p, n), "definition")))
        for n, t in enumerate(terms))
    return '<dl class="glossary">%s</dl>' % out


def chain_html(b, p, max_nodes, notes):
    """A row of icon-and-label nodes joined by arrows; shared by the gist and the chain block."""
    nodes = sized(b, "nodes", p, 2, max_nodes)
    parts, outcomes = [], 0
    for n, nd in enumerate(nodes):
        np_ = "%s.nodes[%d]" % (p, n)
        arrow = capped(nd, "arrow", np_, "arrow", optional=True)
        if n == 0 and arrow is not None:
            raise SpecError("%s.arrow: the first node has no arrow leading into it" % np_)
        if not notes and nd.get("note") is not None:
            raise SpecError("%s.note: notes belong to chain blocks in sections, not to the gist" % np_)
        note = capped(nd, "note", np_, "node_note", optional=True)
        out = bool(need(nd, "outcome", np_, bool, optional=True))
        outcomes += out
        if n:
            lbl = '<span class="arrow-lbl">%s</span>' % inline(arrow) if arrow else sr("leads to")
            parts.append('<div class="arrow">%s</div>' % lbl)
        parts.append('<div class="node%s"><span class="node-ic">%s</span><span class="node-txt"><span class="node-lbl">%s</span>%s</span></div>'
                     % (" out" if out else "", icon(need(nd, "icon", np_), np_ + ".icon"),
                        inline(capped(nd, "label", np_, "node_label")),
                        '<span class="node-note">%s</span>' % inline(note) if note else ""))
    if outcomes > 1:
        raise SpecError("%s.nodes: mark at most one node as the outcome" % p)
    return '<div class="chain c%d"><div class="chain-row">%s</div></div>' % (len(nodes), "".join(parts))


def r_chain(b, p):
    return figure(title_html(b) + chain_html(b, p, 5, True), b.get("caption"), "chainfig")


def r_stats(b, p):
    out = []
    for n, s in enumerate(sized(b, "items", p, 1, 3)):
        sp = "%s.items[%d]" % (p, n)
        val = need(s, "value", sp)
        if len(val) > STAT_CHARS:
            raise SpecError("%s.value: keep it to %d characters, such as \"8 million\" or \"3%%\"" % (sp, STAT_CHARS))
        ic = icon(s["icon"], sp + ".icon") if s.get("icon") is not None else ""
        note = capped(s, "note", sp, "stat_note", optional=True)
        out.append('<div class="stat"><p class="stat-v">%s</p><p class="stat-l">%s<span>%s</span></p>%s</div>'
                   % (inline(val), ic, inline(capped(s, "label", sp, "stat_label")),
                      '<p class="stat-n">%s</p>' % inline(note) if note else ""))
    return figure('<div class="stats">%s</div>' % "".join(out), b.get("caption"), "statsfig")


def r_icon_array(b, p):
    total = whole(b, "total", p, 1, ICON_ARRAY_TOTAL)
    count = whole(b, "count", p, 0, total)
    label = capped(b, "label", p, "ia_label")
    cols = 10 if total > 10 else total
    step, r = 17, 6
    dots = "".join('<circle class="%s" cx="%d" cy="%d" r="%d"></circle>' % (
        "on" if i < count else "off", r + 1 + (i % cols) * step, r + 1 + (i // cols) * step, r) for i in range(total))
    w, h = (cols - 1) * step + 2 * r + 2, (int(math.ceil(total / float(cols))) - 1) * step + 2 * r + 2
    svg = ('<svg class="dots" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">%s</svg>'
           % (w, h, w, h, esc("%d of %d: %s" % (count, total, label)), dots))
    text = '<div class="ia-text"><p class="ia-n"><strong>%d</strong> of %d</p><p>%s</p></div>' % (count, total, inline(label))
    return figure('<div class="ia">%s%s</div>' % (svg, text), b.get("caption"), "iafig")


def r_cards(b, p):
    out = []
    for n, c in enumerate(sized(b, "cards", p, 2, 4)):
        cp = "%s.cards[%d]" % (p, n)
        st = state_of(c, cp, tuple(STATES))
        mark = (icon(STATES[st], cp) + sr("(%s)" % st)) if st else ""
        text = capped(c, "text", cp, "card_text", optional=True)
        pts = c.get("points") or []
        if not isinstance(pts, list) or len(pts) > 3:
            raise SpecError("%s.points: expected a list of at most 3 points" % cp)
        lis = []
        for k, pt in enumerate(pts):
            pp = "%s.points[%d]" % (cp, k)
            sign = need(pt, "sign", pp)
            if sign not in ("+", "-"):
                raise SpecError("%s.sign: expected \"+\" or \"-\"" % pp)
            plus = sign == "+"
            lis.append('<li class="%s">%s%s<span>%s</span></li>' % (
                "pro" if plus else "con", icon("plus" if plus else "minus", pp), sr("For:" if plus else "Against:"),
                inline(capped(pt, "text", pp, "point"))))
        out.append('<div class="card%s"><h3>%s<span>%s</span></h3>%s%s</div>' % (
            " s-" + st if st else "", mark, inline(capped(c, "title", cp, "card_title")),
            "<p>%s</p>" % inline(text) if text else "", '<ul class="points">%s</ul>' % "".join(lis) if lis else ""))
    return figure('<div class="cards n%d">%s</div>' % (len(out), "".join(out)), b.get("caption"), "cardsfig")


SVG_TAGS = {"svg", "g", "defs", "marker", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path",
            "text", "tspan", "lineargradient", "radialgradient", "stop", "use", "symbol",
            "clippath", "mask", "pattern"}
REF_ATTRS = {"href", "xlink:href", "src"}


class SvgCheck(HTMLParser):
    """Parse an svg fragment and record why it is unsafe, if it is."""

    def __init__(self):
        # Raw text, so a "<" that Python reads as text but a browser may read as a tag is visible in handle_data.
        HTMLParser.__init__(self, convert_charrefs=False)
        self.stack, self.roots, self.problem, self.trailing = [], 0, None, False

    def fail(self, msg):
        self.problem = self.problem or msg

    def handle_starttag(self, tag, attrs, closing=False):
        if not self.stack:
            self.roots += 1
            if tag != "svg":
                self.fail("the fragment must be one <svg> element")
        if tag not in SVG_TAGS:
            self.fail("element <%s> is not allowed" % tag)
        for name, val in attrs:
            val = (val or "").strip().lower().replace(" ", "")
            if name.startswith("on"):
                self.fail("event attribute %s is not allowed" % name)
            # CSS can load a resource without a plain url(...), through image-set() or an escape such as u\72l(.
            if name == "style" or "\\" in val:
                self.fail("attribute %s: style attributes and backslashes are not allowed" % name)
            if name in REF_ATTRS and not val.startswith("#"):
                self.fail("%s must point inside the svg (start with #)" % name)
            if "javascript:" in val or re.search(r"url\((?!['\"]?#)", val):
                self.fail("attribute %s may only reference ids inside the svg" % name)
        if not closing:
            self.stack.append(tag)
        elif not self.stack:
            self.trailing = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, closing=True)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.fail("unbalanced </%s>" % tag)
            return
        self.stack.pop()

    def handle_data(self, data):
        if not self.stack and data.strip():
            self.fail("text outside the <svg> element")
        # Python passes a malformed tag, such as one with an unclosed quote, through as text; a browser still builds it.
        if "<" in data:
            self.fail("a literal < in text (write &lt;) or a malformed tag")

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        self.fail("declarations are not allowed")

    def handle_pi(self, data):
        self.fail("processing instructions are not allowed")


def r_svg(b, p):
    raw = need(b, "svg", p)
    # Comments, CDATA and declarations are rejected outright: browsers and Python's parser end some of them in different places.
    if re.search(r"<\s*script|<\s*foreignobject|<\s*style|<!", raw, re.I):
        raise SpecError("%s.svg: <script>, <style>, <foreignObject>, comments and declarations are not allowed" % p)
    # Inline SVG in HTML needs no namespace declarations, and they would put URLs on the page.
    raw = re.sub(r'\s+xmlns(:\w+)?\s*=\s*("[^"]*"|\'[^\']*\')', "", raw)
    chk = SvgCheck()
    chk.feed(raw)
    chk.close()
    if chk.stack:
        chk.fail("unclosed <%s>" % chk.stack[-1])
    if chk.roots != 1 or chk.trailing:
        chk.fail("the fragment must be exactly one <svg> element")
    if chk.problem:
        raise SpecError("%s.svg: %s" % (p, chk.problem))
    if re.search(r"https?:", raw, re.I):
        raise SpecError("%s.svg: URLs are not allowed inside the svg" % p)
    return figure('<div class="scroll svgslot">%s</div>' % raw, need(b, "caption", p), "svgfig")


RENDERERS = {
    "text": r_text, "list": r_list, "stepper": r_stepper, "table": r_table, "bar_chart": r_bar_chart,
    "dot_chart": r_dot_chart, "flow": r_flow, "timeline": r_timeline, "before_after": r_before_after,
    "check": r_check, "details": r_details, "glossary": r_glossary, "svg": r_svg, "chain": r_chain,
    "stats": r_stats, "icon_array": r_icon_array, "cards": r_cards,
}
_counter = [0]


def render_block(b, p):
    kind = need(b, "type", p)
    if kind not in RENDERERS:
        raise SpecError("%s.type: unknown type %r (expected one of %s)" % (p, kind, ", ".join(sorted(RENDERERS))))
    for key in ("caption", "title", "unit"):
        capped(b, key, p, key, optional=True)
    if "ordered" in b and not isinstance(b["ordered"], bool):
        raise SpecError("%s.ordered: expected true or false" % p)
    _counter[0] += 1
    b = dict(b, _id="v%d" % _counter[0])
    return '<div class="block b-%s">%s</div>' % (kind.replace("_", "-"), RENDERERS[kind](b, p))


# ---------------------------------------------------------------- gist

def r_gist(g, p):
    kind = need(g, "kind", p)
    if kind == "chain":
        return chain_html(g, p, 4, False)
    if kind == "verdict":
        w = need(g, "winner", p, dict)
        wp = p + ".winner"
        alts = []
        for n, a in enumerate(sized(g, "alternatives", p, 1, 3)):
            ap = "%s.alternatives[%d]" % (p, n)
            alts.append('<li>%s<span><strong>%s</strong><span class="alt-why">%s</span></span></li>' % (
                icon("cross", ap) + sr("Not chosen:"), inline(capped(a, "name", ap, "alt_name")),
                inline(capped(a, "why_not", ap, "why_not"))))
        return ('<div class="verdict"><div class="win"><span class="win-ic">%s</span><div><p class="win-name">%s%s</p>'
                '<p class="win-why">%s</p></div></div><ul class="alts">%s</ul></div>') % (
            icon("check", wp), sr("Chosen:"), inline(capped(w, "name", wp, "winner_name")),
            inline(capped(w, "reason", wp, "winner_reason")), "".join(alts))
    if kind == "status":
        lis = []
        for n, t in enumerate(sized(g, "tallies", p, 2, 4)):
            tp = "%s.tallies[%d]" % (p, n)
            count = whole(t, "count", tp, 0, 10 ** 9)
            st = state_of(t, tp, TALLY_STATES, optional=False)
            lis.append('<li class="s-%s"><span class="st-n">%s</span><span class="st-l">%s<span>%s</span>%s</span></li>' % (
                st, fmt(count), icon(STATES[st], tp), inline(capped(t, "label", tp, "tally_label")), sr("(%s)" % st)))
        return '<ul class="status n%d">%s</ul>' % (len(lis), "".join(lis))
    raise SpecError("%s.kind: expected chain, verdict or status" % p)


# ---------------------------------------------------------------- word counts

def spec_words(obj):
    """Count words in every string of the spec except ids, types, icon names, URLs and raw svg."""
    if isinstance(obj, str):
        return len(obj.split())
    if isinstance(obj, list):
        return sum(spec_words(x) for x in obj)
    if isinstance(obj, dict):
        return sum(spec_words(v) for k, v in obj.items() if k not in NOT_TEXT)
    return 0


def first_read_words(obj):
    """Count the words a reader sees without opening anything collapsed."""
    if isinstance(obj, dict):
        if obj.get("type") == "details":
            return spec_words(obj.get("summary"))
        if obj.get("type") == "list":
            return spec_words((obj.get("items") or [])[:VISIBLE_ITEMS])
        return sum(first_read_words(v) if isinstance(v, (dict, list)) else spec_words(v) for k, v in obj.items()
                   if k not in NOT_TEXT + ("answer", "also_worth_knowing", "sources", "reference"))
    if isinstance(obj, list):
        return sum(first_read_words(x) for x in obj)
    return spec_words(obj)


def prose_words(block):
    """First-read words in text blocks and visible list items, including those nested in stepper steps."""
    kind = block.get("type") if isinstance(block, dict) else None
    if kind in ("text", "list"):
        return first_read_words(block)
    if kind == "stepper":
        return sum(prose_words(s.get("block")) for s in block.get("steps") or [] if isinstance(s, dict))
    return 0


def balance(spec):
    """Return (first read, prose, words in visuals, visual block count, collapsed) for the stderr line."""
    blocks = [b for s in spec["sections"] for b in s["blocks"]]
    visuals = [b for b in blocks if b["type"] not in NOT_VISUAL]
    first = first_read_words(spec)
    prose = sum(prose_words(b) for b in blocks)
    in_visuals = first_read_words(spec["gist"]) + sum(first_read_words(b) - prose_words(b) for b in visuals)
    return first, prose, in_visuals, len(visuals), spec_words(spec) - first


# ---------------------------------------------------------------- page

def check_section(s, sp):
    blocks = need(s, "blocks", sp, list)
    kinds = [need(b, "type", "%s.blocks[%d]" % (sp, i)) for i, b in enumerate(blocks)]
    if all(k in NOT_VISUAL for k in kinds):
        raise SpecError("%s.blocks: every section needs at least one visual block (anything except %s); turn the "
                        "sentence that carries a number, proportion, mechanism or comparison into one" % (sp, ", ".join(sorted(NOT_VISUAL))))
    if kinds.count("text") > MAX_TEXT_BLOCKS:
        raise SpecError("%s.blocks: at most %d text blocks per section" % (sp, MAX_TEXT_BLOCKS))
    if kinds.count("details") > MAX_DETAILS:
        raise SpecError("%s.blocks: at most %d details block per section; move the rest into the top-level reference list" % (sp, MAX_DETAILS))
    prose = sum(prose_words(b) for b in blocks)
    if prose > LIMITS["section_prose"]:
        raise SpecError("%s.blocks: %d words of prose (text blocks and visible list items); keep it to %d and let a "
                        "visual carry the rest" % (sp, prose, LIMITS["section_prose"]))
    return blocks


def r_reference(entries):
    out = []
    for n, e in enumerate(entries):
        ep = "spec.reference[%d]" % n
        body = paras(need(e, "text", ep)) if e.get("text") is not None else ""
        if e.get("items") is not None:
            body += '<ul class="list">%s</ul>' % "".join(
                "<li>%s</li>" % inline(text_at(it, "%s.items[%d]" % (ep, k))) for k, it in enumerate(need(e, "items", ep, list)))
        if not body:
            raise SpecError("%s: needs text or items" % ep)
        out.append('<div class="ref"><h3>%s</h3>%s</div>' % (inline(need(e, "title", ep)), body))
    return ('<details class="drawer"><summary>Full detail <span class="count">%d</span></summary>%s</details>'
            % (len(out), "".join(out)))


def build(spec):
    _counter[0] = 0
    if not isinstance(spec, dict):
        raise SpecError("spec: expected a JSON object")
    title = need(spec, "title", "spec")
    if not 2 <= len(title.split()) <= 4:
        raise SpecError("spec.title: use a name of two to four words (got %d)" % len(title.split()))
    ptype = need(spec, "page_type", "spec")
    if ptype not in PAGE_TYPES:
        raise SpecError("spec.page_type: expected one of %s" % ", ".join(PAGE_TYPES))
    bottom = capped(spec, "bottom_line", "spec", "bottom_line")
    gist = r_gist(need(spec, "gist", "spec", dict), "spec.gist")
    nxt = need(spec, "next_action", "spec", dict)
    sections = sized(spec, "sections", "spec", 1, MAX_SECTIONS)

    route, secs = [], []
    for n, s in enumerate(sections):
        sp = "spec.sections[%d]" % n
        heading = capped(s, "heading", sp, "heading")
        short = capped(s, "short", sp, "short")
        blocks = check_section(s, sp)
        sid = "sec-%d" % (n + 1)
        route.append('<li><a href="#%s"><span class="dot">%d</span><span class="rl">%s</span></a></li>' % (sid, n + 1, inline(short)))
        body = "".join(render_block(blk, "%s.blocks[%d]" % (sp, i)) for i, blk in enumerate(blocks))
        secs.append('<section id="%s" class="stop" aria-labelledby="%s-h"><h2 id="%s-h"><span class="dot">%d</span><span>%s</span></h2>%s</section>'
                    % (sid, sid, sid, n + 1, inline(heading), body))

    reference = r_reference(need(spec, "reference", "spec", list)) if spec.get("reference") else ""

    also = ""
    if spec.get("also_worth_knowing"):
        items = need(spec, "also_worth_knowing", "spec", list)
        lis = "".join("<li>%s</li>" % inline(text_at(t, "spec.also_worth_knowing[%d]" % n, LIMITS["also"])) for n, t in enumerate(items))
        also = '<details class="more also"><summary>Also worth knowing <span class="count">%d</span></summary><ul class="list">%s</ul></details>' % (len(items), lis)

    sources = ""
    if spec.get("sources"):
        lis = []
        for n, s in enumerate(need(spec, "sources", "spec", list)):
            sp = "spec.sources[%d]" % n
            label = need(s, "label", sp)
            if s.get("url") is not None:
                lis.append('<li><a href="%s" rel="noopener noreferrer">%s</a></li>' % (esc(check_url(need(s, "url", sp), sp + ".url")), inline(label)))
            else:
                lis.append("<li>%s</li>" % inline(label))
        sources = '<section class="sources" aria-label="Sources"><h2>Sources</h2><ul class="list">%s</ul></section>' % "".join(lis)

    detail = capped(nxt, "detail", "spec.next_action", "next_detail", optional=True)
    next_card = ('<aside class="next" aria-label="Next action"><p class="next-h">Next action</p>'
                 '<p class="next-text">%s</p>%s</aside>') % (inline(capped(nxt, "text", "spec.next_action", "next_text")),
                                                             paras(detail) if detail else "")

    minutes = max(1, int(math.ceil(first_read_words(spec) / float(WORDS_PER_MINUTE))))
    lead, shows = STOP_LINE[ptype]
    stops = len(sections)
    stop_line = "%s %d short stop%s below show%s %s, about %d minute%s." % (
        lead, stops, "" if stops == 1 else "s", "s" if stops == 1 else "", shows, minutes, "" if minutes == 1 else "s")
    header = ('<header class="top"><h1>%s</h1><div class="hero"><figure class="gist g-%s">%s</figure>'
              '<p class="bottom-line">%s</p></div><p class="stopline">%s</p></header>'
              % (inline(title), esc(spec["gist"]["kind"]), gist, inline(bottom), esc(stop_line)))
    nav = '<nav class="route" aria-label="Stops on this page"><ol>%s</ol></nav>' % "".join(route)

    main = header + nav + "".join(secs) + reference + also + next_card + sources
    with open(TEMPLATE, encoding="utf-8") as fh:
        template = fh.read()
    if "{{TITLE}}" not in template or "{{MAIN}}" not in template:
        raise SpecError("template: {{TITLE}} or {{MAIN}} placeholder missing from %s" % TEMPLATE)
    return template.replace("{{TITLE}}", esc(title)).replace("{{MAIN}}", main)


# ---------------------------------------------------------------- output checks

class Balance(HTMLParser):
    """Track open tags and collect the visible text of the page."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.errors, self.text, self.skip = [], [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)
        if tag in ("style", "script", "title"):
            self.skip += 1
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "summary", "dt", "dd", "tr", "figcaption", "div", "text"):
            self.text.append("\n")
        if tag == "span":
            self.text.append(" ")
        if tag in ("td", "th"):
            self.text.append(" | ")

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("unexpected </%s> (open: %s)" % (tag, self.stack[-1] if self.stack else "none"))
            return
        self.stack.pop()
        if tag in ("style", "script", "title"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def page_text(html):
    parser = Balance()
    parser.feed(html)
    parser.close()
    text = re.sub(r"[ \t]+", " ", "".join(parser.text))
    return re.sub(r"\n\s*\n+", "\n", text).strip(), parser


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 3:
        sys.stderr.write("usage: build_page.py <spec.json> <out.html> | --selftest\n")
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.stderr.write("cannot read spec %s: %s\n" % (argv[1], exc))
        return 1
    try:
        html = build(spec)
    except SpecError as exc:
        sys.stderr.write("invalid spec: %s\n" % exc)
        return 1
    with open(argv[2], "w", encoding="utf-8") as fh:
        fh.write(html)
    text, _ = page_text(html)
    sys.stdout.write(text + "\n")
    first, prose, in_visuals, nvis, collapsed = balance(spec)
    sys.stderr.write("first read: %d words (prose %d, in visuals %d, other %d); visual blocks: %d; "
                     "collapsed: %d words\n" % (first, prose, in_visuals, first - prose - in_visuals, nvis, collapsed))
    return 0


# ---------------------------------------------------------------- self-test

SAMPLE = {
    "title": "How Caching Works",
    "page_type": "concept",
    "gist": {"kind": "chain", "nodes": [
        {"icon": "user", "label": "Request arrives"},
        {"icon": "search", "label": "Cache is checked", "arrow": "looks up"},
        {"icon": "bolt", "label": "Fast answer", "arrow": "on a hit", "outcome": True}]},
    "bottom_line": "A cache keeps a copy of slow answers close by, so the second request is fast.",
    "sections": [
        {"heading": "The idea", "short": "The idea", "blocks": [
            {"type": "text", "text": "Ask the database once, keep the answer.\n\nUse `GET /users` as the example; **cache hit** means the copy was there."},
            {"type": "stats", "items": [{"value": "40 ms", "label": "Answer from the database", "icon": "database"},
                                        {"value": "2 ms", "label": "Answer from the cache", "note": "20 times faster"}]},
            {"type": "list", "items": ["one", "two", "three", "four", "five", "six"]},
            {"type": "glossary", "terms": [{"term": "Cache hit", "definition": "The copy was there."}]},
            {"type": "check", "question": "What happens on the second request?", "answer": "It is served from the cache."}]},
        {"heading": "Step by step", "short": "Steps", "blocks": [
            {"type": "stepper", "steps": [
                {"title": "Request arrives", "text": "The app checks the cache."},
                {"title": "Miss", "text": "It asks the database.", "block": {"type": "before_after",
                    "before": {"text": "Empty cache."}, "after": {"label": "Then", "text": "One entry."}}},
                {"title": "Hit", "text": "The next request is fast."}]},
            {"type": "flow", "title": "Request path", "nodes": [
                {"id": "app", "label": "App"}, {"id": "cache", "label": "Cache"},
                {"id": "db", "label": "Database with a long label that wraps"}, {"id": "out", "label": "Response"}],
             "edges": [{"from": "app", "to": "cache", "label": "looks up"}, {"from": "cache", "to": "db", "label": "on a miss"},
                       {"from": "cache", "to": "out", "label": "on a hit"}, {"from": "db", "to": "out"}],
             "caption": "A miss takes the long way."},
            {"type": "chain", "nodes": [
                {"icon": "database", "label": "Data changes", "note": "A row is updated."},
                {"icon": "trash", "label": "Copy is dropped", "arrow": "invalidates"},
                {"icon": "repeat", "label": "Next read refills", "outcome": True}]},
            {"type": "timeline", "items": [{"when": "0 ms", "title": "Request"}, {"when": "40 ms", "title": "Answer", "text": "From the database."}]}]},
        {"heading": "Numbers", "short": "Numbers", "blocks": [
            {"type": "bar_chart", "title": "Response time", "unit": " ms", "items": [{"label": "Miss", "value": 40}, {"label": "Hit", "value": 2}], "caption": "Hits are 20 times faster."},
            {"type": "dot_chart", "title": "Hit rate", "unit": "%", "min": 0, "max": 100, "items": [{"label": "Monday", "value": 72}, {"label": "Tuesday", "value": 91}]},
            {"type": "table", "columns": ["Option", "Speed", "Cost"], "rows": [["Redis", "Fast", "Medium"], ["In memory", "Fastest", "Low"]], "highlight_column": 1, "caption": "Speed matters most here."},
            {"type": "details", "summary": "Why not always cache?", "text": "Stale data.", "items": ["Invalidation is hard."]},
            {"type": "svg", "caption": "A bespoke sketch.", "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 320 70\" role=\"img\" aria-label=\"App reads from the cache\"><defs><marker id=\"m\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" orient=\"auto\"><path d=\"M0 0L10 5L0 10z\" fill=\"currentColor\"/></marker></defs><rect x=\"10\" y=\"10\" width=\"100\" height=\"40\" rx=\"6\" fill=\"none\" stroke=\"currentColor\"/><text x=\"60\" y=\"35\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">App</text><line x1=\"110\" y1=\"30\" x2=\"206\" y2=\"30\" stroke=\"currentColor\" marker-end=\"url(#m)\"/><rect x=\"210\" y=\"10\" width=\"100\" height=\"40\" rx=\"6\" fill=\"none\" stroke=\"currentColor\"/><text x=\"260\" y=\"35\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">Cache</text></svg>"}]},
        {"heading": "When it pays off", "short": "Trade-offs", "blocks": [
            {"type": "icon_array", "count": 3, "total": 100, "label": "requests that miss the cache"},
            {"type": "cards", "cards": [
                {"title": "Cache in memory", "state": "good", "text": "Fastest option.",
                 "points": [{"sign": "+", "text": "No network hop"}, {"sign": "-", "text": "Lost on restart"}]},
                {"title": "No cache", "state": "bad", "points": [{"sign": "-", "text": "Every request is slow"}]}]}]}],
    "reference": [{"title": "Expiry times", "text": "Entries expire after five minutes.", "items": ["Set per key.", "Default is five minutes."]},
                  {"title": "Cache size", "text": "The cache holds 10,000 entries."}],
    "also_worth_knowing": ["Browsers have their own cache."],
    "next_action": {"text": "Open your slowest endpoint and time it twice.", "detail": "If the second call is not faster, nothing is cached."},
    "sources": [{"label": "HTTP caching", "url": "https://example.org/caching"}, {"label": "Team notes"}],
}

VERDICT = {"kind": "verdict", "winner": {"name": "Redis", "reason": "Fast and already running"},
           "alternatives": [{"name": "Memcached", "why_not": "No persistence"}, {"name": "No cache", "why_not": "Too slow"}]}
STATUS = {"kind": "status", "tallies": [{"count": 3, "label": "Shipped", "state": "done"},
                                        {"count": 1200, "label": "Open items", "state": "open"},
                                        {"count": 1, "label": "Blocked", "state": "blocked"}]}


def selftest():
    html = build(SAMPLE)
    assert not re.search(r"\{\{\s*[A-Za-z_]+\s*\}\}", html), "leftover placeholder"
    urls = set(re.findall(r"https?://[^\s\"'<>)]+", html))
    assert urls == {"https://example.org/caching"}, "unexpected URLs: %s" % urls
    text, parser = page_text(html)
    assert not parser.errors, parser.errors
    assert not parser.stack, "unclosed tags: %s" % parser.stack
    for kind in RENDERERS:
        assert 'class="block b-%s"' % kind.replace("_", "-") in html, "component %s not rendered" % kind
    for needle in ("That is the whole idea. 4 short stops below show why, about 2 minutes.", 'class="route"',
                   "Full detail", "Also worth knowing", "Next action", 'id="progress"', "<code>GET /users</code>", "2 more",
                   'class="gist g-chain"', 'class="node out"', "invalidates"):
        assert needle in html, "missing %r" % needle
    for gone in ("On this page", "Bottom line", "&middot;", "eyebrow"):
        assert gone not in html, "should be gone: %r" % gone
    assert "xmlns" not in html
    # The longest bar holds its value inside; a wide flow keeps at least three quarters of its size.
    assert 'class="val in"' in html and "min-width:138px" in html
    # An icon array draws every dot of the denominator, with the count highlighted.
    assert html.count('class="on"') == 3 and html.count('class="off"') == 97
    # The other two gist kinds render.
    verdict = build(dict(SAMPLE, gist=VERDICT))
    assert 'class="gist g-verdict"' in verdict and "Fast and already running" in verdict and "Memcached" in verdict
    status = build(dict(SAMPLE, gist=STATUS))
    assert 'class="gist g-status"' in status and "1,200" in status and 'class="s-blocked"' in status
    assert fmt(8000000) == "8,000,000" and fmt(2) == "2" and fmt(1234.5) == "1,234.5"
    assert fmt(0.004) == "0.004" and fmt(-0.001) == "-0.001" and fmt(0.123) == "0.12"
    assert inline("`a**b**c` **d**") == "<code>a**b**c</code> <strong>d</strong>"
    assert wrap("x" * 25, 20) == ["x" * 20, "x" * 5]
    # Collapsed text (details, check answers, list items past the visible ones, reference, tangents) is not part of the first read.
    assert 0 < first_read_words(SAMPLE) < spec_words(SAMPLE)
    assert first_read_words({"type": "list", "items": ["a b"] * (VISIBLE_ITEMS + 3)}) == 2 * VISIBLE_ITEMS
    assert first_read_words({"type": "details", "summary": "one two", "text": "hidden words here"}) == 2
    assert spec_words({"icon": "database", "label": "two words"}) == 2
    first, prose, in_visuals, nvis, collapsed = balance(SAMPLE)
    assert first > prose + in_visuals > 0 and prose == 24 and nvis == 11 and collapsed > 0
    # Empty optional lists mean "none", and a table may have an empty corner header.
    empty = json.loads(json.dumps(SAMPLE))
    empty["sources"], empty["also_worth_knowing"], empty["reference"] = [], [], []
    assert "Sources" not in build(empty) and "Full detail" not in build(empty)
    corner = {"title": "Corner Cell Test", "page_type": "research", "bottom_line": "x", "next_action": {"text": "y"},
              "gist": VERDICT, "sections": [{"heading": "h", "short": "h", "blocks": [
                  {"type": "table", "columns": ["", "A"], "rows": [["r", "1"]]}]}]}
    one = build(corner)
    assert '<th scope="col"></th>' in one and "That is the answer. 1 short stop below shows why" in one
    assert "A cache keeps a copy" in text and "Open your slowest endpoint" in text

    def rejects(mutate, field):
        spec = json.loads(json.dumps(SAMPLE))
        mutate(spec)
        try:
            build(spec)
        except SpecError as exc:
            assert field in str(exc), "error %r does not name %r" % (str(exc), field)
            return
        raise AssertionError("spec accepted but should fail on %s" % field)

    blk = lambda s, sec, i: s["sections"][sec]["blocks"][i]
    sec = lambda s, n: s["sections"][n]
    long_ = lambda n: " ".join(["word"] * (n + 1))
    node = lambda s, i: s["gist"]["nodes"][i]
    rejects(lambda s: s.pop("bottom_line"), "spec.bottom_line")
    rejects(lambda s: s.update(bottom_line=long_(LIMITS["bottom_line"])), "spec.bottom_line")
    rejects(lambda s: s.update(title="Caching"), "spec.title")
    rejects(lambda s: s.update(page_type="essay"), "spec.page_type")
    rejects(lambda s: s.update(bottom_line="{{MAIN}}"), "spec.bottom_line")
    rejects(lambda s: blk(s, 0, 0).update(type="video"), "spec.sections[0].blocks[0].type")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(value=True), "spec.sections[2].blocks[0].items[0].value")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(value=-1), "spec.sections[2].blocks[0].items")
    rejects(lambda s: blk(s, 2, 1).update(min=5, max=5), "spec.sections[2].blocks[1]")
    rejects(lambda s: blk(s, 2, 1).update(min=float("-inf")), "spec.sections[2].blocks[1].min")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(value=10 ** 400), "spec.sections[2].blocks[0].items[0].value")
    rejects(lambda s: blk(s, 1, 1)["edges"].append({"from": "out", "to": "app"}), "spec.sections[1].blocks[1].edges")
    rejects(lambda s: blk(s, 1, 1)["edges"].append({"from": "app", "to": "nowhere"}), "spec.sections[1].blocks[1].edges[4].to")
    rejects(lambda s: blk(s, 2, 2)["rows"].append(["only one"]), "spec.sections[2].blocks[2].rows[2]")
    rejects(lambda s: s["sources"][0].update(url="javascript:alert(1)"), "spec.sources[0].url")
    rejects(lambda s: s["sources"][0].update(url="https://example.org/a\n"), "spec.sources[0].url")
    rejects(lambda s: s.update(title="One two three four five"), "spec.title")
    rejects(lambda s: blk(s, 2, 2)["rows"][0].__setitem__(1, long_(LIMITS["cell"])), "spec.sections[2].blocks[2].rows[0][1]")
    rejects(lambda s: blk(s, 1, 1)["nodes"].append({"id": "app", "label": "Again"}), "spec.sections[1].blocks[1].nodes[4].id")
    rejects(lambda s: blk(s, 2, 0).update(caption=5), "spec.sections[2].blocks[0].caption")
    rejects(lambda s: blk(s, 1, 3)["items"].append("not an object"), "spec.sections[1].blocks[3].items[2]")
    rejects(lambda s: blk(s, 1, 0)["steps"][1]["block"]["before"].update(label=3), "spec.sections[1].blocks[0].steps[1].block.before.label")
    # The gist.
    rejects(lambda s: s.pop("gist"), "spec.gist")
    rejects(lambda s: s["gist"].update(kind="poster"), "spec.gist.kind")
    rejects(lambda s: s["gist"].update(nodes=s["gist"]["nodes"][:1]), "spec.gist.nodes")
    rejects(lambda s: s["gist"]["nodes"].extend([{"icon": "flag", "label": "x"}] * 2), "spec.gist.nodes")
    rejects(lambda s: node(s, 0).update(label=long_(LIMITS["node_label"])), "spec.gist.nodes[0].label")
    rejects(lambda s: node(s, 1).update(arrow=long_(LIMITS["arrow"])), "spec.gist.nodes[1].arrow")
    rejects(lambda s: node(s, 0).update(arrow="starts"), "spec.gist.nodes[0].arrow")
    rejects(lambda s: node(s, 0).update(outcome=True), "spec.gist.nodes")
    rejects(lambda s: node(s, 0).update(note="Only in sections."), "spec.gist.nodes[0].note")
    rejects(lambda s: node(s, 0).update(icon="unicorn"), "spec.gist.nodes[0].icon")
    rejects(lambda s: node(s, 0).update(icon="<script>"), "expected one of arrow-down")
    rejects(lambda s: s.update(gist=dict(VERDICT, winner={"name": "Redis", "reason": long_(LIMITS["winner_reason"])})), "spec.gist.winner.reason")
    rejects(lambda s: s.update(gist=dict(VERDICT, winner={"name": long_(LIMITS["winner_name"]), "reason": "x"})), "spec.gist.winner.name")
    rejects(lambda s: s.update(gist=dict(VERDICT, alternatives=[{"name": "A", "why_not": long_(LIMITS["why_not"])}])), "spec.gist.alternatives[0].why_not")
    rejects(lambda s: s.update(gist=dict(VERDICT, alternatives=[{"name": "A", "why_not": "b"}] * 4)), "spec.gist.alternatives")
    rejects(lambda s: s.update(gist=dict(STATUS, tallies=STATUS["tallies"][:1])), "spec.gist.tallies")
    rejects(lambda s: s.update(gist=dict(STATUS, tallies=[dict(STATUS["tallies"][0], label="one two three four")] * 2)), "spec.gist.tallies[0].label")
    rejects(lambda s: s.update(gist=dict(STATUS, tallies=[dict(STATUS["tallies"][0], state="good")] * 2)), "spec.gist.tallies[0].state")
    rejects(lambda s: s.update(gist=dict(STATUS, tallies=[dict(STATUS["tallies"][0], count=2.5)] * 2)), "spec.gist.tallies[0].count")
    # Sections.
    rejects(lambda s: s["sections"].extend([s["sections"][3]] * 2), "spec.sections")
    rejects(lambda s: sec(s, 0).pop("short"), "spec.sections[0].short")
    rejects(lambda s: sec(s, 0).update(short="one two three four"), "spec.sections[0].short")
    rejects(lambda s: sec(s, 0).update(heading=long_(LIMITS["heading"])), "spec.sections[0].heading")
    rejects(lambda s: sec(s, 0)["blocks"].pop(1), "spec.sections[0].blocks")
    rejects(lambda s: sec(s, 3)["blocks"].insert(0, {"type": "text", "text": long_(LIMITS["text"])}), "spec.sections[3].blocks[0].text")
    rejects(lambda s: sec(s, 0)["blocks"].extend([{"type": "text", "text": "More."}] * 2), "spec.sections[0].blocks")
    rejects(lambda s: sec(s, 0)["blocks"].append({"type": "text", "text": long_(36)}), "spec.sections[0].blocks: 61 words")
    rejects(lambda s: sec(s, 2)["blocks"].append({"type": "details", "summary": "x", "text": "y"}), "spec.sections[2].blocks")
    rejects(lambda s: blk(s, 2, 3).update(summary=long_(LIMITS["summary"])), "spec.sections[2].blocks[3].summary")
    # Text-bearing fields of existing blocks.
    rejects(lambda s: blk(s, 2, 0).update(caption=long_(LIMITS["caption"])), "spec.sections[2].blocks[0].caption")
    rejects(lambda s: blk(s, 2, 0).update(title=long_(LIMITS["title"])), "spec.sections[2].blocks[0].title")
    rejects(lambda s: blk(s, 1, 0)["steps"][0].update(title=long_(LIMITS["step_title"])), "spec.sections[1].blocks[0].steps[0].title")
    rejects(lambda s: blk(s, 1, 0)["steps"][0].update(text=long_(LIMITS["step_text"])), "spec.sections[1].blocks[0].steps[0].text")
    rejects(lambda s: blk(s, 0, 3)["terms"][0].update(term=long_(LIMITS["term"])), "spec.sections[0].blocks[3].terms[0].term")
    rejects(lambda s: blk(s, 0, 3)["terms"][0].update(definition=long_(LIMITS["definition"])), "spec.sections[0].blocks[3].terms[0].definition")
    rejects(lambda s: blk(s, 0, 3).update(terms=[{"term": "a", "definition": "b"}] * 5), "spec.sections[0].blocks[3].terms")
    rejects(lambda s: blk(s, 0, 4).update(question=long_(LIMITS["question"])), "spec.sections[0].blocks[4].question")
    rejects(lambda s: blk(s, 1, 0)["steps"][1]["block"]["after"].update(text=long_(LIMITS["ba_text"])), "steps[1].block.after.text")
    rejects(lambda s: blk(s, 1, 3)["items"][0].update(title=long_(LIMITS["tl_title"])), "spec.sections[1].blocks[3].items[0].title")
    rejects(lambda s: blk(s, 1, 3)["items"][1].update(text=long_(LIMITS["tl_text"])), "spec.sections[1].blocks[3].items[1].text")
    rejects(lambda s: blk(s, 0, 2)["items"].__setitem__(0, long_(LIMITS["item"])), "spec.sections[0].blocks[2].items[0]")
    rejects(lambda s: blk(s, 0, 2)["items"].append("seven"), "spec.sections[0].blocks[2].items")
    rejects(lambda s: blk(s, 2, 2).update(columns=["a"] * 6, rows=[["b"] * 6]), "spec.sections[2].blocks[2].columns")
    rejects(lambda s: blk(s, 2, 2)["rows"].extend([["a", "b", "c"]] * 5), "spec.sections[2].blocks[2].rows")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(label=long_(LIMITS["chart_label"])), "spec.sections[2].blocks[0].items[0].label")
    rejects(lambda s: blk(s, 1, 1)["edges"][0].update(label=long_(LIMITS["edge_label"])), "spec.sections[1].blocks[1].edges[0].label")
    rejects(lambda s: s["next_action"].update(text=long_(LIMITS["next_text"])), "spec.next_action.text")
    rejects(lambda s: s["next_action"].update(detail=long_(LIMITS["next_detail"])), "spec.next_action.detail")
    rejects(lambda s: s["also_worth_knowing"].append(long_(LIMITS["also"])), "spec.also_worth_knowing[1]")
    rejects(lambda s: s["reference"].append({"title": "Empty"}), "spec.reference[2]")
    # The new blocks.
    rejects(lambda s: blk(s, 0, 1)["items"][0].update(value="forty milliseconds"), "spec.sections[0].blocks[1].items[0].value")
    rejects(lambda s: blk(s, 0, 1)["items"][0].update(label=long_(LIMITS["stat_label"])), "spec.sections[0].blocks[1].items[0].label")
    rejects(lambda s: blk(s, 0, 1)["items"][1].update(note=long_(LIMITS["stat_note"])), "spec.sections[0].blocks[1].items[1].note")
    rejects(lambda s: blk(s, 0, 1)["items"].extend([{"value": "1", "label": "x"}] * 2), "spec.sections[0].blocks[1].items")
    rejects(lambda s: blk(s, 0, 1)["items"][0].update(icon="dragon"), "spec.sections[0].blocks[1].items[0].icon")
    rejects(lambda s: blk(s, 3, 0).update(total=101), "spec.sections[3].blocks[0].total")
    rejects(lambda s: blk(s, 3, 0).update(count=101), "spec.sections[3].blocks[0].count")
    rejects(lambda s: blk(s, 3, 0).update(count=True), "spec.sections[3].blocks[0].count")
    rejects(lambda s: blk(s, 3, 0).update(label=long_(LIMITS["ia_label"])), "spec.sections[3].blocks[0].label")
    rejects(lambda s: blk(s, 1, 2)["nodes"].extend([{"icon": "flag", "label": "x"}] * 3), "spec.sections[1].blocks[2].nodes")
    rejects(lambda s: blk(s, 1, 2)["nodes"][0].update(note=long_(LIMITS["node_note"])), "spec.sections[1].blocks[2].nodes[0].note")
    rejects(lambda s: blk(s, 3, 1)["cards"].pop(), "spec.sections[3].blocks[1].cards")
    rejects(lambda s: blk(s, 3, 1)["cards"][0].update(title=long_(LIMITS["card_title"])), "spec.sections[3].blocks[1].cards[0].title")
    rejects(lambda s: blk(s, 3, 1)["cards"][0].update(text=long_(LIMITS["card_text"])), "spec.sections[3].blocks[1].cards[0].text")
    rejects(lambda s: blk(s, 3, 1)["cards"][0].update(state="great"), "spec.sections[3].blocks[1].cards[0].state")
    rejects(lambda s: blk(s, 3, 1)["cards"][0]["points"].extend([{"sign": "+", "text": "x"}] * 2), "spec.sections[3].blocks[1].cards[0].points")
    rejects(lambda s: blk(s, 3, 1)["cards"][0]["points"][0].update(sign="*"), "spec.sections[3].blocks[1].cards[0].points[0].sign")
    rejects(lambda s: blk(s, 3, 1)["cards"][0]["points"][0].update(text=long_(LIMITS["point"])), "spec.sections[3].blocks[1].cards[0].points[0].text")
    bad_svgs = [
        "<svg><script>alert(1)</script></svg>",
        "<svg><rect onclick=\"x()\"/></svg>",
        "<svg><image href=\"https://evil.example/x.png\"/></svg>",
        "<svg><use href=\"https://evil.example/s.svg#a\"/></svg>",
        "<svg><use xlink:href=\"&#x6a;avascript:x\"/></svg>",
        "<svg></svg></main><img src=x onerror=alert(1)>",
        "<svg><rect style=\"fill:url(https://evil.example/a)\"/></svg>",
        "<svg><a href=\"#x\"><text>t</text></a></svg>",
        "<svg><g>",
        "<svg><!--><img src=x onerror=alert(1)>--></svg>",
        "<svg><title><img src=x onerror=alert(1)></title></svg>",
        "<svg><text><img onerror=alert(1) src=\"x></text></svg>",
        "<svg style=\"background-image:image-set('//evil.example/a.png' 1x)\"></svg>",
        "<svg><rect fill=\"u\\72l(//evil.example/a)\"/></svg>",
        "<svg><text>a < b</text></svg>",
    ]
    for bad in bad_svgs:
        rejects(lambda s, bad=bad: blk(s, 2, 4).update(svg=bad), "spec.sections[2].blocks[4].svg")

    with tempfile.TemporaryDirectory() as tmp:
        spec_path, out_path = os.path.join(tmp, "spec.json"), os.path.join(tmp, "out.html")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(SAMPLE, fh)
        devnull = open(os.devnull, "w")
        saved, saved_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = devnull
        try:
            assert main(["build_page.py", spec_path, out_path]) == 0
        finally:
            sys.stdout, sys.stderr = saved, saved_err
            devnull.close()
        assert os.path.getsize(out_path) > 1000
    print("build_page.py selftest: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
