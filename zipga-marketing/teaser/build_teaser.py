# 30초 유튜브 티저 합성
#   실제 앱 녹화(집가1~3)를 폰 프레임에 넣고, 콤피가 만든 배경 위에 얹어 자막과 함께 합칩니다.
#   실행: python build_teaser.py
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TMP = HERE / "_tmp"
DESKTOP = Path("C:/Users/User/OneDrive/Desktop")
BG = HERE / "assets" / "배경_보케.mp4"   # 콤피로 만든 배경 (소재라 watch 에 두지 않음)
OUT = HERE.parent / "uploader" / "watch" / "20_유튜브_티저_30초.mp4"

W, H = 1080, 1920
SCREEN_W, SCREEN_H = 620, 1102
SCREEN_X, SCREEN_Y = 230, 470
CROP = "crop=1080:1920:0:285"   # 브라우저 주소창·안드로이드 하단바 제거

# (원본, 시작초, 길이, 자막)
SEGMENTS_LONG = [
    ("집가1.mp4", 12,  5, "cap1"),   # 로비 — 친구들이 한 방에
    ("집가1.mp4", 45,  6, "cap2"),   # 알 깨기
    ("집가1.mp4", 86,  6, "cap3"),   # 틀린 그림 찾기
    ("집가3.mp4", 82,  5, "cap4"),   # 점수 결과
    ("집가2.mp4", 104, 4, "cap5"),   # 탈락
]                                     # + CTA 4초 = 30초

# 15초: 같은 흐름을 짧게 끊어 빠르게 넘김
SEGMENTS_SHORT = [
    ("집가1.mp4", 13,  2.2, "cap1"),
    ("집가1.mp4", 46,  2.2, "cap2"),
    ("집가1.mp4", 87,  2.2, "cap3"),
    ("집가3.mp4", 83,  2.2, "cap4"),
    ("집가2.mp4", 105, 2.2, "cap5"),
]                                     # + CTA 4초 = 15초

SEGMENTS = SEGMENTS_LONG
CTA_SEC = 4
CTA_IMG = "cta"


def log(m):
    print(m, flush=True)


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        log("[ffmpeg 오류]\n" + (p.stderr or "")[-1500:])
        return False
    return True


def make_segment(idx, src, start, dur, cap, fade_out=False):
    """배경 + 폰 안 앱화면 + 폰 프레임 + 자막을 합쳐 한 구간을 만듭니다."""
    out = TMP / f"seg{idx}.mp4"
    fade = f",afade=t=out:st={max(0, dur - 1.2):.1f}:d=1.2" if fade_out else ""
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(BG),                 # 0 배경 (반복)
        "-ss", str(start), "-t", str(dur), "-i", str(DESKTOP / src),  # 1 앱 녹화
        "-i", str(ASSETS / "phone_frame.png"),               # 2 폰 프레임
        "-i", str(ASSETS / f"{cap}.png"),                    # 3 자막
        "-i", str(ASSETS / "watermark.png"),                 # 4 로고 워터마크
        "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=18:2,eq=brightness=-0.08,trim=duration={dur},setpts=PTS-STARTPTS[bg];"
        f"[1:v]{CROP},scale={SCREEN_W}:{SCREEN_H},setpts=PTS-STARTPTS[app];"
        f"[bg][app]overlay={SCREEN_X}:{SCREEN_Y}[a];"
        f"[a][2:v]overlay=0:0[b];"
        f"[b][3:v]overlay=0:0[c];"
        f"[c][4:v]overlay=0:0,format=yuv420p[v];"
        # 녹화 원본 소리 — 조용해서(-30dB) 방송 레벨로 정규화
        f"[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11{fade}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", str(dur), str(out),
    ]
    log(f"  [{idx}/{len(SEGMENTS)}] {src} {start}s~ ({dur}초) · {cap}")
    return out if run(args) else None


def make_cta():
    out = TMP / "seg_cta.mp4"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(BG),
        "-i", str(ASSETS / f"{CTA_IMG}.png"),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=24:2,eq=brightness=-0.12,trim=duration={CTA_SEC},setpts=PTS-STARTPTS[bg];"
        f"[bg][1:v]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", str(CTA_SEC), str(out),
    ]
    log(f"  [CTA] ({CTA_SEC}초)")
    return out if run(args) else None


def main():
    global SEGMENTS, CTA_IMG, OUT
    ap = argparse.ArgumentParser(description="유튜브 티저 합성")
    ap.add_argument("--short", action="store_true", help="15초 버전 (기본은 30초)")
    ap.add_argument("--link", action="store_true", help="CTA를 '링크는 설명란에'로 (사이트 공개 후)")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.short:
        SEGMENTS = SEGMENTS_SHORT
        CTA_IMG = "cta_short"
        OUT = OUT.with_name("21_유튜브_티저_15초.mp4")
    if args.link:
        CTA_IMG = "cta_link"
        OUT = OUT.with_name(OUT.stem + "_링크.mp4")
    TMP.mkdir(exist_ok=True)

    if not BG.exists():
        log(f"[오류] 배경 영상이 없습니다: {BG}")
        log("       comfy 폴더에서 배경을 먼저 만드세요.")
        sys.exit(1)
    for src, *_ in SEGMENTS:
        if not (DESKTOP / src).exists():
            log(f"[오류] 원본 영상 없음: {DESKTOP / src}")
            sys.exit(1)

    log("=== 구간 합성 ===")
    parts = []
    for i, (src, start, dur, cap) in enumerate(SEGMENTS, 1):
        f = make_segment(i, src, start, dur, cap, fade_out=(i == len(SEGMENTS)))
        if not f:
            sys.exit(1)
        parts.append(f)
    cta = make_cta()
    if not cta:
        sys.exit(1)
    parts.append(cta)

    log("\n=== 이어붙이기 ===")
    listfile = TMP / "concat.txt"
    listfile.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    ok = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
              "-i", str(listfile), "-c", "copy", str(OUT)])
    if not ok or not OUT.exists():
        sys.exit(1)

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT)],
        capture_output=True, text=True).stdout.strip()
    log(f"\n=== 완성 ===")
    log(f"  {OUT}")
    log(f"  길이 {float(dur):.1f}초 · {W}x{H}")
    log("  소리: 녹화 원본(게임 효과음)을 방송 레벨로 정규화해 넣었습니다")


if __name__ == "__main__":
    main()
