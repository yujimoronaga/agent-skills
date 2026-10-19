#!/usr/bin/env python3
"""Render the .loop/ folder into one self-contained HTML report.

Usage:
  python3 build_report.py <project>/.loop out.html               # body-only page (for Artifact publish)
  python3 build_report.py <project>/.loop out.html --standalone  # full HTML file to open in any browser
Standard library only. Re-run at every gate; publish to the same place so the link stays the same.
"""
import html
import os
import re
import sys

STAGES = [("1", "Plan"), ("2", "Council"), ("3", "Code"), ("4", "Final check")]
SECTIONS = [("final-report.md", "Final report"), ("checklist.md", "Checklist"), ("plan.md", "Plan"),
            ("council.md", "Council"), ("intake.md", "Intake")]


def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"\b(PASS \((?:partial|risk|modelled only)\)|PASS|FAIL|N/A|REJECTED|APPROVED WITH CHANGES|APPROVED|RESOLVED|NOT RESOLVED)\b",
               lambda m: f'<span class="pill {pill_class(m.group(1))}">{m.group(1)}</span>', t)
    return t


def pill_class(word):
    if word.startswith("PASS (") or word == "APPROVED WITH CHANGES":
        return "warn"
    if word in ("PASS", "APPROVED", "RESOLVED"):
        return "ok"
    if word in ("FAIL", "REJECTED", "NOT RESOLVED"):
        return "crit"
    return "neutral"


def md(text):
    """Small Markdown subset: headings, lists, task lists, tables, code fences, paragraphs."""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(ln)
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            out.append('<div class="tw"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                item = re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                box = re.match(r"^\[( |x|X)\]\s+(.*)", item)
                if box:
                    done = box.group(1).lower() == "x"
                    items.append(f'<li class="task {"done" if done else ""}"><span class="box" aria-hidden="true">{"✓" if done else ""}</span>{inline(box.group(2))}</li>')
                else:
                    items.append(f"<li>{inline(item)}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if ln.strip():
            para = [ln.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|\s*([-*]|\d+\.)\s)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            continue
        i += 1
    return "\n".join(out)


def state_fields(text):
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in text.splitlines() if ":" in l and not l.startswith(" "))}


def main(argv):
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    d = argv[0]
    read = lambda f: open(os.path.join(d, f)).read() if os.path.exists(os.path.join(d, f)) else ""
    st = state_fields(read("state.md"))
    plan = read("plan.md")
    m = re.search(r"^# Plan — (.+)$", plan, re.M)
    title = (m.group(1).strip() if m else os.path.basename(os.path.dirname(os.path.abspath(d)))) + " — loop report"
    stage = st.get("stage", "")
    cur = "5" if stage.startswith("done") else (stage[:1] if stage[:1].isdigit() else "1")
    steps = "".join(
        f'<li class="{"done" if n < cur else "now" if n == cur else ""}"><span>{n}</span>{name}</li>' for n, name in STAGES)
    meta = "".join(f"<div><dt>{html.escape(k)}</dt><dd>{inline(v)}</dd></div>" for k, v in st.items())
    tabs, panels = [], []
    for f, name in SECTIONS:
        body = read(f)
        if not body:
            continue
        sid = f.replace(".md", "")
        tabs.append(f'<a href="#{sid}">{name}</a>')
        panels.append(f'<section class="panel" id="{sid}"><div class="eyebrow">.loop/{f}</div>{md(body)}</section>')
    page = TEMPLATE.format(title=html.escape(title), steps=steps, meta=meta, tabs="".join(tabs), panels="\n".join(panels))
    if "--standalone" in argv:
        page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    with open(argv[1], "w") as fh:
        fh.write(page)
    print(f"wrote {argv[1]}")
    return 0


