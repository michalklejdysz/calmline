#!/bin/sh
# calmline installer: curl -fsSL https://raw.githubusercontent.com/michalklejdysz/calmline/main/install.sh | sh
set -eu
src="${CALMLINE_SRC:-https://raw.githubusercontent.com/michalklejdysz/calmline/main}"
dest="$HOME/.claude/calmline"
settings="$HOME/.claude/settings.json"

# The status line runs outside any project, so a version-manager shim (asdf, pyenv) without a global
# version fails there: take the first python3 that runs from / .
py=""
for c in "$(command -v python3 || true)" /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -n "$c" ] && (cd / && "$c" -c 'import sys; assert sys.version_info >= (3, 8)') 2>/dev/null && py=$c && break
done
[ -n "$py" ] || { echo "calmline needs Python 3.8+ (python3)" >&2; exit 1; }

# Run from a git clone in $dest: the files are already there, only settings need updating.
if [ "$(cd "$(dirname "$0")" && pwd)" != "$dest" ]; then
  mkdir -p "$dest"
  for f in calmline.py CLAUDE.md my_segments.example.py; do
    curl -fsSL "$src/$f" -o "$dest/$f"
  done
fi

# Point statusLine at calmline; an existing statusLine is saved first so it can be restored.
"$py" - "$settings" "$dest" "$py" <<'PY'
import json, os, sys
settings, dest, py = sys.argv[1:]
data = {}
if os.path.exists(settings):
    with open(settings) as f:
        data = json.load(f)
previous = data.get("statusLine")
if previous and "calmline" not in json.dumps(previous):
    with open(os.path.join(dest, "previous-statusline.json"), "w") as f:
        json.dump(previous, f, indent=2)
    print("Your previous statusLine is saved in", os.path.join(dest, "previous-statusline.json"))
data["statusLine"] = {"type": "command", "command": f"{py} {os.path.join(dest, 'calmline.py')}"}
os.makedirs(os.path.dirname(settings), exist_ok=True)
tmp = settings + ".calmline-tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, settings)
PY

echo "calmline installed. It shows up in Claude Code within a few seconds."
echo "To change it, ask Claude in $dest, e.g. \"make it one line with only my usage\"."
