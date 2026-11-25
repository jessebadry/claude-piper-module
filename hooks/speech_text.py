import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal, assert_never

Mode = Literal["full", "short"]

SHORT_LIMIT = 400

# Single-segment slash commands like /speak are left alone: they read fine aloud.
PATH_LIKE = re.compile(
    r"(?<![\w/])(?:~|\.{1,2})/(?:[\w.\-@/]*[\w\-@/])?"
    r"|(?<![\w/])/[\w.\-@]+(?:/[\w.\-@]*[\w\-@])+/?"
    r"|(?<![\w/.])[\w\-]+(?:/[\w.\-@]*[\w\-@]){2,}"
    r"|(?<![\w/.])[\w\-]+/[\w\-]+\.\w{1,5}\b"
)

def last_segment(path: re.Match[str]) -> str:
    segment = path.group().rstrip("/").rsplit("/", 1)[-1]
    return segment if any(c.isalnum() for c in segment) else ""


STRIP_STEPS: list[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]] = [
    (re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL), ""),
    (re.compile(r"^\s*\|.*$", re.MULTILINE), ""),
    (re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE), ""),
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),
    (re.compile(r"https?://\S+"), ""),
    (PATH_LIKE, last_segment),
    (re.compile(r"^\s*(?:#{1,6}|>|[-*+]|\d+[.)])\s+", re.MULTILINE), ""),
    (re.compile(r"(?<=\w)_(?=\w)"), " "),
    (re.compile(r"\*+|`+|(?<!\w)_+|_+(?!\w)"), ""),
    (re.compile("[←-⇿☀-➿\U0001f000-\U0001faff]"), ""),
    (re.compile(r"\(\s*\)"), ""),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r" +([.,;:!?])"), r"\1"),
]


def parse_mode(raw: str) -> Mode:
    match raw.strip():
        case "short":
            return "short"
        case _:
            return "full"


def assistant_text(transcript_line: str) -> str | None:
    try:
        entry = json.loads(transcript_line)
    except json.JSONDecodeError:
        return None
    if entry.get("type") != "assistant":
        return None
    content = entry.get("message", {}).get("content", [])
    if isinstance(content, str):
        return content or None
    return "\n".join(b["text"] for b in content if b.get("type") == "text") or None


def last_assistant_text(transcript: Path) -> str | None:
    try:
        lines = transcript.read_text().splitlines()
    except OSError:
        return None
    return next((t for t in map(assistant_text, reversed(lines)) if t), None)


def last_reply(payload: dict) -> str | None:
    # Stop payloads don't always carry the reply text, so the transcript is the fallback.
    direct = payload.get("last_assistant_message")
    if isinstance(direct, str) and direct.strip():
        return direct
    path = payload.get("transcript_path")
    return last_assistant_text(Path(path)) if isinstance(path, str) else None


def spoken_lines(markdown: str) -> list[str]:
    text = markdown
    for pattern, replacement in STRIP_STEPS:
        text = pattern.sub(replacement, text)
    return [line.strip() for line in text.splitlines() if line.strip()]


def flatten(lines: list[str]) -> str:
    return " ".join(line if line[-1] in ".!?:" else line + "." for line in lines)


def shorten(text: str, limit: int) -> str:
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?:])\s+", text):
        if kept and len(" ".join([*kept, sentence])) > limit:
            break
        kept.append(sentence)
    return " ".join(kept)[:limit]


def speech_for(payload: dict, mode: Mode) -> str | None:
    reply = last_reply(payload)
    lines = spoken_lines(reply) if reply else []
    if not lines:
        return None
    match mode:
        case "full":
            return "\n".join(lines)
        case "short":
            return shorten(flatten(lines), SHORT_LIMIT)
        case _:
            assert_never(mode)


def main(argv: list[str]) -> int:
    mode = parse_mode(argv[1]) if len(argv) > 1 else "full"
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    speech = speech_for(payload, mode) if isinstance(payload, dict) else None
    if speech:
        print(speech)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
