#!/usr/bin/env python3
"""calmline: a calm two-line status line for Claude Code.

Reads the status line JSON from stdin, prints one line per entry in LINES.
Labels and separators are dimmed; colour appears only where a number needs attention.
Standard library only. Your own segments go in my_segments.py (see CLAUDE.md).
"""
import importlib.util
import json
import os
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


def state_path():
    return os.path.expanduser(os.environ.get("CALMLINE_STATE", "~/.claude/.calmline-turn.json"))


# Segments: each takes the status line input and returns a string, or None to hide itself.


def session(d):
    name = d.get("session_name")
    return name and paint("1", name)


def git(d):
    cwd = d.get("cwd")
    if not cwd:
        return None
    run = lambda *a: subprocess.run(
        ["git", "-C", cwd, *a], capture_output=True, text=True, timeout=0.25
    ).stdout.strip()
    branch = run("branch", "--show-current") or run("rev-parse", "--short", "HEAD")
    if not branch:
        return None
    dirty = paint("33", "●") if run("status", "--porcelain", "-uno") else ""
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
    """(cost, api_ms) of the previous turn: change in session totals between two prompt starts."""
    c = d.get("cost") or {}
    total, ms = c.get("total_cost_usd"), c.get("total_api_duration_ms") or 0
    try:
        with open(state_path()) as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    same = s.get("session") == d.get("session_id")
    if not same or s.get("prompt") != d.get("prompt_id"):
        last = (s["end"] - s["start"], s["end_ms"] - s["start_ms"]) if same and "start" in s else None
        s = {
            "session": d.get("session_id"),
            "prompt": d.get("prompt_id"),
            "start": s["end"] if same else total,
            "start_ms": s["end_ms"] if same else ms,
            "last": last,
        }
    s["end"], s["end_ms"] = total, ms
    with open(state_path(), "w") as f:
        json.dump(s, f)
    return s["last"]


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
    ["session", "git", "model", "context", "cache"],
    ["ponytail", "cost", "5h", "week"],
]

SEPARATOR = dim("  │  ")


class _Slow(Exception):
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
        return fn(d)
    except (_Slow, subprocess.TimeoutExpired):
        return dim(f"{name} …")
    except Exception as e:  # any bug in any segment, ours or the user's
        print(f"calmline: segment {name!r} failed: {e!r}", file=sys.stderr)
        return paint("31", f"{name} !")
    finally:
        if timed:
            signal.setitimer(signal.ITIMER_REAL, 0)


def load_custom(path):
    """Merge SEGMENTS and LINES from my_segments.py next to this file, if present."""
    if not os.path.exists(path):
        return {}, None
    sys.modules.setdefault("calmline", sys.modules[__name__])
    spec = importlib.util.spec_from_file_location("my_segments", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "SEGMENTS", {}), getattr(mod, "LINES", None)


def render(d, segments=None, lines=None):
    segments = segments or SEGMENTS
    out = []
    for names in lines or LINES:
        parts = [run_segment(n, segments[n], d) if n in segments else paint("31", f"{n} ?") for n in names]
        line = SEPARATOR.join(p for p in parts if p)
        if line:
            out.append(line)
    return out


def main():
    d = json.load(sys.stdin)
    try:
        extra, lines = load_custom(os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_segments.py"))
    except Exception as e:  # a broken my_segments.py must not blank the whole line
        print(f"calmline: my_segments.py failed: {e!r}", file=sys.stderr)
        extra, lines = {"my_segments": lambda _: paint("31", "my_segments.py !")}, LINES + [["my_segments"]]
    print("\n".join(render(d, {**SEGMENTS, **extra}, lines)))


if __name__ == "__main__":
    main()
