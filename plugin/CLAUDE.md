# calmline: rules for the agent changing it

Users ask you to change their status line in plain words. Make the change and keep the line calm, fast and unbreakable.

## Where changes go

- **User requests go to `my_segments.py`** (create it from `my_segments.example.py` if it is missing). It is gitignored so updates never conflict. It can define `SEGMENTS` (a dict merged over the built-ins, so a same-named entry replaces one) and `LINES` (the full layout, a list of lines, each a list of segment names). Import helpers with `from calmline import dim, paint, level, duration, until, LINES`.
- Edit `calmline.py` only when changing calmline itself (a bug fix or a built-in segment for everyone), not for one user's taste.

## A segment

```python
def venv(d):                      # d = the status line JSON Claude Code sends on stdin
    path = os.environ.get("VIRTUAL_ENV")
    return path and dim("venv ") + os.path.basename(path)   # None or "" hides the segment
```

- Missing data → return `None`. Never raise on absent keys; read with `.get()`.
- **Style:** label `dim()`, value plain. Colour (`level()` or `paint("31"|"32"|"33", …)`) only for a number the user acts on, by threshold. No emoji walls, no new colours without a reason.
- **Speed:** the line re-renders often and each segment gets 300 ms. No network calls. A subprocess needs `timeout=` under 0.25 s. Read small files only.
- Standard library only. No `pip install`.

## Input fields

Claude Code sends: `session_id`, `prompt_id`, `session_name`, `cwd`, `workspace.{current_dir,project_dir,repo}`, `model.{id,display_name}`, `effort.level`, `fast_mode`, `thinking.enabled`, `context_window.{used_percentage,context_window_size,total_input_tokens,current_usage}`, `prompt_cache.{hit_ratio,warm,ttl,expires_at}`, `cost.{total_cost_usd,total_duration_ms,total_api_duration_ms,total_lines_added,total_lines_removed}`, `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`, `output_style`, `version`, `transcript_path`. Any of them can be missing; fields come and go between Claude Code versions.

## Check your change

```sh
python3 calmline.py < fixtures/full.json      # see it
python3 calmline.py < fixtures/minimal.json   # nothing breaks when data is missing
python3 -m unittest discover tests            # must stay green
```

Show the user the rendered output after the change. If you changed `calmline.py` itself, also run `python3 demo/render.py` so the README demo matches the code.
