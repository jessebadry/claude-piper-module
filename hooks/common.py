import os
import signal
import sys
from pathlib import Path

DEFAULT_VOICE = "en_US-lessac-medium"
REQUIREMENTS = ("piper-tts", "miniaudio")
MIN_PYTHON = (3, 11)

HOOKS_DIR = Path(__file__).resolve().parent
DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "claude-tts"
VENV_PYTHON = DATA / "venv" / "bin" / "python"
VOICES = DATA / "voices"
PIDFILE = DATA / "speak.pid"
LAST_TEXT = DATA / "last.txt"
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
