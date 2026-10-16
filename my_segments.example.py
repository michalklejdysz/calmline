"""Your own segments. Copy to my_segments.py (gitignored, so updates never conflict) and edit.

Easier: ask your Claude, e.g. "add a calmline segment that shows the active Python venv".
It reads CLAUDE.md in this repo and knows the rules.
"""
import os

from calmline import LINES, dim


def venv(d):
    path = os.environ.get("VIRTUAL_ENV")
    return path and dim("venv ") + os.path.basename(path)


SEGMENTS = {"venv": venv}

# Default layout with the new segment at the end of the first line.
LINES = [LINES[0] + ["venv"], LINES[1]]
