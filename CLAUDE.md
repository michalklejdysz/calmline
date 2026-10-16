# Working on calmline itself

- The plugin, and everything users get, is in `plugin/`: the status line (`plugin/calmline.py`), the rules for changing it (`plugin/CLAUDE.md`, read it first), the installer (`plugin/install.sh`, used by curl, git clone and `/calmline:install`), the install skill and the update hook. Repo-only files stay outside it (README, demo, tests), so they are never copied to users.
- Tests: `python3 -m unittest discover tests`. They must pass on Python 3.8 (`uv run --python 3.8 python -m unittest discover tests`).
- After changing `plugin/calmline.py`, run `python3 demo/render.py`, so the README images match the code.
- Releasing: bump `version` in `plugin/.claude-plugin/plugin.json`; users get it on their next plugin update. `my_segments.py` imports (`dim`, `paint`, `level`, `duration`, `until`, `LINES`, `SEGMENTS`) are public API: don't break them.
- The files copied to `~/.claude/calmline` are listed in `plugin/install.sh` and `plugin/hooks/update.sh`; a test keeps the two lists equal.
- Validate the plugin with `claude plugin validate .` before pushing.
- CI (`.github/workflows/ci.yml`) runs the tests on Python 3.8 and 3.13, macOS and Linux, plus shellcheck and the plugin validator. Lint shell locally with `uvx --from shellcheck-py shellcheck plugin/install.sh plugin/hooks/update.sh`.
- Releases: tag `vX.Y.Z` matching `plugin.json`, then `gh release create vX.Y.Z` with two or three lines on what changed for users.
