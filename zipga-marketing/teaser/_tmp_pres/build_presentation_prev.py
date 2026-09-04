# 발표용 시연 영상 (가로 1920x1080, 한 편)
#   시연영상 3개 + 실제 게임 화면을 하나로 이어 붙입니다.
#   홍보용 CTA(링크 안내)는 넣지 않습니다.
#
#   실행: python build_presentation.py
#         python build_presentation.py --no-bgm     (음악 없이)
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TMP = HERE / "_tmp_pres"
DESKTOP = Path("C:/Users/User/OneDrive/Desktop")
BGM_DIR = HERE.parent / "bgm"
OUT = HERE.parent / "발표용_집가_시연.mp4"

W, H = 1920, 1080           # 발표 화면에 맞춘 가로
FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
WHITE = (255, 255, 255)
PURPLE = (196, 168, 255)
BGM_VOL = 0.12              # 발표용이라 조금 더 작게

D1, D2, D3 = "집가 시연영상.mp4", "집가 시연영상2.mp4", "집가 시연영상3.mp4"
P1 = "집가1.mp4"
PHONE_CROP = "crop=1080:1920:0:285"

# (종류, 파일, 시작초, 길이, 자막)
#   real = 가로 시연영상 / phone = 세로 폰 녹화(게임 화면)
SEGS = [
    ("real",  D1,  3.0, 7.0, "방장이 QR을 띄우면 다 같이 스캔"),
    ("real",  D1, 10.5, 4.5, "설치도 가입도 없이 링크만"),
    ("real",  D3, 50.0, 5.5, "정해진 시간마다 다 같이 미니게임"),
    ("phone", P1, 46.0, 5.0, "각자 폰에서 동시에 — 알 깨기"),
    ("phone", P1, 87.0, 5.0, "게임은 계속 바뀝니다 — 틀린 그림 찾기"),
    ("real",  D2, 22.0, 5.0, "3판 평균으로 점수가 남고"),
    ("real",  D3, 88.0, 5.5, "40점 아래면 — 집 가"),
]
END_SEC = 3.5


def font(size):
    return ImageFont.truetype(FONT_BD, size)


def caption_png(idx, text):
    """아래쪽 자막 (가로 화면이라 하단 배치)."""
    p = ASSETS / f"pres_{idx}.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(58)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - tw) // 2 - bb[0], H - 150
    # 가독성용 반투명 띠
    d.rounded_rectangle([x - 40, y - 26, x + tw + 40, y + th + 30],
                        radius=18, fill=(10, 8, 18, 170))
    d.text((x, y), text, font=f, fill=WHITE, stroke_width=5,
           stroke_fill=(0, 0, 0, 220))
    img.save(p)
    return p


def end_png():
    """마지막 로고 화면 — 링크 안내 없이 브랜드만."""
    p = ASSETS / "pres_end.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    logo = DESKTOP / "zipga_logo.png"
    y = 330
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lw = 760
        lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
        img.alpha_composite(lg, ((W - lw) // 2, y))
        y += lg.height + 50
    text = "점수가 낮으면, 집에 갈 시간"
    f = font(64)
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y), text, font=f,
           fill=PURPLE, stroke_width=5, stroke_fill=(0, 0, 0, 220))
    img.save(p)
    return p


def run(args):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[ffmpeg 오류]\n" + (r.stderr or "")[-1200:])
        return False
    return True


def make_seg(idx, kind, src, start, dur, cap):
    out = TMP / f"s{idx}.mp4"
    if kind == "phone":
        # 세로 녹화(흰 UI)라 블러 배경이 뿌옇게 뭉개진다 -> 어두운 브랜드색 배경에 얹는다
        base = (f"color=c=0x140f1e:s={W}x{H}:d={dur}:r=30[bg];"
                f"[0:v]{PHONE_CROP},scale=-2:{H},setpts=PTS-STARTPTS[fg];"
                f"[bg][fg]overlay=(W-w)/2:0:shortest=1[a];")
    else:
        base = f"[0:v]scale={W}:{H},setpts=PTS-STARTPTS[a];"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(start), "-t", str(dur), "-i", str(DESKTOP / src),
        "-i", str(cap),
        "-filter_complex", base + "[a][1:v]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30",
        "-t", str(dur), str(out),
    ]
    print(f"  [{idx}] {'게임화면' if kind == 'phone' else '시연'} {src} {start}s~ ({dur}초)")
    return out if run(args) else None


def make_end(png):
    out = TMP / "end.mp4"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=0x140f1e:s={W}x{H}:d={END_SEC}:r=30",
        "-i", str(png),
        "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-t", str(END_SEC), str(out),
    ]
    print(f"  [마무리] 로고 ({END_SEC}초)")
    return out if run(args) else None


def find_bgm():
    if not BGM_DIR.exists():
        return None
    for f in sorted(BGM_DIR.iterdir()):
        if f.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}:
            return f
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bgm", action="store_true", help="배경음 없이")
    a = ap.parse_args()

    TMP.mkdir(exist_ok=True)
    for f in {D1, D2, D3, P1}:
        if not (DESKTOP / f).exists():
            print(f"[오류] 원본 없음: {f}")
            sys.exit(1)

    print("=== 발표용 영상 만들기 (1920x1080) ===")
    parts = []
    for i, (kind, src, start, dur, text) in enumerate(SEGS, 1):
        f = make_seg(i, kind, src, start, dur, caption_png(i, text))
        if not f:
            sys.exit(1)
        parts.append(f)
    end = make_end(end_png())
    if not end:
        sys.exit(1)
    parts.append(end)

    lst = TMP / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    tmp_out = TMP / "joined.mp4"
    if not run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c", "copy", str(tmp_out)]):
        sys.exit(1)

    bgm = None if a.no_bgm else find_bgm()
    if bgm:
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(tmp_out)], capture_output=True, text=True).stdout.strip())
        ok = run([
            "ffmpeg", "-y", "-v", "error",
            "-i", str(tmp_out), "-stream_loop", "-1", "-i", str(bgm),
            "-filter_complex",
            f"[1:a]volume={BGM_VOL},afade=t=in:st=0:d=1.5,"
            f"afade=t=out:st={max(0, dur - 2):.2f}:d=2,"
            f"atrim=duration={dur},aresample=48000[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT)])
        if ok:
            print(f"  BGM: {bgm.name}")
        else:
            tmp_out.replace(OUT)
            print("  BGM 적용 실패 — 무음으로 저장")
    else:
        tmp_out.replace(OUT)
        print("  BGM: 없음")

    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(OUT)], capture_output=True, text=True).stdout.strip()
    print(f"\n=== 완성 ===\n  {OUT}\n  {float(dur):.1f}초 · {W}x{H}")


if __name__ == "__main__":
    main()
