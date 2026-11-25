# piper-hook

Speaks Claude Code's replies aloud with [Piper](https://pypi.org/project/piper-tts/) TTS. A `Stop` hook runs when a turn ends, strips the reply down to speakable text, and plays it through `paplay`.

## Layout

| File | Installs to | Purpose |
|---|---|---|
| `hooks/speak.sh` | `~/.claude/hooks/speak.sh` | The `Stop` hook. Reads mode and voice, cleans the text, starts playback. |
| `hooks/speech_text.py` | `~/.claude/hooks/speech_text.py` | Turns a markdown reply into speakable text. Stdlib only. |
| `bin/claude-speak` | `~/.local/bin/claude-speak` | CLI for mode, voice and stopping playback. |
| `commands/speak.md` | `~/.claude/commands/speak.md` | `/speak <args>` wrapper around the CLI. |

State lives in `~/.claude/tts-mode` and `~/.claude/tts-voice`. Voice models and the Piper venv live in `~/.local/share/claude-tts/`. Neither is in this repo.

## Requirements

`jq`, `paplay`, `setsid`, and Python 3.11+ (the cleaner uses `typing.assert_never`).

The engine is the pip package `piper-tts`. The `piper` on your `PATH` may be something else (on some distros it is a mouse-configuration app), so the scripts call the venv's binary directly.

## Install

```bash
python3 -m venv ~/.local/share/claude-tts/venv
~/.local/share/claude-tts/venv/bin/pip install piper-tts

mkdir -p ~/.claude/hooks ~/.claude/commands ~/.local/bin
ln -sf "$PWD/hooks/speak.sh"        ~/.claude/hooks/speak.sh
ln -sf "$PWD/hooks/speech_text.py"  ~/.claude/hooks/speech_text.py
ln -sf "$PWD/bin/claude-speak"      ~/.local/bin/claude-speak
ln -sf "$PWD/commands/speak.md"     ~/.claude/commands/speak.md

claude-speak voice en_US-lessac-medium   # downloads the model, then selects it
```

Register the hook in `~/.claude/settings.json`, alongside any hooks already there:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "bash '$HOME/.claude/hooks/speak.sh'", "timeout": 15 }
        ]
      }
    ]
  }
}
```

Use your real home path if your Claude Code version doesn't expand `$HOME` in hook commands.

## Usage

```
claude-speak full | short | off | stop | status | voice [name]
```

- `full` speaks the whole reply. `short` speaks whole sentences up to about 400 characters. `off` disables speech and stops anything playing.
- `voice` with no name lists installed voices. `voice <name>` downloads the model if missing, then switches. Names look like `en_US-ryan-high`. Samples: <https://rhasspy.github.io/piper-samples/>.
- Inside Claude Code, `/speak short` and the rest do the same thing.

## What gets cleaned

Code blocks, tables, rules, URLs (link text is kept), list and heading markers, emphasis marks, emoji and arrows are removed. `snake_case` is spoken as "snake case". Paths are spoken as their last segment, so `~/.claude/settings.json` becomes "settings.json". To drop paths entirely, change `last_segment` to `""` in `STRIP_STEPS`.

Only the final message of a turn is spoken, because `Stop` fires once when the turn ends.

## Quick test

```bash
printf '{"last_assistant_message":"Edited `~/.claude/settings.json` and **fixed** the bug."}' \
  | ~/.local/share/claude-tts/venv/bin/python hooks/speech_text.py full
```

## Known gaps

- If a `Stop` payload has no `last_assistant_message` and the transcript isn't flushed yet, the fallback could read the previous reply. It hasn't happened in practice.
- Multi-speaker voices always use speaker 0.
- No test suite yet.
