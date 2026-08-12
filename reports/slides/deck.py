#!/usr/bin/env python3
"""Daniel's slide deck generator — UCSD-themed 16:9 HTML slides.

Theme is code, content is data: a deck is a list of slide dicts (see
`working_meeting.py` for an example). Renders a self-contained HTML file
(figures embedded as data URIs) that
  * navigates with arrow keys / space / click,
  * prints to a standard 16:9 PDF via the browser (Cmd/Ctrl-P, landscape,
    background graphics ON, margins none),
  * publishes as-is to a shareable artifact page.

House rules this template enforces (the point of having a standard):
  1. ASSERTION HEADLINES. The title of a slide is the finding, written as a
     sentence -- "Pairwise wins tttt and the gap grows with data", not
     "tttt results". If you can't say it in a sentence, the slide isn't ready.
  2. ONE IDEA PER SLIDE, <=4 bullets, <=10 words each. Bullets are prompts for
     what you say, not what you read out.
  3. ONE piece of evidence per slide: a figure OR a compact table, sized big.
  4. DETAIL LIVES IN `notes`. Notes never render on the slide; they print in
     the speaker-notes appendix (--notes) and are there for the Q&A.
  5. Numbers are tabular; the row that wins is highlighted, never explained.

BRAND ASSETS (drop-in, not fabricated):
  reports/slides/assets/ucsd-logo.png   <- official mark from brand.ucsd.edu
  If the file is absent the deck renders cleanly without it.
Palette below follows the UC San Diego primary colours; confirm against the
current brand guide before an external talk.
"""
import base64
import html as _html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# --- UC San Diego primary palette -------------------------------------------
NAVY = "#182B49"   # UCSD Navy   -- headlines, title slide ground, table header
BLUE = "#00629B"   # UCSD Blue   -- secondary accent, links, one data series
GOLD = "#FFCD00"   # UCSD Gold   -- the rule under headlines, winner highlight
INK = "#222C3A"    # body text
MUTED = "#6E7A8A"  # footers, captions
PAPER = "#FFFFFF"
WASH = "#F4F6F8"   # table zebra / panel fill


