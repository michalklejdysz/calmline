#!/bin/sh
# calmline installer: curl -fsSL https://raw.githubusercontent.com/michalklejdysz/calmline/main/plugin/install.sh | sh
# Also run by /calmline:install with CALMLINE_SRC=file://<plugin folder>, and from a git clone.
# Everything runs from main() at the end, so a download cut off half way runs nothing.
set -eu

main() {
  src="${CALMLINE_SRC:-https://raw.githubusercontent.com/michalklejdysz/calmline/main/plugin}"
  dest="$HOME/.claude/calmline"
  settings="$HOME/.claude/settings.json"
  files="calmline.py CLAUDE.md my_segments.example.py fixtures/full.json fixtures/minimal.json"

  # The status line runs outside any project, so a version-manager shim (asdf, pyenv) without a global
  # version fails there: take the first python3 that runs from / .
  py=""
  for c in "$(command -v python3 || true)" /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    [ -n "$c" ] && (cd / && "$c" -c 'import sys; assert sys.version_info >= (3, 8)') 2>/dev/null && py=$c && break
  done
  [ -n "$py" ] || { echo "calmline needs Python 3.8+ (python3)" >&2; exit 1; }

  if [ -d "$dest/.git" ]; then
    run="$dest/plugin"  # a git clone: the files are already there, git pull updates them
  else
    run="$dest"
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    mkdir -p "$tmp/fixtures"
    for f in $files; do
      curl -fsSL "$src/$f" -o "$tmp/$f" || { echo "calmline: download of $f failed, nothing changed" >&2; exit 1; }
    done
    # Try the new copy before it replaces anything the status line already runs.
    "$py" "$tmp/calmline.py" < "$tmp/fixtures/minimal.json" > /dev/null \
      || { echo "calmline: the downloaded copy doesn't run with $py, nothing changed" >&2; exit 1; }
    mkdir -p "$run/fixtures"
    for f in $files; do
      mv "$tmp/$f" "$run/$f"
    done
  fi

  "$py" - "$settings" "$run" "$dest" "$py" <<'PY'
import json, os, shlex, shutil, sys

settings, run, dest, py = sys.argv[1:]
target = os.path.realpath(settings)  # a dotfiles symlink stays a symlink
data = {}
if os.path.exists(target):
    try:
        with open(target) as f:
            data = json.load(f)
    except ValueError as e:
        sys.exit(f"calmline: {settings} is not valid JSON ({e}). Fix it and run again; nothing was changed.")
    if not isinstance(data, dict):
        sys.exit(f"calmline: {settings} is not a JSON object. Fix it and run again; nothing was changed.")

previous = data.get("statusLine")
saved = os.path.join(dest, "previous-statusline.json")
if previous and "calmline" not in json.dumps(previous):
    with open(saved, "w") as f:
        json.dump(previous, f, indent=2)
    print("Your previous statusLine is saved in", saved)

data["statusLine"] = {"type": "command", "command": f"{shlex.quote(py)} {shlex.quote(os.path.join(run, 'calmline.py'))}"}
os.makedirs(os.path.dirname(target), exist_ok=True)
tmp = target + ".calmline-tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
if os.path.exists(target):
    shutil.copymode(target, tmp)  # settings.json can hold tokens: keep its permissions
os.replace(tmp, target)
PY

  echo "calmline installed. It shows up in Claude Code within a few seconds."
  echo "To change it, ask Claude in $run, e.g. \"make it one line with only my usage\"."
}

main "$@"