TEMPLATE = """<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: engineering log. Stage rail on top, run metadata, then the .loop files as sections */
:root {{
  --bg: #f3f5f8; --surface: #ffffff; --ink: #18202b; --muted: #5b6676; --line: #d3dae4;
  --accent: #2343c8; --accent-soft: #e4e9fb;
  --ok: #138a52; --ok-soft: #d9f2e5; --warn: #b26b00; --warn-soft: #fbeccf; --crit: #cc2b2b; --crit-soft: #fadcdc;
  --f-display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --f-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0f141b; --surface: #171e28; --ink: #e6ebf2; --muted: #95a1b2; --line: #2c3746; --accent: #8ea4ff; --accent-soft: #1e2a52;
  --ok: #3fcf8a; --ok-soft: #12342a; --warn: #f0a83a; --warn-soft: #3a2a10; --crit: #ff6464; --crit-soft: #431a1a; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0f141b; --surface: #171e28; --ink: #e6ebf2; --muted: #95a1b2; --line: #2c3746; --accent: #8ea4ff; --accent-soft: #1e2a52;
  --ok: #3fcf8a; --ok-soft: #12342a; --warn: #f0a83a; --warn-soft: #3a2a10; --crit: #ff6464; --crit-soft: #431a1a; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--f-body); }}
.wrap {{ max-width: 980px; margin: 0 auto; padding-block: 24px 48px; display: grid; gap: 16px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
h1, h2, h3, h4 {{ font-family: var(--f-display); text-wrap: balance; margin: 18px 0 6px; }}
h1 {{ font-size: 1.8rem; margin: 0; }} h2 {{ font-size: 1.3rem; margin-top: 4px; }} h3 {{ font-size: 1.08rem; }} h4 {{ font-size: 0.98rem; }}
.eyebrow {{ font: 600 0.72rem/1 var(--f-body); text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
.rail {{ display: flex; gap: 6px; flex-wrap: wrap; list-style: none; padding: 0; margin: 0; }}
.rail li {{ display: flex; align-items: center; gap: 8px; padding: 6px 12px 6px 6px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); color: var(--muted); font-weight: 500; }}
.rail li span {{ display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; background: var(--line); color: var(--ink); font: 600 0.75rem var(--f-mono); }}
.rail li.done span {{ background: var(--ok); color: var(--surface); }}
.rail li.now {{ border-color: var(--accent); color: var(--ink); }}
.rail li.now span {{ background: var(--accent); color: var(--surface); }}
dl {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 8px 20px; margin: 0; }}
dl div {{ min-width: 0; }} dt {{ font: 600 0.72rem var(--f-body); text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
dd {{ margin: 2px 0 0; font: 0.85rem/1.4 var(--f-mono); overflow-wrap: anywhere; }}
nav {{ display: flex; gap: 6px; flex-wrap: wrap; }}
nav a {{ color: var(--accent); text-decoration: none; padding: 5px 10px; border-radius: 6px; background: var(--accent-soft); font-weight: 500; font-size: 0.88rem; }}
.panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; min-width: 0; }}
p, li {{ max-width: 75ch; }} ul {{ padding-left: 20px; }} li {{ margin: 3px 0; }}
li.task {{ list-style: none; margin-left: -20px; display: flex; gap: 8px; }}
.box {{ flex: none; width: 16px; height: 16px; margin-top: 3px; border: 1.5px solid var(--muted); border-radius: 4px; display: grid; place-items: center; font-size: 11px; color: var(--surface); }}
li.task.done .box {{ background: var(--ok); border-color: var(--ok); }}
code {{ font: 0.84em var(--f-mono); background: var(--bg); padding: 1px 4px; border-radius: 4px; }}
pre {{ background: var(--bg); padding: 10px 12px; border-radius: 8px; overflow-x: auto; }} pre code {{ background: none; padding: 0; }}
.tw {{ overflow-x: auto; }} table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; }}
th, td {{ text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font: 600 0.72rem var(--f-body); text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
a {{ color: var(--accent); }}
.pill {{ font: 600 0.72rem/1 var(--f-body); letter-spacing: 0.04em; padding: 3px 7px; border-radius: 999px; white-space: nowrap; }}
.pill.ok {{ background: var(--ok-soft); color: var(--ok); }} .pill.warn {{ background: var(--warn-soft); color: var(--warn); }}
.pill.crit {{ background: var(--crit-soft); color: var(--crit); }} .pill.neutral {{ background: var(--bg); color: var(--muted); }}
</style>
<div class="wrap">
  <header><div class="eyebrow">Loop engineering report</div><h1>{title}</h1></header>
  <ol class="rail" aria-label="Stages">{steps}</ol>
  <section class="panel"><dl>{meta}</dl></section>
  <nav aria-label="Sections">{tabs}</nav>
  {panels}
</div>
"""

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
