# M2 전사·자막 — data/raw/*.mp4 를 한국어로 전사해 json + srt 저장
# faster-whisper 가 설치돼 있으면 실제 전사, 없으면 샘플 전사를 복사해 다음 단계를 뚫습니다.
#   실제 전사 설치:  pip install faster-whisper
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, info, load_json, save_json, warn

TAG = "M2"


def _to_srt(segments):
    def ts(sec):
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        ms = int(round((s - int(s)) * 1000))
        return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"
    lines = []
    for i, seg in enumerate(segments, 1):
        lines += [str(i), f"{ts(seg['start'])} --> {ts(seg['end'])}", seg["text"], ""]
    return "\n".join(lines)


def _transcribe_real(video, model_size="small"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    info(TAG, f"faster-whisper({model_size}) 로 전사 중: {video.name} — 몇 분 걸릴 수 있어요")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video), language="ko")
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]


def run(model_size="small"):
    raws = sorted((DATA / "raw").glob("*.mp4"))
    if not raws:
        warn(TAG, "data/raw 에 영상이 없습니다. M1을 먼저 실행하세요.")
        return False

    sample = DATA / "samples" / "sample_transcript.json"
    used_sample = False
    for video in raws:
        out_json = DATA / "transcript" / f"{video.stem}.json"
        out_srt = DATA / "transcript" / f"{video.stem}.srt"
        if out_json.exists():
            info(TAG, f"건너뜀 (이미 전사): {video.stem}")
            continue
        segments = _transcribe_real(video, model_size)
        if segments is None:
            segments = load_json(sample)
            used_sample = True
            info(TAG, f"샘플 전사 사용: {video.stem} (faster-whisper 미설치)")
        save_json(out_json, segments)
        out_srt.write_text(_to_srt(segments), encoding="utf-8")
        info(TAG, f"저장: transcript/{out_json.name}, {out_srt.name} ({len(segments)}문장)")

    if used_sample:
        warn(TAG, "실제 전사를 하려면:  pip install faster-whisper  후 다시 실행")
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    run()
