#!/usr/bin/env python3
"""calmline: a calm status line for Claude Code.

Reads the status line JSON from stdin, prints one line per entry in LINES.
Labels and separators are dimmed; colour appears only where a number needs attention.
Standard library only. Your own segments go in my_segments.py (see CLAUDE.md).
"""
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time

RESET = "\033[0m"
BUDGET_S = 0.3  # a segment slower than this is dropped, so the line never lags


def paint(code, s):
    return f"\033[{code}m{s}{RESET}"


def dim(s):
    return paint("2", s)


def level(v, warn, alarm):
    """Percentage coloured green / yellow / red by threshold."""
    return paint("31" if v >= alarm else "33" if v >= warn else "32", f"{v:.0f}%")


def duration(ms):
    s = int(ms / 1000)
    return f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


def until(ts, now=None):
    m = max(0, int(ts - (now or time.time())) // 60)
    if m >= 1440:
        return f"{m // 1440}d{m % 1440 // 60}h"
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}m"


STATE_MAX_AGE_S = 7 * 86400


def state_dir():
    return os.path.expanduser(os.environ.get("CALMLINE_STATE", "~/.claude/calmline-state"))


def log_error(message):
    """Errors go to error.log next to this file too: Claude Code does not show a status line's stderr."""
    print(f"calmline: {message}", file=sys.stderr)
    path = os.environ.get("CALMLINE_LOG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
    try:
        mode = "w" if os.path.exists(path) and os.path.getsize(path) > 100_000 else "a"  # keep it small
        with open(path, mode) as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def write_json(path, data):
    """Atomic: a reader never sees a half-written file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def prune_state(directory, now):
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if now - os.path.getmtime(path) > STATE_MAX_AGE_S:
            os.remove(path)


# Segments: each takes the status line input and returns a string, or None to hide itself.


def session(d):
    name = d.get("session_name")
    return name and paint("1", name)


def directory(d):
    """Folder Claude is working in, home shortened to ~ and only the last two parts kept."""
    cwd = d.get("cwd")
    if not cwd:
        return None
    home = os.path.expanduser("~")
    path = "~" + cwd[len(home):] if cwd == home or cwd.startswith(home + os.sep) else cwd
    parts = path.split(os.sep)
    return paint("34", os.sep.join(parts[-2:]) if len(parts) > 3 else path)


def git(d):
    cwd = d.get("cwd")
    if not cwd:
        return None
    run = lambda *a: subprocess.run(
        ["git", "-C", cwd, *a], capture_output=True, text=True, timeout=0.25
    ).stdout.strip()
    try:
        branch = run("branch", "--show-current") or run("rev-parse", "--short", "HEAD")
    except FileNotFoundError:  # git is optional
        return None
    if not branch:
        return None
    dirty = paint("33", " ●") if run("status", "--porcelain", "-uno") else ""
    return paint("36", f"⎇ {branch}") + dirty


def model(d):
    name = (d.get("model") or {}).get("display_name")
    if not name:
        return None
    effort = (d.get("effort") or {}).get("level")
    return name + (dim(f" · {effort}") if effort else "") + (paint("33", " ⚡") if d.get("fast_mode") else "")


def context(d):
    used = (d.get("context_window") or {}).get("used_percentage")
    return None if used is None else dim("ctx ") + level(used, 40, 70)


def cache(d):
    hit = (d.get("prompt_cache") or {}).get("hit_ratio")
    return None if hit is None else dim("cache ") + f"{hit * 100:.0f}%"


def ponytail(d):
    """Mode of the ponytail plugin, if it is installed."""
    try:
        with open(os.path.expanduser("~/.claude/.ponytail-active")) as f:
            return f.read().strip() or None
    except OSError:
        return None


def last_turn(d):
    """(cost, api_ms) of the previous turn: change in session totals between two prompt starts.

    One state file per session, so parallel Claude Code sessions don't reset each other.
    """
    c = d.get("cost") or {}
    total, ms = c.get("total_cost_usd"), c.get("total_api_duration_ms") or 0
    session = re.sub(r"[^A-Za-z0-9_-]", "_", str(d.get("session_id") or "default"))[:80]
    path = os.path.join(state_dir(), session + ".json")
    try:
        with open(path) as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = None
    keys = ("start", "start_ms", "end", "end_ms")
    valid = isinstance(s, dict) and all(isinstance(s.get(k), (int, float)) for k in keys)
    new_prompt = not valid or s.get("prompt") != d.get("prompt_id")
    if not valid:
        s = {"prompt": d.get("prompt_id"), "start": total, "start_ms": ms, "last": None}
    elif new_prompt:
        last = [s["end"] - s["start"], s["end_ms"] - s["start_ms"]]
        s = {"prompt": d.get("prompt_id"), "start": s["end"], "start_ms": s["end_ms"], "last": last}
    s["end"], s["end_ms"] = total, ms
    try:
        write_json(path, s)
        if new_prompt:
            prune_state(state_dir(), time.time())
    except OSError as e:  # the session total still shows; only the last-turn figure needs the state
        log_error(f"state not saved: {e!r}")
    return s.get("last")


def cost(d):
    total = (d.get("cost") or {}).get("total_cost_usd")
    if total is None:
        return None
    last = last_turn(d)
    return f"${total:.2f}" + (dim(f" · last ${last[0]:.2f} · {duration(last[1])}") if last else "")


def limit(key, label):
    def segment(d):
        r = (d.get("rate_limits") or {}).get(key) or {}
        if r.get("used_percentage") is None:
            return None
        reset = dim(f" ↻{until(r['resets_at'])}") if r.get("resets_at") else ""
        return dim(label + " ") + level(r["used_percentage"], 50, 80) + reset

    return segment


SEGMENTS = {
    "session": session,
    "dir": directory,
    "git": git,
    "model": model,
    "context": context,
    "cache": cache,
    "ponytail": ponytail,
    "cost": cost,
    "5h": limit("five_hour", "5h"),
    "week": limit("seven_day", "week"),
}

LINES = [
    ["session", "dir", "git", "model", "context", "cache"],
    ["ponytail", "cost", "5h", "week"],
]

SEPARATOR = dim("  │  ")


class _Slow(BaseException):  # not an Exception, so a segment's own `except Exception` can't swallow the timeout
    pass


def _raise_slow(*_):
    raise _Slow


def run_segment(name, fn, d):
    """A status line must always render: a slow or broken segment becomes a small marker."""
    timed = hasattr(signal, "setitimer")
    if timed:
        signal.signal(signal.SIGALRM, _raise_slow)
        signal.setitimer(signal.ITIMER_REAL, BUDGET_S)
    try:
        result = fn(d)
        if timed:
            signal.setitimer(signal.ITIMER_REAL, 0)
        if result is None or isinstance(result, str):
            return result
        raise TypeError(f"returned {type(result).__name__}, expected str or None")
    except (_Slow, subprocess.TimeoutExpired):
        return dim(f"{name} …")
    except (Exception, SystemExit) as e:  # any bug in any segment, ours or the user's
        log_error(f"segment {name!r} failed: {e!r}")
        return paint("31", f"{name} !")
    finally:
        if timed:
            signal.setitimer(signal.ITIMER_REAL, 0)


def segment_text(name, segments, d):
    if name not in segments:
        return paint("31", f"{name} ?")
    try:
        return run_segment(name, segments[name], d)
    except _Slow:  # the alarm went off inside run_segment's own handlers, after the segment ran
        return dim(f"{name} …")


def load_custom(path):
    """Merge SEGMENTS and LINES from my_segments.py next to this file, if present."""
    if not os.path.exists(path):
        return {}, None
    sys.modules.setdefault("calmline", sys.modules[__name__])
    sys.dont_write_bytecode = True  # a cached .pyc can hide an edit made within the same second
    spec = importlib.util.spec_from_file_location("my_segments", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    segments, lines = getattr(mod, "SEGMENTS", {}), getattr(mod, "LINES", None)
    if not isinstance(segments, dict) or not all(callable(f) for f in segments.values()):
        raise TypeError("SEGMENTS must be a dict of name -> function")
    if lines is not None and not (
        isinstance(lines, list) and all(isinstance(l, list) and all(isinstance(n, str) for n in l) for l in lines)
    ):
        raise TypeError("LINES must be a list of lists of segment names")
    return segments, lines


def render(d, segments=None, lines=None):
    segments = segments or SEGMENTS
    out = []
    for names in lines or LINES:
        parts = [segment_text(n, segments, d) for n in names]
        line = SEPARATOR.join(p for p in parts if p)
        if line:
            out.append(line)
    return out


def main():
    try:
        d = json.load(sys.stdin)
        if not isinstance(d, dict):
            raise ValueError("not a JSON object")
    except ValueError as e:
        log_error(f"bad input from Claude Code: {e!r}")
        print(paint("31", "calmline: no input"))
        return
    try:
        extra, lines = load_custom(os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_segments.py"))
    except (Exception, SystemExit) as e:  # a broken my_segments.py must not blank the whole line
        log_error(f"my_segments.py failed: {e!r}")
        extra, lines = {"my_segments": lambda _: paint("31", "my_segments.py !")}, LINES + [["my_segments"]]
    print("\n".join(render(d, {**SEGMENTS, **extra}, lines)))


if __name__ == "__main__":
    main()