def _uri(path):
    """Embed a local image as a data URI (None-safe)."""
    if not path:
        return None
    p = path if os.path.isabs(path) else os.path.join(HERE, path)
    if not os.path.exists(p):
        return None
    ext = os.path.splitext(p)[1].lstrip(".").lower()
    mime = "image/svg+xml" if ext == "svg" else f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
    with open(p, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _esc(s):
    return _html.escape(str(s), quote=False)


def _rich(s):
    """Allow a tiny inline vocabulary in content strings: **bold**, `mono`."""
    out = _esc(s)
    while "**" in out:
        out = out.replace("**", "<b>", 1).replace("**", "</b>", 1)
    while "`" in out:
        out = out.replace("`", "<span class='m'>", 1).replace("`", "</span>", 1)
    return out


# --- slide renderers ---------------------------------------------------------

def _title_slide(s, logo):
    sub = f"<p class='t-sub'>{_rich(s['subtitle'])}</p>" if s.get("subtitle") else ""
    mark = f"<img class='t-logo' src='{logo}' alt=''>" if logo else ""
    meta = " &nbsp;·&nbsp; ".join(_esc(x) for x in s.get("meta", []))
    return f"""<section class="slide title">
  <div class="t-body">
    {mark}
    <h1>{_rich(s['title'])}</h1>
    <div class="t-rule"></div>
    {sub}
  </div>
  <div class="t-meta">{meta}</div>
</section>"""


def _divider_slide(s, logo):
    return f"""<section class="slide divider">
  <div class="d-body">
    <div class="d-rule"></div>
    <h2>{_rich(s['title'])}</h2>
  </div>
</section>"""


def _bullets_html(items):
    if not items:
        return ""
    return "<ul class='bul'>" + "".join(f"<li>{_rich(b)}</li>" for b in items) + "</ul>"


def _table_html(tbl):
    head = "".join(f"<th>{_rich(c)}</th>" for c in tbl["head"])
    rows = []
    for r in tbl["rows"]:
        cls = " class='win'" if r.get("win") else ""
        cells = "".join(f"<td>{_rich(c)}</td>" for c in r["cells"])
        rows.append(f"<tr{cls}>{cells}</tr>")
    return (f"<div class='tw'><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _content_slide(s, logo, num, total, footer):
    body = ""
    fig = _uri(s.get("figure"))
    if fig:
        cap = f"<figcaption>{_rich(s['caption'])}</figcaption>" if s.get("caption") else ""
        body += f"<figure class='fig'><img src='{fig}' alt=''>{cap}</figure>"
    if s.get("table"):
        body += _table_html(s["table"])
    body += _bullets_html(s.get("bullets"))
    if s.get("kicker"):
        body += f"<p class='kicker'>{_rich(s['kicker'])}</p>"
    layout = "split" if (fig and s.get("bullets")) else "stack"
    mark = f"<img class='f-logo' src='{logo}' alt=''>" if logo else ""
    return f"""<section class="slide">
  <header><h2>{_rich(s['title'])}</h2><div class="rule"></div></header>
  <div class="body {layout}">{body}</div>
  <footer>{mark}<span class="f-txt">{_esc(footer)}</span><span class="f-num">{num}</span></footer>
</section>"""


def _decisions_slide(s, logo, num, total, footer):
    items = "".join(
        f"<li><span class='dn'>{i+1}</span><span class='dt'>{_rich(d)}</span></li>"
        for i, d in enumerate(s["decisions"]))
    mark = f"<img class='f-logo' src='{logo}' alt=''>" if logo else ""
    return f"""<section class="slide">
  <header><h2>{_rich(s['title'])}</h2><div class="rule"></div></header>
  <div class="body stack"><ol class="dec">{items}</ol></div>
  <footer>{mark}<span class="f-txt">{_esc(footer)}</span><span class="f-num">{num}</span></footer>
</section>"""


CSS = f"""
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;background:#20242b;
  font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:{INK};}}
.deck{{display:flex;flex-direction:column;align-items:center;gap:22px;padding:26px 14px 60px;}}
.slide{{position:relative;width:1280px;height:720px;flex:0 0 auto;background:{PAPER};
  overflow:hidden;box-shadow:0 6px 26px rgba(0,0,0,.34);padding:58px 72px 0;}}
.slide header{{margin-bottom:26px;}}
.slide h2{{font-size:40px;line-height:1.14;letter-spacing:-.02em;font-weight:700;
  color:{NAVY};margin:0;max-width:1040px;text-wrap:balance;}}
.rule{{width:104px;height:5px;background:{GOLD};margin-top:18px;}}
.body{{height:474px;display:flex;gap:44px;}}
.body.stack{{flex-direction:column;}}
.body.split{{flex-direction:row;align-items:flex-start;}}
.body.split .fig{{flex:1 1 58%;min-width:0;}}
.body.split .bul{{flex:1 1 42%;}}
.bul{{list-style:none;margin:0;padding:0;}}
.bul li{{font-size:25px;line-height:1.42;margin:0 0 17px;padding-left:26px;position:relative;}}
.bul li::before{{content:"";position:absolute;left:0;top:14px;width:11px;height:3px;background:{GOLD};}}
.bul li b{{color:{NAVY};font-weight:700;}}
.kicker{{margin:6px 0 0;font-size:23px;color:{BLUE};font-weight:600;max-width:1000px;}}
.fig{{margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;width:100%;}}
.fig img{{max-width:100%;max-height:412px;object-fit:contain;}}
.fig figcaption{{margin-top:10px;font-size:16px;color:{MUTED};max-width:1000px;text-align:center;}}
.tw{{width:100%;overflow:hidden;}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;}}
thead th{{background:{NAVY};color:#fff;text-align:left;font-size:17px;font-weight:600;
  letter-spacing:.03em;padding:12px 16px;}}
tbody td{{padding:12px 16px;font-size:23px;border-bottom:1px solid #E2E7EC;
  font-family:ui-monospace,Menlo,Consolas,monospace;}}
tbody td:first-child{{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:{NAVY};}}
tbody tr:nth-child(even) td{{background:{WASH};}}
tbody tr.win td{{background:{GOLD};font-weight:700;color:{NAVY};}}
.m{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92em;}}
.dec{{list-style:none;margin:0;padding:0;}}
.dec li{{display:flex;gap:18px;align-items:flex-start;margin:0 0 20px;}}
.dn{{flex:0 0 auto;width:34px;height:34px;border-radius:50%;background:{NAVY};color:#fff;
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px;}}
.dt{{font-size:25px;line-height:1.4;max-width:1020px;}}
.dt b{{color:{NAVY};}}
.slide footer{{position:absolute;left:72px;right:72px;bottom:26px;display:flex;
  align-items:center;gap:16px;border-top:1px solid #E2E7EC;padding-top:12px;}}
.f-logo{{height:30px;width:auto;}}
.f-txt{{font-size:15px;color:{MUTED};}}
.f-num{{margin-left:auto;font-size:15px;color:{MUTED};font-variant-numeric:tabular-nums;}}
.slide.title{{background:{NAVY};color:#fff;display:flex;flex-direction:column;
  justify-content:center;padding:0 92px;}}
.t-logo{{height:56px;width:auto;margin-bottom:34px;display:block;}}
.slide.title h1{{font-size:60px;line-height:1.08;letter-spacing:-.025em;font-weight:700;
  margin:0;max-width:1020px;text-wrap:balance;}}
.t-rule{{width:132px;height:6px;background:{GOLD};margin:26px 0;}}
.t-sub{{font-size:27px;line-height:1.36;color:#C8D4E2;margin:0;max-width:940px;font-weight:300;}}
.t-meta{{position:absolute;left:92px;bottom:52px;font-size:18px;color:#8FA3BA;}}
.slide.divider{{background:{WASH};display:flex;align-items:center;padding:0 92px;}}
.d-rule{{width:104px;height:5px;background:{GOLD};margin-bottom:22px;}}
.slide.divider h2{{font-size:52px;color:{NAVY};}}
@media print{{
  @page{{size:1280px 720px;margin:0;}}
  html,body{{background:#fff;}}
  .deck{{gap:0;padding:0;}}
  .slide{{box-shadow:none;page-break-after:always;break-after:page;}}
  .hint{{display:none!important;}}
}}
.hint{{position:fixed;right:16px;bottom:14px;background:rgba(24,43,73,.92);color:#fff;
  font-size:12px;padding:7px 12px;border-radius:4px;z-index:9;}}
"""

JS = """
const slides=[...document.querySelectorAll('.slide')];let i=0;
function go(n){i=Math.max(0,Math.min(slides.length-1,n));
  slides[i].scrollIntoView({behavior:'smooth',block:'center'});}
addEventListener('keydown',e=>{
  if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1);}
  if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();go(i-1);}
  if(e.key==='Home')go(0); if(e.key==='End')go(slides.length-1);});
new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting)i=slides.indexOf(x.target);}),
  {threshold:.6}).observe;
slides.forEach(s=>new IntersectionObserver(es=>es.forEach(x=>{
  if(x.isIntersecting)i=slides.indexOf(x.target);}),{threshold:.6}).observe(s));
"""


def render(deck, out_path, notes_path=None):
    """deck = {title, footer, slides:[...]}; writes self-contained HTML."""
    logo = _uri(os.path.join(ASSETS, "ucsd-logo.png")) or _uri(os.path.join(ASSETS, "ucsd-logo.svg"))
    footer = deck.get("footer", "")
    body, n, notes = [], 0, []
    total = sum(1 for s in deck["slides"] if s.get("type") not in ("title", "divider"))
    for s in deck["slides"]:
        t = s.get("type", "content")
        if t == "title":
            body.append(_title_slide(s, logo))
        elif t == "divider":
            body.append(_divider_slide(s, logo))
        else:
            n += 1
            fn = _decisions_slide if t == "decisions" else _content_slide
            body.append(fn(s, logo, n, total, footer))
        if s.get("notes"):
            notes.append((s.get("title", ""), s["notes"]))

    doc = (f"<title>{_esc(deck['title'])}</title>\n<style>{CSS}</style>\n"
           f"<div class='deck'>\n" + "\n".join(body) + "\n</div>\n"
           f"<div class='hint'>← → to navigate · ⌘P → landscape, no margins, "
           f"background graphics ON for PDF</div>\n<script>{JS}</script>")
    with open(out_path, "w") as f:
        f.write(doc)

    if notes_path:
        with open(notes_path, "w") as f:
            f.write(f"# Speaker notes — {deck['title']}\n\n")
            for title, note in notes:
                f.write(f"## {title}\n\n{note}\n\n")
    return out_path
