---
name: install
description: "Install calmline as the user's Claude Code status line, or reinstall it. Use when the user runs /calmline:install or asks to set up, install or switch to calmline."
---

# Install calmline

Plugins cannot set `statusLine` themselves, so you run the installer that does. It finds a Python that works outside any project, copies calmline to `~/.claude/calmline` (never touching `my_segments.py`), checks the copy runs, saves the user's previous status line and sets the new one while keeping every other setting, its permissions and a symlinked file.

1. Run:
   ```sh
   CALMLINE_SRC="file://${CLAUDE_PLUGIN_ROOT}" sh "${CLAUDE_PLUGIN_ROOT}/install.sh"
   ```
2. If it exits with an error, tell the user its message and stop. In particular, if it says `settings.json is not valid JSON`, do not repair the file yourself: show the user where it is broken and let them decide.
3. If it printed `Your previous statusLine is saved in …`, tell the user in one line that it can be restored.
4. Show the result: run the `command` from the `statusLine` key of `~/.claude/settings.json` with `< ~/.claude/calmline/fixtures/full.json` as input (read only that key; the file can hold secrets). If the output contains `name !` or `name ?`, read `~/.claude/calmline/error.log` and report it. Otherwise tell the user it appears in Claude Code within seconds, and that they can change it by asking, e.g. "make calmline one line with only my usage" (the rules are in `~/.claude/calmline/CLAUDE.md`).

**Uninstall** if asked: put the contents of `~/.claude/calmline/previous-statusline.json` back as `statusLine`, or remove the key if there is no such file. Edit only that key. Leave `~/.claude/calmline/` unless the user says to delete it.
