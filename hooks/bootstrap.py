"""SessionStart hook and `claude-speak setup`: build the venv and fetch the voice.

Without --run it starts itself detached and returns at once, so a first-run
install (a few hundred MB) never blocks session start.
"""
import fcntl
import json
import subprocess
import sys
from pathlib import Path

import common

LOG = common.DATA / "bootstrap.log"
LOCK = common.DATA / "bootstrap.lock"
SHIM = Path.home() / ".local" / "bin" / "claude-speak"
CLI = common.HOOKS_DIR.parent / "bin" / "claude-speak"


def notify(message: str) -> None:
    print(json.dumps({"systemMessage": f"piper-hook: {message}"}))


def refresh_shim() -> None:
    """Keep an existing terminal shim pointing at the current plugin version."""
    if SHIM.is_symlink() and SHIM.resolve() != CLI.resolve():
        SHIM.unlink()
        SHIM.symlink_to(CLI.resolve())


def run(*cmd: str) -> bool:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd).returncode == 0


def install_engine() -> bool:
    venv_python = str(common.VENV_PYTHON)
    return (
        (common.VENV_PYTHON.exists() or run(sys.executable, "-m", "venv", str(common.DATA / "venv")))
        and run(venv_python, "-m", "pip", "install", "--quiet", *common.REQUIREMENTS)
    )


def install_voice(voice: str) -> bool:
    return common.voice_model(voice).exists() or run(
        str(common.VENV_PYTHON), "-m", "piper.download_voices",
        "--data-dir", str(common.VOICES), voice,
    )


def build() -> int:
    with LOCK.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        voice = common.read_state("voice", common.DEFAULT_VOICE)
        if not (install_engine() and install_voice(voice)):
            print("setup failed", flush=True)
            return 1
        common.READY_MARKER.write_text(" ".join(common.REQUIREMENTS) + "\n")
        print("setup done", flush=True)
        return 0


def start_detached() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [sys.executable, __file__, "--run"],
        stdin=subprocess.DEVNULL,
        stdout=LOG.open("w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    notify(f"installing the voice engine in the background, speech starts when it finishes (log: {LOG})")


def main(argv: list[str]) -> int:
    if common.python_too_old():
        notify(f"needs Python {common.MIN_PYTHON[0]}.{common.MIN_PYTHON[1]}+, found {sys.version.split()[0]}")
        return 0
    common.DATA.mkdir(parents=True, exist_ok=True)
    refresh_shim()
    if "--run" in argv:
        return build()
    if not common.engine_ready():
        start_detached()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
