#!/usr/bin/env python3
"""Build the editable PowerPoint deck and verify it before it is handed over.

Exits non-zero if the saved file does not match the source DECK, so this can
gate a commit or a send.
"""
import sys

from deck_pptx import render_pptx
from verify_pptx import structural
from working_meeting import DECK

OUT = "working_meeting_2026-08-13.pptx"

if __name__ == "__main__":
    render_pptx(DECK, OUT)
    checked, problems = structural(DECK, OUT)
    print(f"{OUT}: {len(DECK['slides'])} slides, {checked} content items checked")
    for p in problems:
        print("  PROBLEM:", p)
    if problems:
        sys.exit(1)
    print("verified: no problems")
