#!/bin/sh
# Keeps the installed copy in ~/.claude/calmline in step with the plugin version.
# The statusLine points at that copy because the plugin's own path changes on every update.
# my_segments.py is never touched. A git clone install manages itself, so it is left alone.
dest="$HOME/.claude/calmline"
[ -f "$dest/calmline.py" ] && [ ! -d "$dest/.git" ] || exit 0
mkdir -p "$dest/fixtures"
for f in calmline.py CLAUDE.md my_segments.example.py fixtures/full.json fixtures/minimal.json; do
  cmp -s "$CLAUDE_PLUGIN_ROOT/$f" "$dest/$f" || cp "$CLAUDE_PLUGIN_ROOT/$f" "$dest/$f"
done
