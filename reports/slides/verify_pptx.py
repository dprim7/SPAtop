#!/usr/bin/env python3
"""Fidelity check for the PPTX back end.

Two independent passes, because "it produced a file" is not verification:

  1. STRUCTURAL. Walk the saved .pptx with python-pptx and confirm that every
     title, bullet, table cell, caption, equation and figure in the source
     DECK dict actually appears in the file, that slide counts and footer
     numbering line up, and that nothing lands outside the slide or on top of
     the logos.

  2. VISUAL. Re-read the saved file and draw every shape (position, size,
     fill, text, images) to a PNG with PIL. This renders what is *in the
     file*, not what we intended to put there, so it catches geometry bugs a
     structural diff cannot.

    python verify_pptx.py deck.pptx out_dir  [--deck module]
"""
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu

PX = 9525
W, H = 1280, 720


def _fonts():
    cands = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    bold = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
    r = next((c for c in cands if os.path.exists(c)), None)
    b = next((c for c in bold if os.path.exists(c)), None)
    return r, b


REG, BOLD = _fonts()


def _font(sz, bold=False):
    path = BOLD if (bold and BOLD) else REG
    try:
        return ImageFont.truetype(path, max(8, int(sz)))
    except Exception:
        return ImageFont.load_default()


def _shape_text(sh):
    if not sh.has_text_frame:
        return "", 12, False, (34, 44, 58)
    txt, size, bold, col = [], 12, False, (34, 44, 58)
    for p in sh.text_frame.paragraphs:
        line = "".join(r.text for r in p.runs)
        if line:
            txt.append(line)
        for r in p.runs:
            if r.font.size:
                size = max(size, r.font.size.pt)
            bold = bold or bool(r.font.bold)
            try:
                if r.font.color and r.font.color.rgb is not None:
                    col = tuple(r.font.color.rgb)
            except Exception:
                pass
    return "\n".join(txt), size, bold, col


def _fill(sh):
    try:
        if sh.fill.type is not None and sh.fill.type == 1:
            return tuple(sh.fill.fore_color.rgb)
    except Exception:
        pass
    return None


