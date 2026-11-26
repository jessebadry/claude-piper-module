import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_VOICE = "en_US-lessac-medium"
REQUIREMENTS = ("piper-tts", "miniaudio")
MIN_PYTHON = (3, 11)
SKIP_NEXT_TTL_SECONDS = 120

HOOKS_DIR = Path(__file__).resolve().parent
DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "claude-tts"
VENV_PYTHON = DATA / "venv" / "bin" / "python"
VOICES = DATA / "voices"
PIDFILE = DATA / "speak.pid"
LAST_TEXT = DATA / "last.txt"
LAST_REPLY = DATA / "last_reply.md"
SKIP_NEXT = DATA / "skip_next"
READY_MARKER = DATA / "ready"


def read_state(name: str, default: str) -> str:
    try:
        return (DATA / name).read_text().strip() or default
    except OSError:
        return default


def write_state(name: str, value: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(value + "\n")


def voice_model(voice: str) -> Path:
    return VOICES / f"{voice}.onnx"


def engine_ready() -> bool:
    try:
        return READY_MARKER.read_text().split() == list(REQUIREMENTS) and VENV_PYTHON.exists()
    except OSError:
        return False


def stop_playback() -> None:
    try:
        pid = int(PIDFILE.read_text())
    except (OSError, ValueError):
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    PIDFILE.unlink(missing_ok=True)


def release_pidfile(pid: int) -> None:
    try:
        if PIDFILE.read_text().strip() == str(pid):
            PIDFILE.unlink(missing_ok=True)
    except OSError:
        pass


def python_too_old() -> bool:
    return sys.version_info < MIN_PYTHON


def pactl_json(kind: str) -> list[dict]:
    try:
        out = subprocess.run(
            ["pactl", "--format=json", "list", kind],
            capture_output=True, text=True, timeout=2, check=True,
        ).stdout
        return json.loads(out)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []


def mic_in_use() -> bool:
    """True when an app is actively recording from a real input. Monitors (screen/audio capture) don't count."""
    outputs = [o for o in pactl_json("source-outputs") if not o.get("corked")]
    if not outputs:
        return False
    monitors = {s["index"] for s in pactl_json("sources") if s["name"].endswith(".monitor")}
    return any(o.get("source") not in monitors for o in outputs)


def save_reply(reply: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    LAST_REPLY.write_text(reply)


def skip_next_reply() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    SKIP_NEXT.touch()


def consume_skip_next() -> bool:
    """The turn that runs a replay ends with its own Stop hook; that reply shouldn't be spoken or saved."""
    try:
        fresh = time.time() - SKIP_NEXT.stat().st_mtime < SKIP_NEXT_TTL_SECONDS
    except OSError:
        return False
    SKIP_NEXT.unlink(missing_ok=True)
    return fresh
