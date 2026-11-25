"""Synthesize a text file with Piper and play it. Runs inside the venv."""
import os
import queue
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path

import miniaudio
from piper import PiperVoice

import common

TAIL_SECONDS = 0.4


def synthesize_into(voice: PiperVoice, text: str, out: "queue.Queue[bytes | None]") -> None:
    for chunk in voice.synthesize(text):
        out.put(chunk.audio_int16_bytes)
    out.put(None)


def pcm_stream(
    chunks: "queue.Queue[bytes | None]", finished: threading.Event
) -> Generator[bytes, int, None]:
    buffered = b""
    ended = False
    frames = yield b""
    while True:
        wanted = frames * 2
        while len(buffered) < wanted and not ended:
            item = chunks.get()
            if item is None:
                ended = True
            else:
                buffered += item
        data, buffered = buffered[:wanted], buffered[wanted:]
        if not data:
            finished.set()
        frames = yield data


def play(voice: PiperVoice, text: str) -> None:
    chunks: queue.Queue[bytes | None] = queue.Queue()
    finished = threading.Event()
    threading.Thread(target=synthesize_into, args=(voice, text, chunks), daemon=True).start()

    stream = pcm_stream(chunks, finished)
    next(stream)
    device = miniaudio.PlaybackDevice(
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=voice.config.sample_rate,
    )
    device.start(stream)
    finished.wait()
    time.sleep(TAIL_SECONDS)
    device.close()


def main(model: Path, text_file: Path) -> int:
    try:
        play(PiperVoice.load(str(model)), text_file.read_text())
    finally:
        common.release_pidfile(os.getpid())
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
