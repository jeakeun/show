# M3 클립 생성 — 전사의 문장 경계에 맞춰 30~50초 구간을 골라 9:16 세로 클립으로 잘라냄
# 자막 번인은 srt 가 있으면 시도하고, 실패하면 자막 없이 잘라냅니다 (스켈레톤 단계 허용).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, has_cmd, info, load_config, load_json, run_cmd, warn, write_csv

TAG = "M3"
MANIFEST = DATA / "clips" / "manifest.csv"
MANIFEST_FIELDS = ["clip_id", "source", "start", "end", "first_sentence", "file", "status"]


def _pick_segments(transcript, min_sec, max_sec, max_n):
    """문장 경계를 지키며 30~50초 구간 후보를 뽑습니다."""
    picks, i = [], 0
    while i < len(transcript) and len(picks) < max_n:
        start = transcript[i]["start"]
        j = i
        while j < len(transcript) and transcript[j]["end"] - start < max_sec:
            j += 1
        j = min(j, len(transcript) - 1)
        end = transcript[j]["end"]
        if end - start >= min_sec:
            picks.append({"start": start, "end": end, "first": transcript[i]["text"]})
            i = j + 1
        else:
            # 남은 구간이 최소 길이보다 짧으면 마지막 후보로 그냥 붙임
            if picks or end - start >= 10:
                picks.append({"start": start, "end": end, "first": transcript[i]["text"]})
            break
    return picks


def _sub_filter(srt_path):
    # ffmpeg subtitles 필터용 윈도우 경로 이스케이프
    p = str(srt_path).replace("\\", "/").replace(":", "\\:")
    return f"subtitles='{p}':force_style='FontSize=16,Alignment=2,MarginV=40'"


def run():
    cfg = load_config()["clip"]
    transcripts = sorted((DATA / "transcript").glob("*.json"))
    if not transcripts:
        warn(TAG, "전사 결과가 없습니다. M2를 먼저 실행하세요.")
        return False

    crop_pos = cfg.get("crop", "center")
    crop_x = {"left": "0", "center": "(iw-608)/2", "right": "iw-608"}[crop_pos]
    rows, cut = [], 0
    for tj in transcripts:
        stem = tj.stem
        video = DATA / "raw" / f"{stem}.mp4"
        srt = DATA / "transcript" / f"{stem}.srt"
        transcript = load_json(tj)
        picks = _pick_segments(transcript, cfg["min_sec"], cfg["max_sec"], cfg["max_candidates"])
        for n, seg in enumerate(picks, 1):
            clip_id = f"{stem}_clip{n:02}"
            out = DATA / "clips" / f"{clip_id}.mp4"
            status = "planned"
            if video.exists() and has_cmd("ffmpeg"):
                if not out.exists():
                    vf = f"crop=608:1080:{crop_x}:0,scale=1080:1920"
                    if srt.exists():
                        vf += "," + _sub_filter(srt)
                    ok = run_cmd([
                        "ffmpeg", "-y", "-ss", str(seg["start"]), "-to", str(seg["end"]),
                        "-i", str(video), "-vf", vf,
                        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", str(out),
                    ])
                    if not out.exists() and srt.exists():
                        # 자막 번인 실패 시 자막 없이 재시도
                        run_cmd([
                            "ffmpeg", "-y", "-ss", str(seg["start"]), "-to", str(seg["end"]),
                            "-i", str(video), "-vf", f"crop=608:1080:{crop_x}:0,scale=1080:1920",
                            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", str(out),
                        ])
                if out.exists():
                    status = "cut"
                    cut += 1
            rows.append({
                "clip_id": clip_id, "source": stem,
                "start": seg["start"], "end": seg["end"],
                "first_sentence": seg["first"],
                "file": out.name if status == "cut" else "",
                "status": status,
            })

    write_csv(MANIFEST, rows, MANIFEST_FIELDS)
    info(TAG, f"완료 — 후보 {len(rows)}개 (실제 잘라낸 것 {cut}개), clips/manifest.csv 갱신")
    info(TAG, "manifest.csv 를 열어 어떤 클립을 쓸지 사람이 고르면 됩니다")
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    run()
