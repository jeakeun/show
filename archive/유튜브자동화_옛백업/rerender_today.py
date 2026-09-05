"""오늘 영상을 현재 설정(애니메이션 + BGM)으로 재렌더링하는 테스트 스크립트."""
import json
from pathlib import Path

from src.tts import make_narration
from src.video import render_animated

workdir = Path(r"C:\Users\User\OneDrive\Desktop\show\output\2026-08-02\shorts")
meta = json.load(open(workdir / "meta.json", encoding="utf-8"))
scenes = meta.get("scenes") or [{"emoji": "💡", "keyword": meta["topic"][:20]}]
mp3, srt = make_narration(meta["script"], "shorts", workdir)
video = render_animated(scenes, meta["title"], mp3, srt, "shorts", workdir)
print("OK:", video)
