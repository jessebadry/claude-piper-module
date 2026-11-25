# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code plugin (`piper-hook`) that speaks replies aloud with Piper TTS. The repo is its own marketplace (`.claude-plugin/marketplace.json`, plugin source `./`). Only prerequisite for users is Python 3.11+. `README.md` has the user-facing install, update and migration steps; don't duplicate them here.

GitHub repo is private: `git@github.com:jessebadry/claude-piper-module.git`. The repo name differs from the plugin name on purpose. The plugin and marketplace name is `piper-hook`, which sets the install id (`piper-hook@piper-hook`) and the slash command prefix (`/piper-hook:speak`).

## Architecture

Two Python environments are involved, and the split drives the file layout:

- **System Python, stdlib only** (whatever `python3` the hook command resolves): `hooks/speak.py` (Stop hook), `hooks/bootstrap.py` (SessionStart hook and `claude-speak setup`), `hooks/common.py`, `hooks/speech_text.py` (markdown to speakable text), `bin/claude-speak`. These must never import `piper` or `miniaudio`.
- **The venv** at `~/.local/share/claude-tts/venv` (has `piper-tts` and `miniaudio`): only `hooks/player.py` runs here. `speak.py` launches it with the venv's python as a detached process group (`start_new_session=True`) and records the pid in `speak.pid`. Replacing or stopping playback is `os.killpg` on that pid (`common.stop_playback`).

Flow: `Stop` payload on stdin → `speak.py` reads state, cleans the reply with `speech_text.speech_for`, writes `last.txt`, spawns `player.py` → player streams Piper chunks through a queue into a `miniaudio` playback device.

`bootstrap.py` runs on every `SessionStart`. If the engine isn't ready it re-launches itself detached with `--run` (so session start never blocks on a pip install), under a non-blocking `flock`. Readiness is the marker file `ready`, whose contents must equal `common.REQUIREMENTS`. Changing `REQUIREMENTS` re-triggers the install for everyone on the next session. It also re-points an existing `~/.local/bin/claude-speak` symlink at the current plugin version (the plugin cache path changes on update).

## Constraints that aren't obvious

- **State lives at a fixed path** (`$XDG_DATA_HOME/claude-tts`, default `~/.local/share/claude-tts`), not `${CLAUDE_PLUGIN_DATA}`. Plugin env vars are not set in the shell Claude's Bash tool uses, and `claude-speak` has to find the same state as the hook. Mode, voice, venv, voices, pidfile and logs all go there. Never write state under the plugin root: it changes on every update.
- `bin/` is on PATH only for Claude's Bash tool, not the user's terminal. `claude-speak shim` is the opt-in terminal link.
- Plugin commands are namespaced. Don't promise `/speak`.
- Python floor is 3.11 because of `miniaudio` (and `typing.assert_never` in `speech_text.py`). Don't lower it without checking both.
- Never call bare `piper`. On some distros `/usr/bin/piper` is a mouse-configuration app. Use the venv's python and `piper.download_voices`.
- POSIX only (`fcntl`, `killpg`, `start_new_session`). macOS is untested, Windows unsupported.
- `hooks/hooks.json` is the hooks file for the plugin and uses `${CLAUDE_PLUGIN_ROOT}`. It is not the same thing as a user's `settings.json`. If a user also has a manual `Stop` hook, replies speak twice.

## Commands

```bash
claude plugin validate .        # expect pass; LICENSE and icon warnings only matter for the public directory
python3 -m py_compile hooks/*.py bin/claude-speak    # then delete the __pycache__ dirs (gitignored anyway)
printf '{"last_assistant_message":"Edited `~/a/b.json` and **fixed** it."}' | python3 hooks/speech_text.py full   # cleaner test
```

There is no test suite. To test the real install flow without touching your own setup, use a throwaway `HOME` and a copy of the repo, then run the hooks by hand:

```bash
export HOME=$SCRATCH/home; unset XDG_DATA_HOME
claude plugin marketplace add $SCRATCH/src && claude plugin install piper-hook@piper-hook
python3 $SCRATCH/src/hooks/bootstrap.py </dev/null     # starts the background install
echo '{"last_assistant_message":"Hello."}' | python3 $SCRATCH/src/hooks/speak.py
```

To test install from GitHub without touching `~/.claude`, set `CLAUDE_CONFIG_DIR` to a throwaway dir instead (the install alone doesn't run hooks, so the real data dir stays untouched). Audio still plays through the real sound server, so confirm by ear.

## Releasing

Users only get changes when `version` in `.claude-plugin/plugin.json` changes. Bump it with every release, push, then users run:

```bash
claude plugin marketplace update piper-hook && claude plugin update piper-hook@piper-hook   # then restart Claude Code
```

The marketplace entry has no `version`. The one in `plugin.json` is the source of truth.

## Working in this repo

- Skills to load for this repo:
  - `/jesse-mode` (`anthropic-skills:jesse-mode`): before writing or changing any Python or shell.
  - `/caveman-commit`: for every commit. It proposes the message and waits for "commit". No AI attribution trailers. The scope used so far is `piper-plugin`; confirm the type with the user.
  - `/codebase-design`: for design-heavy work, such as changing module boundaries or the hook/player split. There has been very little of this so far.
- Pushes to `origin` may prompt for approval. Use plain `git` over SSH. There is no `gh` CLI, and the GitHub MCP is broken (bad tokens), so don't use it for repo work.
- The maintainer's own machine runs this plugin for real (installed from GitHub, speech state in `~/.local/share/claude-tts/`). Don't edit `~/.claude/settings.json` or delete anything in `~/.local/share/claude-tts/` without asking.
- Prose for the README and docs goes through the `unslop` skill.
