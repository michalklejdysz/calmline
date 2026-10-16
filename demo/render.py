"""Render demo/calmline.svg: an animated terminal showing real calmline output in three states.

Run: python3 demo/render.py  (re-run after changing calmline.py so the demo never lies)
"""
import copy
import html
import json
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "plugin"))
import calmline  # noqa: E402

PALETTE = {"31": "#ff6b6b", "32": "#5fd38d", "33": "#f2c94c", "36": "#56c8d8"}
FG, DIMMED, BG, CHROME = "#e6e6e6", "#7a7f87", "#14161a", "#22252b"
CHAR_W, LINE_H, PAD = 8.9, 22, 28
FRAME_S = 3.2

with open(os.path.join(ROOT, "plugin", "fixtures", "full.json")) as f:
    BASE = json.load(f)


def state(session, branch, dirty, ctx, five, week, total, prev_total, turn_s, fast=False, five_reset=98, lines=None, extra=None):
    d = copy.deepcopy(BASE)
    now = time.time()
    d.update(session_name=session, fast_mode=fast)
    d["context_window"]["used_percentage"] = ctx
    d["rate_limits"]["five_hour"].update(used_percentage=five, resets_at=now + five_reset * 60 + 30)
    d["rate_limits"]["seven_day"].update(used_percentage=week, resets_at=now + (4 * 1440 + 23 * 60) * 60 + 30)
    fake_git = lambda _: calmline.paint("36", f"⎇ {branch}") + (calmline.paint("33", " ●") if dirty else "")
    segments = {**calmline.SEGMENTS, **(extra or {}), "dir": lambda _: calmline.paint("34", "~/code/shop"), "git": fake_git, "ponytail": lambda _: None}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CALMLINE_STATE"] = tmp
        d["cost"] = {"total_cost_usd": prev_total, "total_api_duration_ms": 300000}
        calmline.render(d, segments, lines)
        d["cost"] = {"total_cost_usd": total, "total_api_duration_ms": 300000 + turn_s * 1000}
        calmline.render(d, segments, lines)
        d["prompt_id"] = "next"
        return calmline.render(d, segments, lines)


FRAMES = [
    ("all calm", state("Fix login redirect", "main", False, 12, 18, 41, 0.42, 0.31, 9)),
    ("colour shows up only when it matters", state("Fix login redirect", "feat/login", True, 46, 57, 52, 1.84, 1.67, 26)),
    ("red: time to /clear, limit resets soon", state("Fix login redirect", "feat/login", True, 78, 86, 63, 3.12, 2.71, 104, True, 41)),
]

TOKEN = re.compile(r"\033\[([0-9;]*)m")


def spans(line):
    """ANSI line -> SVG tspans, tracking bold/dim/colour like a terminal does."""
    out, style, pos = [], {}, 0
    for m in list(TOKEN.finditer(line)) + [None]:
        text = line[pos : m.start() if m else len(line)]
        if text:
            fill = PALETTE.get(style.get("color"), DIMMED if style.get("dim") else FG)
            weight = ' font-weight="700"' if style.get("bold") else ""
            out.append(f'<tspan fill="{fill}"{weight}>{html.escape(text)}</tspan>')
        if not m:
            break
        for code in (m.group(1) or "0").split(";"):
            if code == "0":
                style = {}
            elif code == "1":
                style["bold"] = True
            elif code == "2":
                style["dim"] = True
            else:
                style["color"] = code
        pos = m.end()
    return "".join(out)


def visible_len(line):
    return len(TOKEN.sub("", line))


def svg(frames, label, cols):
    """One frame renders still; several cross-fade in a loop."""
    width = int(cols * CHAR_W + PAD * 2)
    rows_n = max(len(lines) for _, lines in frames)
    height = 150 + (rows_n - 1) * LINE_H + 28
    css = ["text{font-family:'SF Mono',SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;font-size:14px;white-space:pre}"]
    if len(frames) > 1:
        total, share, fade = FRAME_S * len(frames), 100 / len(frames), 4  # fade: percent of the loop spent cross-fading
        css += [
            f".f{{opacity:0;animation:show {total:.1f}s infinite}}",
            f"@keyframes show{{0%{{opacity:0}}{fade}%{{opacity:1}}{share - fade:.2f}%{{opacity:1}}{share:.2f}%{{opacity:0}}100%{{opacity:0}}}}",
            "@media (prefers-reduced-motion:reduce){.f{animation:none}.f0{opacity:1}}",
        ] + [f".f{i}{{animation-delay:{i * FRAME_S:.1f}s}}" for i in range(len(frames))]
    body = []
    for i, (caption, lines) in enumerate(frames):
        rows = [f'<text x="{PAD}" y="62" fill="{DIMMED}" font-style="italic">{html.escape(caption)}</text>']
        rows.append(f'<text x="{PAD}" y="104"><tspan fill="{FG}">❯ </tspan><tspan fill="{DIMMED}">█</tspan></text>')
        for j, line in enumerate(lines):
            rows.append(f'<text x="{PAD}" y="{150 + j * LINE_H}">{spans(line)}</text>')
        body.append(f'<g class="f f{i}">{"".join(rows)}</g>')
    rule = lambda y: f'<line x1="{PAD - 8}" x2="{width - PAD + 8}" y1="{y}" y2="{y}" stroke="#2f333a"/>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(label)}">
<style>{"".join(css)}</style>
<rect width="{width}" height="{height}" rx="12" fill="{BG}"/>
<rect width="{width}" height="30" rx="12" fill="{CHROME}"/><rect y="18" width="{width}" height="12" fill="{CHROME}"/>
<circle cx="20" cy="15" r="5.5" fill="#ff5f57"/><circle cx="38" cy="15" r="5.5" fill="#febc2e"/><circle cx="56" cy="15" r="5.5" fill="#28c840"/>
{rule(82)}{rule(120)}
{"".join(body)}
</svg>
"""


def red_at_50(d):
    used = (d.get("context_window") or {}).get("used_percentage")
    return None if used is None else calmline.dim("ctx ") + calmline.level(used, 40, 50)


WARM = dict(session="Fix login redirect", branch="feat/login", dirty=True, ctx=46, five=57, week=52, total=1.84, prev_total=1.67, turn_s=26)

# Each layout is what Opus 5.5 wrote into my_segments.py from the one prompt in the caption.
GALLERY = {
    "minimal": ("“one line with only the 5-hour and weekly usage”", state(**WARM, lines=[["5h", "week"]])),
    "focus": (
        "“git branch first, drop session name and cache, context red at 50%”",
        state(**{**WARM, "ctx": 52}, lines=[["git", "model", "context"], calmline.LINES[1]], extra={"context": red_at_50}),
    ),
}

if __name__ == "__main__":
    cols = max(visible_len(l) for _, lines in [*FRAMES, *GALLERY.values()] for l in lines)
    outputs = {"calmline": svg(FRAMES, "calmline status line, shown calm, warm and red", cols)}
    outputs.update({name: svg([frame], f"calmline {name} layout", cols) for name, frame in GALLERY.items()})
    for name, content in outputs.items():
        path = os.path.join(ROOT, "demo", f"{name}.svg")
        with open(path, "w") as f:
            f.write(content)
        print(path)
