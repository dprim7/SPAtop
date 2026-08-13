# Slide standard

`deck.py` is the theme + layout engine; a deck is a content file (see
`working_meeting.py`) that imports `render()`. Build with:

```bash
cd reports/slides && python3 working_meeting.py
```

Outputs a self-contained `.html` (figures embedded — safe to email) and a
`_notes.md` speaker-notes appendix.

**Present**: open the HTML, arrow keys to navigate.
**PDF**: ⌘/Ctrl-P → landscape, margins *none*, background graphics *on*.

## House rules (enforced by the template's shape)

1. **Assertion headlines.** The slide title is the finding as a sentence —
   "Pairwise wins tttt and the gap grows with data", not "tttt results".
2. **One idea per slide**, ≤4 bullets, ≤10 words each. Bullets prompt what you
   say; they are not what you read out.
3. **One piece of evidence** per slide — a figure *or* a compact table, big.
4. **Detail goes in `notes`**, never on the slide. Notes are the Q&A ammunition.
5. **Numbers are tabular**; the winning row is highlighted, not explained.

## Brand

Palette follows the UC San Diego primary colours (Navy `#182B49`, Blue
`#00629B`, Gold `#FFCD00`) — confirm against the current brand guide before an
external talk.

**Logos** are drop-in and deliberately not vendored — use the real assets, not
redrawn ones:

| file | source |
|---|---|
| `assets/ucsd-logo.png` | brand.ucsd.edu |
| `assets/cms-logo.png`  | CMS collaboration resources |

Missing assets render as a dashed placeholder so the layout stays reviewable.
Placement follows the HEP convention: CMS top-left / UCSD top-right on the
title slide, both small together in the top-right on content slides (so the
headline keeps its left edge). Set `LOGO_SPLIT = True` in `deck.py` to mirror
the split onto every slide.

## This is also a user-level skill

Installed at `~/.claude/skills/slides/` so it works in *any* project, not just
SPAtop — ask for slides in any session and it applies these rules. The copy
here is the SPAtop-local one; keep them in sync if you change the engine.
