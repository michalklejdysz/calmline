# calmline: rules for the agent changing it

Users ask you to change their status line in plain words. Make the change and keep the line calm, fast and unbreakable.

## Where changes go

- **User requests go to `my_segments.py`** (create it from `my_segments.example.py` if it is missing). It is gitignored so updates never conflict. It can define `SEGMENTS` (a dict merged over the built-ins, so a same-named entry replaces one) and `LINES` (the full layout, a list of lines, each a list of segment names). Import helpers with `from calmline import dim, paint, level, duration, until, LINES`.
- **Never edit `calmline.py` here**: updates replace it. To change a built-in segment, define one with the same name in `my_segments.py`; it wins. Bugs in calmline itself go to https://github.com/michalklejdysz/calmline/issues.

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

- A segment must return a string or `None`; anything else shows as `name !`.

## Check your change

Use the python from the `statusLine` command in `~/.claude/settings.json` (a bare `python3` may be a version-manager shim that fails outside a project):

```sh
<python> calmline.py < fixtures/full.json      # see it
<python> calmline.py < fixtures/minimal.json   # nothing breaks when data is missing
```

Show the user the rendered output after the change.

## When something shows `name !`, `name …` or `name ?`

- `!`: the segment raised or returned a non-string. `my_segments.py !`: the file itself failed to load. The reason is the last lines of `error.log` here.
- `…`: the segment took longer than 300 ms and was dropped.
- `?`: `LINES` names a segment that doesn't exist.
