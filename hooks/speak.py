"""Stop hook: speak the last reply. Runs on the system Python, stdlib only."""
import json
import subprocess
import sys

import common
import speech_text

PLAYER = common.HOOKS_DIR / "player.py"


def payload_from_stdin() -> dict | None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def say(reply: str, mode: speech_text.Mode) -> str:
    """Speak a raw markdown reply. Returns what happened, for the CLI to print."""
    if not common.engine_ready():
        return "engine not ready (try `claude-speak setup`)"
    model = common.voice_model(common.read_state("voice", common.DEFAULT_VOICE))
    if not model.exists():
        return f"voice model missing: {model.stem}"
    text = speech_text.speech_for({"last_assistant_message": reply}, mode)
    if not text:
        return "nothing speakable in that reply"
    if common.mic_in_use():
        return "microphone in use, not speaking"

    common.stop_playback()
    common.LAST_TEXT.write_text(text + "\n")
    player = subprocess.Popen(
        [str(common.VENV_PYTHON), str(PLAYER), str(model), str(common.LAST_TEXT)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    common.PIDFILE.write_text(str(player.pid))
    return f"speaking ({mode})"


def main() -> int:
    if common.consume_skip_next():
        return 0
    payload = payload_from_stdin()
    reply = payload and speech_text.last_reply(payload)
    if not reply:
        return 0
    common.save_reply(reply)
    mode = common.read_state("mode", "full")
    if mode != "off":
        say(reply, speech_text.parse_mode(mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
