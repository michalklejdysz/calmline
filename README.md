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

Or skip both steps and tell Claude: *"install calmline as my status line"*.

**You need:** Python 3.8+ (macOS ships it as `/usr/bin/python3`), standard library only. Git is optional: without it the branch is just hidden. Any terminal with colour and UTF-8 works. In iTerm2, Ghostty, kitty, WezTerm or Windows Terminal, use a font with `⎇ ↻ ⚡` (SF Mono, JetBrains Mono, any Nerd Font). The 5h and weekly limits show only on a Claude subscription (Pro/Max). API-key users don't get these fields from Claude Code.

**Tested on:** Claude Code 2.1.301 with Opus 5.5, macOS, iTerm2. Tests pass on Python 3.8, 3.9 and 3.14. On Windows it runs, but without the 300 ms segment cut-off: `signal.setitimer` is Unix only.

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
