<p align="center"><img src="demo/calmline.svg" alt="calmline: a calm two-line status line for Claude Code" width="820"></p>

<h1 align="center">calmline</h1>

<p align="center">A quiet status line for Claude Code.<br>Grey until something needs you. No config file: ask your Claude to change it.</p>

---

**What you see**

- **Top line:** session, git branch (● = uncommitted changes), model and effort (⚡ fast mode), context used, cache hits
- **Bottom line:** session cost, cost and time of your last turn, 5-hour and weekly limits with time to reset

Green, yellow, red only on the numbers you act on. Everything else stays grey.

## Install

```sh
git clone https://github.com/michalklejdysz/calmline ~/.claude/calmline
```

Add to `~/.claude/settings.json`:

```json
"statusLine": { "type": "command", "command": "python3 ~/.claude/calmline/calmline.py" }
```

Python 3.8+, standard library only. Or skip both steps and tell Claude: *"install calmline as my status line"*.

## Make it yours

There are no options to learn. Open Claude Code in the calmline folder and ask:

> Add a segment with the active Python venv.

> Put the git branch first and drop the cache segment.

> Turn the context number red at 50% instead of 70%.

> Show the Node version when there is a package.json.

Your changes go to `my_segments.py`, which is gitignored, so `git pull` never conflicts. [CLAUDE.md](CLAUDE.md) gives your Claude the rules: what data exists, how to test, what keeps the line fast.

## Safe by default

- A segment slower than 300 ms is dropped, so the line never lags
- A broken segment shows `name !` and the rest still renders
- No network and nothing leaves your machine; one small state file holds the last-turn numbers
