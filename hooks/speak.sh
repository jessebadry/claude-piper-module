#!/usr/bin/env bash
D="$HOME/.local/share/claude-tts"
mode=$(cat "$HOME/.claude/tts-mode" 2>/dev/null || echo full)
[ "$mode" = off ] && exit 0

voice=$(cat "$HOME/.claude/tts-voice" 2>/dev/null || echo en_US-lessac-medium)
model="$D/voices/$voice.onnx"
[ -f "$model" ] || exit 0
rate=$(jq -r .audio.sample_rate "$model.json")

text=$("$D/venv/bin/python" "$HOME/.claude/hooks/speech_text.py" "$mode") || exit 0
[ -n "$text" ] || exit 0

"$HOME/.local/bin/claude-speak" stop
printf '%s\n' "$text" > "$D/last.txt"

setsid bash -c '
  trap "rm -f \"$1\"" EXIT
  echo $$ > "$1"
  "$2" -m "$3" --output-raw < "$4" 2>/dev/null \
    | paplay --raw --rate="$5" --format=s16le --channels=1
' _ "$D/speak.pid" "$D/venv/bin/piper" "$model" "$D/last.txt" "$rate" \
  </dev/null >/dev/null 2>&1 &
