---
name: install
description: "Install calmline as the user's Claude Code status line, or reinstall it. Use when the user runs /calmline:install or asks to set up, install or switch to calmline."
---

# Install calmline

Set calmline as the user's status line. Plugins cannot set `statusLine` themselves, so you do it.

1. **Python.** The status line runs outside any project, where a version-manager shim (asdf, pyenv) without a global version fails. Try, in order, `python3` from PATH, `/usr/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`, each as `cd / && <candidate> -c 'import sys; assert sys.version_info >= (3, 8)'`. Use the first one that succeeds as the python path for steps 4 and 5. If none does, stop and tell the user calmline needs Python 3.8+.
2. **Copy files.** The plugin's own folder changes on every update, so the status line runs a stable copy:
   ```sh
   mkdir -p ~/.claude/calmline/fixtures
   cp "${CLAUDE_PLUGIN_ROOT}/calmline.py" "${CLAUDE_PLUGIN_ROOT}/CLAUDE.md" "${CLAUDE_PLUGIN_ROOT}/my_segments.example.py" ~/.claude/calmline/
   cp "${CLAUDE_PLUGIN_ROOT}/fixtures/full.json" "${CLAUDE_PLUGIN_ROOT}/fixtures/minimal.json" ~/.claude/calmline/fixtures/
   ```
   Never overwrite an existing `~/.claude/calmline/my_segments.py`: it holds the user's changes. The plugin's SessionStart hook keeps the other files current after updates.
3. **Save what is there.** Read only the `statusLine` key of `~/.claude/settings.json` (e.g. `jq '.statusLine'`); the file can hold secrets, so do not print the rest. If a statusLine exists and is not calmline, save it to `~/.claude/calmline/previous-statusline.json` and tell the user, in one line, what it ran and that it can be restored.
4. **Set it.** Write `"statusLine": {"type": "command", "command": "<python path> ~/.claude/calmline/calmline.py"}` into `~/.claude/settings.json`, keeping every other key. Edit the file; do not rebuild it from a shell string.
5. **Show it.** Run `<python path> ~/.claude/calmline/calmline.py < "${CLAUDE_PLUGIN_ROOT}/fixtures/full.json"` and show the user the output. Tell them it appears in Claude Code within seconds, and that they can change it by asking, e.g. "make calmline one line with only my usage" (rules for that are in `~/.claude/calmline/CLAUDE.md`).

**Uninstall** if asked: restore `previous-statusline.json` into `statusLine`, or remove the key if there is none; leave `~/.claude/calmline/` unless the user says to delete it.
