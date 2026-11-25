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


def main() -> int:
    mode = common.read_state("mode", "full")
    if mode == "off" or not common.engine_ready():
        return 0
    model = common.voice_model(common.read_state("voice", common.DEFAULT_VOICE))
    if not model.exists():
        return 0
    payload = payload_from_stdin()
    text = payload and speech_text.speech_for(payload, speech_text.parse_mode(mode))
    if not text:
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
