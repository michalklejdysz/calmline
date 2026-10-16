#!/bin/sh
# Keeps the installed copy in ~/.claude/calmline in step with the plugin version.
# The statusLine points at that copy because the plugin's own path changes on every update.
# my_segments.py is never touched. A git clone install manages itself, so it is left alone.
# This hook runs async, so nobody sees its output: failures go to error.log.
dest="$HOME/.claude/calmline"
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$dest/calmline.py" ] && [ ! -d "$dest/.git" ] || exit 0
mkdir -p "$dest/fixtures"
for f in calmline.py CLAUDE.md my_segments.example.py fixtures/full.json fixtures/minimal.json; do
  cmp -s "$CLAUDE_PLUGIN_ROOT/$f" "$dest/$f" && continue
  # Copy, then rename: a status line rendering right now never reads a half-written file.
  cp "$CLAUDE_PLUGIN_ROOT/$f" "$dest/$f.tmp" && mv "$dest/$f.tmp" "$dest/$f" \
    || echo "$(date '+%Y-%m-%d %H:%M:%S') update: copying $f failed" >> "$dest/error.log"
done
