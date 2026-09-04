"""edge-tts(무료)로 내레이션 mp3와 자막(SRT)을 생성한다.

단어 단위 타임스탬프(WordBoundary)를 직접 수집해서
읽기 좋은 길이로 묶은 SRT를 만든다.
"""
import asyncio
from pathlib import Path

import edge_tts

from .config import CONFIG


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt(words: list[dict], group_chars: int) -> str:
    """words: [{'text', 'start', 'end'}] → 그룹 단위 SRT 문자열."""
    cues = []
    cur_words: list[dict] = []
    cur_len = 0
    for w in words:
        cur_words.append(w)
        cur_len += len(w["text"])
        if cur_len >= group_chars:
            cues.append(cur_words)
            cur_words, cur_len = [], 0
    if cur_words:
        cues.append(cur_words)

    lines = []
    for i, cue in enumerate(cues, 1):
        start = cue[0]["start"]
        end = cue[-1]["end"] + 0.1
        text = " ".join(w["text"] for w in cue)
        lines.append(f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text}\n")
    return "\n".join(lines)


async def _synth(text: str, voice: str, rate: str, mp3_path: Path) -> list[dict]:
    words = []
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration 단위는 100나노초
                start = chunk["offset"] / 10_000_000
                end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                words.append({"text": chunk["text"], "start": start, "end": end})
    return words


def make_narration(script: str, video_type: str, workdir: Path) -> tuple[Path, Path]:
    """대본 → (mp3 경로, srt 경로)"""
    cfg = CONFIG[video_type]
    mp3_path = workdir / "voice.mp3"
    srt_path = workdir / "subs.srt"
    words = asyncio.run(_synth(script, cfg["voice"], cfg["rate"], mp3_path))
    if not words:
        raise RuntimeError("TTS가 단어 타임스탬프를 반환하지 않았습니다.")
    srt_path.write_text(
        _build_srt(words, cfg["subtitle_group_chars"]), encoding="utf-8"
    )
    return mp3_path, srt_path
