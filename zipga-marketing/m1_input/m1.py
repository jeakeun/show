# M1 입력·정규화 — inbox/ 의 원본 영상을 H.264 1080p 30fps 규격으로 통일해 data/raw/ 에 저장
# inbox 가 비어 있으면 ffmpeg 로 60초 샘플 영상을 만들어 파이프라인을 관통 테스트합니다.
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, INBOX, append_csv, has_cmd, info, read_csv, run_cmd, warn

TAG = "M1"
INDEX = DATA / "index.csv"
INDEX_FIELDS = ["source", "raw_file", "duration_sec", "resolution", "mean_volume_db", "note"]
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
NAME_RULE = re.compile(r"^\d{8}_[0-9a-zA-Z가-힣_-]+$")


def _slugify(stem):
    s = re.sub(r"[^0-9a-zA-Z가-힣_-]+", "_", stem).strip("_")
    return s or "untitled"


def _probe(path):
    """길이·해상도·평균 볼륨을 알아냅니다. 실패하면 빈 값."""
    out = run_cmd([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "csv=p=0", str(path),
    ])
    dur, res = "", ""
    if out:
        lines = [l for l in out.strip().splitlines() if l.strip()]
        for l in lines:
            parts = l.strip().strip(",").split(",")
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                res = f"{parts[0]}x{parts[1]}"
            elif len(parts) == 1:
                try:
                    dur = f"{float(parts[0]):.1f}"
                except ValueError:
                    pass
    vol = ""
    vout = run_cmd(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    # volumedetect 는 stderr 로 나가므로 run_cmd 로는 못 읽는 경우가 많음 — 스켈레톤에서는 생략 가능
    return dur, res, vol


def _make_sample():
    """관통 테스트용 60초 샘플 영상 생성 (보라 화면 + 440Hz 톤)."""
    today = datetime.date.today().strftime("%Y%m%d")
    dst = INBOX / f"{today}_샘플영상.mp4"
    if dst.exists():
        return dst
    info(TAG, "inbox 가 비어 있어 60초 샘플 영상을 생성합니다 (관통 테스트용)")
    ok = run_cmd([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x4A3AA7:s=1920x1080:d=60:r=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=60",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(dst),
    ])
    return dst if dst.exists() else None


def run():
    if not has_cmd("ffmpeg"):
        warn(TAG, "ffmpeg 가 없습니다. https://ffmpeg.org 또는 `winget install ffmpeg` 로 설치하세요.")
        return False

    done = {r["source"] for r in read_csv(INDEX)}
    videos = [p for p in INBOX.iterdir() if p.suffix.lower() in VIDEO_EXT] if INBOX.exists() else []
    if not videos:
        sample = _make_sample()
        videos = [sample] if sample else []
    if not videos:
        warn(TAG, "처리할 영상이 없습니다. 촬영한 원본을 inbox/ 폴더에 넣으세요.")
        return False

    processed = 0
    for src in videos:
        if src.name in done:
            info(TAG, f"건너뜀 (이미 처리): {src.name}")
            continue
        stem = src.stem
        if not NAME_RULE.match(stem):
            today = datetime.date.today().strftime("%Y%m%d")
            new_stem = f"{today}_{_slugify(stem)}"
            warn(TAG, f"파일명 규칙(YYYYMMDD_주제슬러그)에 안 맞아 자동 변경: {stem} → {new_stem}")
            stem = new_stem
        dst = DATA / "raw" / f"{stem}.mp4"
        info(TAG, f"변환 중: {src.name} → data/raw/{dst.name}")
        ok = run_cmd([
            "ffmpeg", "-y", "-i", str(src),
            "-vf", "scale=-2:1080,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(dst),
        ])
        if not dst.exists():
            warn(TAG, f"변환 실패: {src.name}")
            continue
        dur, res, vol = _probe(dst)
        append_csv(INDEX, {
            "source": src.name, "raw_file": dst.name,
            "duration_sec": dur, "resolution": res,
            "mean_volume_db": vol, "note": "",
        }, INDEX_FIELDS)
        processed += 1

    info(TAG, f"완료 — 신규 {processed}개, index.csv 총 {len(read_csv(INDEX))}줄")
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    run()