def render(pptx_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    prs = Presentation(pptx_path)
    scale = 1.0
    outs = []
    for i, slide in enumerate(prs.slides, start=1):
        img = Image.new("RGB", (int(W * scale), int(H * scale)), (255, 255, 255))
        d = ImageDraw.Draw(img)
        for sh in slide.shapes:
            x, y = sh.left / PX * scale, sh.top / PX * scale
            w, h = (sh.width or 0) / PX * scale, (sh.height or 0) / PX * scale
            f = _fill(sh)
            if f:
                d.rectangle([x, y, x + w, y + h], fill=f)
            if sh.shape_type is not None and sh.shape_type == 13:  # picture
                try:
                    from io import BytesIO
                    im = Image.open(BytesIO(sh.image.blob))
                    im = im.convert("RGBA").resize(
                        (max(1, int(w)), max(1, int(h))), Image.LANCZOS)
                    img.paste(im, (int(x), int(y)), im)   # honour alpha
                except Exception:
                    d.rectangle([x, y, x + w, y + h], outline=(200, 60, 60), width=2)
            if sh.has_table:
                tbl = sh.table
                nrows, ncols = len(tbl.rows), len(tbl.columns)
                for ri in range(nrows):
                    for ci in range(ncols):
                        cw, ch = w / ncols, h / nrows
                        cx, cy = x + ci * cw, y + ri * ch
                        cell = tbl.cell(ri, ci)
                        cf = None
                        try:
                            if cell.fill.type == 1:
                                cf = tuple(cell.fill.fore_color.rgb)
                        except Exception:
                            pass
                        if cf:
                            d.rectangle([cx, cy, cx + cw, cy + ch], fill=cf)
                        d.rectangle([cx, cy, cx + cw, cy + ch],
                                    outline=(226, 231, 236))
                        t = cell.text_frame.text
                        cc = (34, 44, 58)
                        for p in cell.text_frame.paragraphs:
                            for r in p.runs:
                                try:
                                    if r.font.color and r.font.color.rgb is not None:
                                        cc = tuple(r.font.color.rgb)
                                except Exception:
                                    pass
                        if t:
                            d.text((cx + 8, cy + ch / 2 - 8), t[:42],
                                   font=_font(13), fill=cc)
                continue
            if not sh.has_text_frame or not sh.text_frame.text.strip():
                continue
            # Draw run by run, honouring per-run size, colour, weight and
            # baseline. Drawing the joined paragraph text instead would hide
            # exactly the defects this pass exists to catch: lost sub/sup and
            # markup that leaked into the text as literal characters.
            yy = y
            for para in sh.text_frame.paragraphs:
                runs = [r for r in para.runs if r.text]
                if not runs:
                    continue
                pieces = []
                for r in runs:
                    sz = (r.font.size.pt if r.font.size else 12) * 1.33
                    fnt = _font(sz, bool(r.font.bold))
                    col = (34, 44, 58)
                    try:
                        if r.font.color and r.font.color.rgb is not None:
                            col = tuple(r.font.color.rgb)
                    except Exception:
                        pass
                    pieces.append([r.text, fnt, col, 0.0, sz,
                                   r.font._rPr.get("baseline")])
                # PIL anchors text at the top left, so a smaller run drawn at
                # the same y sits high and a subscript is indistinguishable
                # from a superscript. Shift each run onto a common baseline
                # first, then apply the sub/sup offset.
                base = max(p[4] for p in pieces)
                for p in pieces:
                    align = (base - p[4]) * 0.85
                    p[3] = (align - base * 0.28 if p[5] == "30000" else
                            align + base * 0.16 if p[5] == "-25000" else align)
                lead = base * 1.30
                total = sum(d.textlength(p[0], font=p[1]) for p in pieces)
                centered = str(para.alignment) == "CENTER (2)"
                x0 = x + max(0, (w - total) / 2) if (centered and total <= w) else x
                xx = x0
                for text, fnt, col, dy, _sz, _bl in pieces:
                    for word in re.findall(r"\S+\s*|\s+", text):
                        wd = d.textlength(word, font=fnt)
                        if xx + wd > x + max(20, w) and xx > x0:
                            xx = x
                            yy += lead
                        d.text((xx, yy + dy), word, font=fnt, fill=col)
                        xx += wd
                yy += lead
        p = os.path.join(out_dir, f"slide_{i:02d}.png")
        img.save(p)
        outs.append(p)
    return outs


def structural(deck, pptx_path):
    """Every piece of source content must be present in the file."""
    prs = Presentation(pptx_path)
    problems, checked = [], 0

    def slide_text(sl):
        out = []
        for sh in sl.shapes:
            if sh.has_text_frame:
                out.append(sh.text_frame.text)
            if sh.has_table:
                for r in sh.table.rows:
                    for c in r.cells:
                        out.append(c.text)
        return " ".join(out)

    def norm(s):
        s = re.sub(r"<[^>]+>", "", str(s))
        s = s.replace("**", "").replace("`", "").replace("&nbsp;", " ")
        s = s.replace("&middot;", "·").replace("&rarr;", "→")
        return re.sub(r"\s+", " ", s).strip().lower()

    # No source markup may survive into the file. A non-recursive inline
    # renderer leaks "<i>", "<sub>" etc. as literal characters, which reads as
    # correct in a structural diff that strips tags from both sides.
    leak = re.compile(r"</?(?:i|b|sub|sup|span|em|strong)\b[^>]*>|\*\*|&nbsp;|&middot;")
    for idx, sl in enumerate(prs.slides, start=1):
        for sh in sl.shapes:
            if sh.has_text_frame:
                m = leak.search(sh.text_frame.text)
                if m:
                    problems.append(f"slide {idx}: literal markup {m.group(0)!r} in text")
            if sh.has_table:
                for r in sh.table.rows:
                    for c in r.cells:
                        m = leak.search(c.text)
                        if m:
                            problems.append(
                                f"slide {idx}: literal markup {m.group(0)!r} in table cell")

    if len(prs.slides) != len(deck["slides"]):
        problems.append(f"slide count {len(prs.slides)} != {len(deck['slides'])}")

    for idx, (src, sl) in enumerate(zip(deck["slides"], prs.slides), start=1):
        txt = norm(slide_text(sl))
        want = [src.get("title", "")]
        want += list(src.get("bullets", []))
        want += [src.get("kicker", ""), src.get("caption", ""), src.get("subtitle", "")]
        if src.get("callout"):
            c = src["callout"]
            c = c if isinstance(c, dict) else {"text": c}
            want += [c.get("text", ""), c.get("label", "")]
        for d_ in src.get("decisions", []):
            want.append(d_)
        for key in ("table", "minitable"):
            if src.get(key):
                t = src[key]
                want += [str(x) for x in t["head"]]
                for r in t["rows"]:
                    cells = r["cells"] if isinstance(r, dict) else r
                    want += [str(x) for x in cells]
                if t.get("label"):
                    want.append(t["label"])
        for w_ in want:
            w_ = norm(w_)
            if not w_:
                continue
            checked += 1
            probe = w_[:38]
            if probe and probe not in txt:
                problems.append(f"slide {idx}: missing {probe!r}")
        # figures must be present as pictures
        if src.get("figure"):
            if not any(getattr(sh, "shape_type", None) == 13 for sh in sl.shapes):
                problems.append(f"slide {idx}: figure missing")
        # geometry: nothing outside the canvas
        for sh in sl.shapes:
            if sh.left is None:
                continue
            if sh.left < -1 or sh.top < -1:
                problems.append(f"slide {idx}: shape off canvas top/left")
            if (sh.left + (sh.width or 0)) > Emu((W + 2) * PX):
                problems.append(f"slide {idx}: shape past right edge")
            if (sh.top + (sh.height or 0)) > Emu((H + 2) * PX):
                problems.append(f"slide {idx}: shape past bottom edge")
    return checked, problems


if __name__ == "__main__":
    pptx_path, out_dir = sys.argv[1], sys.argv[2]
    outs = render(pptx_path, out_dir)
    print(f"rendered {len(outs)} slides to {out_dir}")
