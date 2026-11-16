#!/usr/bin/env python3
"""Render a help-me-understand page spec into one self-contained HTML file.

Usage:
    build_page.py <spec.json> <out.html>
    build_page.py --selftest

The spec format is described in references/spec-schema.md. All spec text is
HTML-escaped; the only raw passthrough is the "svg" block, which is parsed and
checked against an element and attribute allowlist first. Charts and flow
diagrams are drawn here as inline SVG, so the page needs no library.

After writing the page, the script prints the page's visible text to stdout,
so the naive-reader check can be given exactly what a reader would see.
Standard library only; runs on Python 3.8 and later.
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
# A bottom line or table cell longer than this is prose in the wrong place.
BOTTOM_LINE_WORDS = 35
CELL_WORDS = 14
VISIBLE_ITEMS = 4
PAGE_TYPES = ("concept", "research", "work-summary", "how-to")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


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
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            raise SpecError("%s: expected a number" % where)
    elif kind is list:
        if not isinstance(val, list) or not val:
            raise SpecError("%s: expected a non-empty list" % where)
    elif kind is dict:
        if not isinstance(val, dict):
            raise SpecError("%s: expected an object" % where)
    elif kind is str:
        if not isinstance(val, str) or not val.strip():
            raise SpecError("%s: expected non-empty text" % where)
        if "{{" in val or "}}" in val:
            raise SpecError("%s: text may not contain '{{' or '}}'" % where)
    return val


def text_at(val, where):
    """Check one text value that has no key of its own, such as a list item."""
    if not isinstance(val, str) or not val.strip():
        raise SpecError("%s: expected non-empty text" % where)
    if "{{" in val or "}}" in val:
        raise SpecError("%s: text may not contain '{{' or '}}'" % where)
    return val


def check_url(url, path):
    if not re.match(r"https?://[^\s\"'<>]+$", url):
        raise SpecError("%s: source links must be http:// or https:// URLs" % path)
    return url


# ---------------------------------------------------------------- text helpers

def esc(text):
    return _escape(text, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def inline(text):
    """Escape text, then allow `code` and **bold** as the only inline markup."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def paras(text):
    return "".join("<p>%s</p>" % inline(p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip())


def wrap(text, width):
    """Greedy word wrap for SVG labels."""
    lines, cur = [], ""
    for word in text.split():
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
    return "{:,d}".format(int(n)) if float(n).is_integer() else "{:,.2f}".format(n).rstrip("0").rstrip(".")


def figure(inner, caption, cls):
    cap = "<figcaption>%s</figcaption>" % inline(caption) if caption else ""
    return '<figure class="%s">%s%s</figure>' % (cls, inner, cap)


# ---------------------------------------------------------------- components

def r_text(b, p):
    return paras(need(b, "text", p))


def r_list(b, p):
    items = need(b, "items", p, list)
    lis = ["<li>%s</li>" % inline(text_at(it, "%s.items[%d]" % (p, n))) for n, it in enumerate(items)]
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
        body = paras(need(s, "text", sp))
        if s.get("block") is not None:
            body += render_block(need(s, "block", sp, dict), sp + ".block")
        out.append('<li class="step"><h4><span class="num">%d</span>%s</h4>%s</li>' % (
            n + 1, inline(need(s, "title", sp)), body))
    return '<div class="stepper" data-stepper><ol class="steps">%s</ol></div>' % "".join(out)


def r_table(b, p):
    cols = need(b, "columns", p, list)
    rows = need(b, "rows", p, list)
    hl = b.get("highlight_column")
    if hl is not None and (isinstance(hl, bool) or not isinstance(hl, int) or not 0 <= hl < len(cols)):
        raise SpecError("%s.highlight_column: expected a column index from 0 to %d" % (p, len(cols) - 1))

    def cell_text(text, path):
        if isinstance(text, str) and len(text.split()) > CELL_WORDS:
            raise SpecError("%s: keep table cells to %d words or fewer; put sentences in a text block" % (path, CELL_WORDS))
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
    return [(need(it, "label", "%s.items[%d]" % (p, n)), need(it, "value", "%s.items[%d]" % (p, n), float))
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
        rows.append(
            '<text class="lbl" x="0" y="%d">%s</text>'
            '<rect class="bar" x="0" y="%d" width="%.2f%%" height="14" rx="2"></rect>'
            '<text class="val" x="%.2f%%" y="%d" dx="6">%s</text>'
            % (y + 14, esc(label), y + 22, w, w, y + 34, esc(fmt(v) + unit)))
    h = len(items) * ROW
    svg = ('<svg class="chart" width="100%%" height="%d" role="img" aria-label="%s">%s'
           '<line class="axis" x1="0" y1="18" x2="0" y2="%d"></line></svg>') % (
        h, esc(b.get("title") or "Bar chart"), "".join(rows), h - 6)
    return figure(title_html(b) + svg, b.get("caption"), "chartfig")


def r_dot_chart(b, p):
    items = chart_items(b, p)
    lo = b.get("min", min(v for _, v in items))
    hi = b.get("max", max(v for _, v in items))
    for key, val in (("min", lo), ("max", hi)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise SpecError("%s.%s: expected a number" % (p, key))
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
        labels[nid] = wrap(need(nd, "label", np_), 20)
    out = {i: [] for i in ids}
    indeg = {i: 0 for i in ids}
    for n, e in enumerate(edges):
        ep = "%s.edges[%d]" % (p, n)
        a, z = need(e, "from", ep), need(e, "to", ep)
        for key, v in (("from", a), ("to", z)):
            if v not in labels:
                raise SpecError("%s.%s: no node with id %r" % (ep, key, v))
        if e.get("label") is not None:
            need(e, "label", ep)
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
    svg = ('<div class="scroll"><svg class="flow" viewBox="0 0 %d %d" style="max-width:%dpx;min-width:%dpx" role="img" aria-label="%s">%s%s</svg></div>'
           % (width, height, width, min(width, 320), esc(b.get("title") or "Flow diagram"), defs, "".join(parts)))
    return figure(title_html(b) + svg, b.get("caption"), "flowfig")


def r_timeline(b, p):
    items = need(b, "items", p, list)
    lis = []
    for n, it in enumerate(items):
        ip = "%s.items[%d]" % (p, n)
        when, title = need(it, "when", ip), need(it, "title", ip)
        text = need(it, "text", ip, optional=True)
        lis.append('<li><span class="when">%s</span><div class="what"><strong>%s</strong>%s</div></li>'
                   % (inline(when), inline(title), paras(text) if text else ""))
    return '<ol class="timeline">%s</ol>' % "".join(lis)


def r_before_after(b, p):
    sides = []
    for key, default in (("before", "Before"), ("after", "After")):
        side = need(b, key, p, dict)
        label = need(side, "label", "%s.%s" % (p, key), optional=True) or default
        sides.append('<div class="ba-%s"><div class="ba-label">%s</div>%s</div>'
                     % (key, inline(label), paras(need(side, "text", "%s.%s" % (p, key)))))
    return figure('<div class="ba">%s</div>' % "".join(sides), b.get("caption"), "bafig")


def r_check(b, p):
    return ('<details class="check"><summary><span class="eyebrow">Check yourself</span><span class="q">%s</span></summary>'
            '<div class="answer">%s</div></details>') % (inline(need(b, "question", p)), paras(need(b, "answer", p)))


def r_details(b, p):
    inner = ""
    if b.get("text") is not None:
        inner += paras(need(b, "text", p))
    if b.get("items") is not None:
        inner += "<ul class=\"list\">%s</ul>" % "".join(
            "<li>%s</li>" % inline(text_at(it, "%s.items[%d]" % (p, n))) for n, it in enumerate(need(b, "items", p, list)))
    if not inner:
        raise SpecError("%s: needs text or items" % p)
    return '<details class="more"><summary>%s</summary>%s</details>' % (inline(need(b, "summary", p)), inner)


def r_glossary(b, p):
    terms = need(b, "terms", p, list)
    out = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (
        inline(need(t, "term", "%s.terms[%d]" % (p, n))), inline(need(t, "definition", "%s.terms[%d]" % (p, n))))
        for n, t in enumerate(terms))
    return '<dl class="glossary">%s</dl>' % out


SVG_TAGS = {"svg", "g", "defs", "marker", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path",
            "text", "tspan", "lineargradient", "radialgradient", "stop", "use", "symbol",
            "clippath", "mask", "pattern"}
REF_ATTRS = {"href", "xlink:href", "src"}


class SvgCheck(HTMLParser):
    """Parse an svg fragment and record why it is unsafe, if it is."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
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
    "check": r_check, "details": r_details, "glossary": r_glossary, "svg": r_svg,
}
_counter = [0]


def render_block(b, p):
    kind = need(b, "type", p)
    if kind not in RENDERERS:
        raise SpecError("%s.type: unknown type %r (expected one of %s)" % (p, kind, ", ".join(sorted(RENDERERS))))
    for key in ("caption", "title", "unit"):
        need(b, key, p, optional=True)
    if "ordered" in b and not isinstance(b["ordered"], bool):
        raise SpecError("%s.ordered: expected true or false" % p)
    _counter[0] += 1
    b = dict(b, _id="v%d" % _counter[0])
    return '<div class="block b-%s">%s</div>' % (kind.replace("_", "-"), RENDERERS[kind](b, p))


# ---------------------------------------------------------------- page

def spec_words(obj):
    """Count words in every string of the spec except ids, types, URLs and raw svg."""
    if isinstance(obj, str):
        return len(obj.split())
    if isinstance(obj, list):
        return sum(spec_words(x) for x in obj)
    if isinstance(obj, dict):
        return sum(spec_words(v) for k, v in obj.items() if k not in ("type", "id", "from", "to", "url", "svg", "page_type"))
    return 0


def first_read_words(obj):
    """Count the words a reader sees without opening anything collapsed."""
    if isinstance(obj, dict):
        if obj.get("type") == "details":
            return spec_words(obj.get("summary"))
        if obj.get("type") == "list":
            return spec_words((obj.get("items") or [])[:VISIBLE_ITEMS])
        return sum(first_read_words(v) if isinstance(v, (dict, list)) else spec_words(v) for k, v in obj.items()
                   if k not in ("type", "id", "from", "to", "url", "svg", "page_type", "answer", "also_worth_knowing", "sources"))
    if isinstance(obj, list):
        return sum(first_read_words(x) for x in obj)
    return spec_words(obj)


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
    bottom = need(spec, "bottom_line", "spec")
    if len(bottom.split()) > BOTTOM_LINE_WORDS:
        raise SpecError("spec.bottom_line: keep it to %d words or fewer (got %d)" % (BOTTOM_LINE_WORDS, len(bottom.split())))
    nxt = need(spec, "next_action", "spec", dict)
    sections = need(spec, "sections", "spec", list)

    nav, secs = [], []
    for n, s in enumerate(sections):
        sp = "spec.sections[%d]" % n
        heading = need(s, "heading", sp)
        blocks = need(s, "blocks", sp, list)
        sid = "sec-%d" % (n + 1)
        nav.append('<li><a href="#%s">%s</a></li>' % (sid, inline(heading)))
        body = "".join(render_block(blk, "%s.blocks[%d]" % (sp, i)) for i, blk in enumerate(blocks))
        secs.append('<section id="%s" aria-labelledby="%s-h"><h2 id="%s-h">%s</h2>%s</section>' % (sid, sid, sid, inline(heading), body))

    also = ""
    if spec.get("also_worth_knowing"):
        items = need(spec, "also_worth_knowing", "spec", list)
        lis = "".join("<li>%s</li>" % inline(text_at(t, "spec.also_worth_knowing[%d]" % n)) for n, t in enumerate(items))
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

    detail = need(nxt, "detail", "spec.next_action", optional=True)
    detail = paras(detail) if detail else ""
    next_card = ('<aside class="next" aria-label="Next action"><div class="eyebrow">Next action</div>'
                 '<p class="next-text">%s</p>%s</aside>') % (inline(need(nxt, "text", "spec.next_action")), detail)

    minutes = max(1, int(math.ceil(first_read_words(spec) / float(WORDS_PER_MINUTE))))
    kind_label = {"concept": "Concept", "research": "Research", "work-summary": "Work summary", "how-to": "How-to"}[ptype]
    header = ('<header class="top"><div class="meta"><span>%s</span><span aria-hidden="true">&middot;</span><span>%d min read</span></div>'
              '<h1>%s</h1><div class="bottom-line" role="note"><div class="eyebrow">Bottom line</div><p>%s</p></div></header>'
              % (kind_label, minutes, inline(title), inline(bottom)))
    navhtml = '<nav class="toc" aria-label="On this page"><div class="eyebrow">On this page</div><ol>%s</ol></nav>' % "".join(nav)

    main = header + navhtml + "".join(secs) + also + next_card + sources
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
    first = first_read_words(spec)
    sys.stderr.write("first read: %d words; collapsed: %d words\n" % (first, spec_words(spec) - first))
    return 0


# ---------------------------------------------------------------- self-test

SAMPLE = {
    "title": "How Caching Works",
    "page_type": "concept",
    "bottom_line": "A cache keeps a copy of slow answers close by, so the second request is fast.",
    "sections": [
        {"heading": "The idea", "blocks": [
            {"type": "text", "text": "Ask the database once, keep the answer.\n\nUse `GET /users` as the example; **cache hit** means the copy was there."},
            {"type": "list", "items": ["one", "two", "three", "four", "five", "six"]},
            {"type": "glossary", "terms": [{"term": "Cache hit", "definition": "The copy was there."}]},
            {"type": "check", "question": "What happens on the second request?", "answer": "It is served from the cache."}]},
        {"heading": "Step by step", "blocks": [
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
            {"type": "timeline", "items": [{"when": "0 ms", "title": "Request"}, {"when": "40 ms", "title": "Answer", "text": "From the database."}]}]},
        {"heading": "Numbers", "blocks": [
            {"type": "bar_chart", "title": "Response time", "unit": " ms", "items": [{"label": "Miss", "value": 40}, {"label": "Hit", "value": 2}], "caption": "Hits are 20 times faster."},
            {"type": "dot_chart", "title": "Hit rate", "unit": "%", "min": 0, "max": 100, "items": [{"label": "Monday", "value": 72}, {"label": "Tuesday", "value": 91}]},
            {"type": "table", "columns": ["Option", "Speed", "Cost"], "rows": [["Redis", "Fast", "Medium"], ["In memory", "Fastest", "Low"]], "highlight_column": 1, "caption": "Speed matters most here."},
            {"type": "details", "summary": "Why not always cache?", "text": "Stale data.", "items": ["Invalidation is hard."]},
            {"type": "svg", "caption": "A bespoke sketch.", "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 320 70\" role=\"img\" aria-label=\"App reads from the cache\"><defs><marker id=\"m\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" orient=\"auto\"><path d=\"M0 0L10 5L0 10z\" fill=\"currentColor\"/></marker></defs><rect x=\"10\" y=\"10\" width=\"100\" height=\"40\" rx=\"6\" fill=\"none\" stroke=\"currentColor\"/><text x=\"60\" y=\"35\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">App</text><line x1=\"110\" y1=\"30\" x2=\"206\" y2=\"30\" stroke=\"currentColor\" marker-end=\"url(#m)\"/><rect x=\"210\" y=\"10\" width=\"100\" height=\"40\" rx=\"6\" fill=\"none\" stroke=\"currentColor\"/><text x=\"260\" y=\"35\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">Cache</text></svg>"}]}],
    "also_worth_knowing": ["Browsers have their own cache."],
    "next_action": {"text": "Open your slowest endpoint and time it twice.", "detail": "If the second call is not faster, nothing is cached."},
    "sources": [{"label": "HTTP caching", "url": "https://example.org/caching"}, {"label": "Team notes"}],
}


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
    for needle in ("min read", "Bottom line", "On this page", "Also worth knowing", "Next action", 'id="progress"', "<code>GET /users</code>", "2 more"):
        assert needle in html, "missing %r" % needle
    assert "xmlns" not in html
    assert fmt(8000000) == "8,000,000" and fmt(2) == "2" and fmt(1234.5) == "1,234.5"
    # Collapsed text (details, check answers, list items past the visible ones, tangents) is not part of the first read.
    assert 0 < first_read_words(SAMPLE) < spec_words(SAMPLE)
    assert first_read_words({"type": "list", "items": ["a b"] * (VISIBLE_ITEMS + 3)}) == 2 * VISIBLE_ITEMS
    assert first_read_words({"type": "details", "summary": "one two", "text": "hidden words here"}) == 2
    # Empty optional lists mean "none", and a table may have an empty corner header.
    empty = json.loads(json.dumps(SAMPLE))
    empty["sources"], empty["also_worth_knowing"] = [], []
    assert "Sources" not in build(empty)
    corner = {"title": "Corner Cell Test", "page_type": "research", "bottom_line": "x", "next_action": {"text": "y"},
              "sections": [{"heading": "h", "blocks": [{"type": "table", "columns": ["", "A"], "rows": [["r", "1"]]}]}]}
    assert '<th scope="col"></th>' in build(corner)
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
    rejects(lambda s: s.pop("bottom_line"), "spec.bottom_line")
    rejects(lambda s: s.update(bottom_line="word " * (BOTTOM_LINE_WORDS + 1)), "spec.bottom_line")
    rejects(lambda s: s.update(title="Caching"), "spec.title")
    rejects(lambda s: s.update(page_type="essay"), "spec.page_type")
    rejects(lambda s: s.update(bottom_line="{{MAIN}}"), "spec.bottom_line")
    rejects(lambda s: blk(s, 0, 0).update(type="video"), "spec.sections[0].blocks[0].type")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(value=True), "spec.sections[2].blocks[0].items[0].value")
    rejects(lambda s: blk(s, 2, 0)["items"][0].update(value=-1), "spec.sections[2].blocks[0].items")
    rejects(lambda s: blk(s, 2, 1).update(min=5, max=5), "spec.sections[2].blocks[1]")
    rejects(lambda s: blk(s, 1, 1)["edges"].append({"from": "out", "to": "app"}), "spec.sections[1].blocks[1].edges")
    rejects(lambda s: blk(s, 1, 1)["edges"].append({"from": "app", "to": "nowhere"}), "spec.sections[1].blocks[1].edges[4].to")
    rejects(lambda s: blk(s, 2, 2)["rows"].append(["only one"]), "spec.sections[2].blocks[2].rows[2]")
    rejects(lambda s: s["sources"][0].update(url="javascript:alert(1)"), "spec.sources[0].url")
    rejects(lambda s: blk(s, 2, 0).update(caption=5), "spec.sections[2].blocks[0].caption")
    rejects(lambda s: blk(s, 1, 2)["items"].append("not an object"), "spec.sections[1].blocks[2].items[2]")
    rejects(lambda s: blk(s, 1, 0)["steps"][1]["block"]["before"].update(label=3), "spec.sections[1].blocks[0].steps[1].block.before.label")
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
