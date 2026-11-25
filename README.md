# piper-hook

Speaks Claude Code's replies aloud with [Piper](https://pypi.org/project/piper-tts/) TTS. A `Stop` hook runs when a turn ends, strips the reply down to speakable text, and plays it.

The only prerequisite is Python 3.11 or newer. No `jq`, `paplay` or `bash` needed. Tested on Linux. macOS should work but is untested, and Windows is not supported.

## Install

```bash
claude plugin install piper-hook --marketplace jessebadry/claude-piper-module
```

Start a new Claude Code session. The first session builds a Python venv with `piper-tts` and `miniaudio` and downloads the default voice, in the background (a few hundred MB, a minute or two). Replies start speaking once it finishes. Progress is in `~/.local/share/claude-tts/bootstrap.log`.

The repo is private, so git needs credentials that work without a prompt, for example an SSH key loaded in `ssh-agent`.

On Debian and Ubuntu, `python3 -m venv` needs the `python3-venv` package.

## Update

```bash
claude plugin marketplace update piper-hook && claude plugin update piper-hook@piper-hook
```

Restart Claude Code to apply it. Updates only arrive when `version` in `.claude-plugin/plugin.json` changes, so bump it on every release. The venv and voices are kept across updates.

## Use

```
claude-speak full | short | off | stop | status | voice [name] | setup | shim
```

- `full` speaks the whole reply. `short` speaks whole sentences up to about 400 characters. `off` disables speech and stops anything playing.
- `voice` with no name lists installed voices. `voice <name>` downloads the model if missing, then switches. Names look like `en_US-ryan-high`. Samples: <https://rhasspy.github.io/piper-samples/>.
- Inside Claude Code, `/piper-hook:speak short` and the rest do the same thing.
- `claude-speak` is on PATH for Claude's own shell. To use it from your terminal, run the plugin's copy once with `claude-speak shim` (Claude can do this for you), which links it into `~/.local/bin`. Plugin updates re-point the link.
- `setup` re-runs the install step by hand if the first one failed.

## Where things live

| Path | What |
|---|---|
| `~/.local/share/claude-tts/` (or `$XDG_DATA_HOME/claude-tts/`) | venv, voices, `mode`, `voice`, `last.txt`, `speak.pid`, `bootstrap.log` |
| `hooks/hooks.json` | `SessionStart` (bootstrap) and `Stop` (speak) registration |
| `hooks/speak.py` | The `Stop` hook. Cleans the reply, starts the player. |
| `hooks/player.py` | Runs inside the venv. Synthesizes with Piper and plays through `miniaudio`. |
| `hooks/bootstrap.py` | Builds the venv and fetches the voice, detached so it never blocks session start. |
| `hooks/speech_text.py` | Turns a markdown reply into speakable text. Stdlib only. |
| `bin/claude-speak` | CLI for mode, voice and stopping playback. |
| `commands/speak.md` | `/piper-hook:speak <args>` wrapper around the CLI. |

The data directory is a fixed path because Claude's shell doesn't get `CLAUDE_PLUGIN_DATA`, and the CLI has to find the same state as the hook. Uninstalling the plugin leaves it in place. Delete it by hand to reclaim the space.

## Moving from the manual install

Earlier versions were copied into `~/.claude/hooks/` and registered in `~/.claude/settings.json`. If both that `Stop` entry and the plugin are active, every reply is spoken twice. After installing the plugin:

1. Remove the `speak.sh` entry from `hooks.Stop` in `~/.claude/settings.json`. Leave other hooks alone.
2. Delete `~/.claude/hooks/speak.sh`, `~/.claude/hooks/speech_text.py`, `~/.claude/commands/speak.md` and `~/.local/bin/claude-speak`.
3. Copy your old settings: `~/.claude/tts-mode` to `~/.local/share/claude-tts/mode`, and `~/.claude/tts-voice` to `~/.local/share/claude-tts/voice`.

The old venv and voices in `~/.local/share/claude-tts/` are reused.

## What gets cleaned

Code blocks, tables, rules, URLs (link text is kept), list and heading markers, emphasis marks, emoji and arrows are removed. `snake_case` is spoken as "snake case". Paths are spoken as their last segment, so `~/.claude/settings.json` becomes "settings.json". To drop paths entirely, change `last_segment` to `""` in `STRIP_STEPS`.

Only the final message of a turn is spoken, because `Stop` fires once when the turn ends.

## Quick test

```bash
printf '{"last_assistant_message":"Edited `~/.claude/settings.json` and **fixed** the bug."}' \
  | python3 hooks/speech_text.py full
```

## Known gaps

- If a `Stop` payload has no `last_assistant_message` and the transcript isn't flushed yet, the fallback could read the previous reply. It hasn't happened in practice.
- Multi-speaker voices always use speaker 0.
- Plugin commands are namespaced, so the slash command is `/piper-hook:speak`, not `/speak`.
- No test suite yet.
