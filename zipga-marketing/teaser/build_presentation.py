# 집가 시연 통합 영상 — 시연영상 3개 + 실제 게임화면을 한 편으로
#
#   python build_presentation.py            발표용 (가로 1920x1080, CTA 없음)
#   python build_presentation.py --shorts   쇼츠/릴스용 (세로 1080x1920, CTA·링크 포함)
#   python build_presentation.py --no-bgm   배경음 없이
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
WATCH = HERE.parent / "uploader" / "watch"

OUT_PRES = HERE.parent / "발표용_집가_시연.mp4"
OUT_SHORTS = WATCH / "25_시연_풀버전.mp4"

FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
WHITE = (255, 255, 255)
GREY = (200, 200, 215)
PURPLE = (196, 168, 255)
BG_DARK = "0x140f1e"
LINK = "zip-ga-frontend.vercel.app"

D1, D2, D3 = "집가 시연영상.mp4", "집가 시연영상2.mp4", "집가 시연영상3.mp4"
P1 = "집가1.mp4"
PHONE_CROP = "crop=1080:1920:0:285"      # 브라우저 주소창·하단바 제거

# (종류, 파일, 시작초, 길이, 가로용 한 줄 자막, 세로용 (윗줄, 아랫줄))
SEGS = [
    ("real",  D1,  3.0, 7.0, "방장이 QR을 띄우면 다 같이 스캔",
     ("QR 하나로", "다 같이 한 방에")),
    ("real",  D1, 10.5, 4.5, "설치도 가입도 없이 링크만",
     ("설치도 가입도 없이", "링크만 누르면 끝")),
    ("real",  D3, 50.0, 5.5, "정해진 시간마다 다 같이 미니게임",
     ("정해진 시간마다", "다 같이 미니게임")),
    ("phone", P1, 46.0, 5.0, "각자 폰에서 동시에 — 알 깨기",
     ("각자 폰에서 동시에", "")),
    ("phone", P1, 87.0, 5.0, "게임은 계속 바뀝니다 — 틀린 그림 찾기",
     ("게임은 계속 바뀝니다", "")),
    ("real",  D2, 22.0, 5.0, "3판 평균으로 점수가 남고",
     ("3판 평균으로", "점수가 남고")),
    ("real",  D3, 88.0, 5.5, "40점 아래면 — 집 가",
     ("40점 아래면", "집 가")),
]
END_SEC = 3.5
CTA_SEC = 4.5


def font(size):
    return ImageFont.truetype(FONT_BD, size)


# ---------- 자막 ----------

def caption_wide(W, H, idx, text):
    """가로용 — 하단 반투명 띠 위에 한 줄."""
    p = ASSETS / f"pres_w{idx}.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(58)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - tw) // 2 - bb[0], H - 150
    d.rounded_rectangle([x - 40, y - 26, x + tw + 40, y + th + 30],
                        radius=18, fill=(10, 8, 18, 170))
    d.text((x, y), text, font=f, fill=WHITE, stroke_width=5,
           stroke_fill=(0, 0, 0, 220))
    img.save(p)
    return p


def caption_tall(W, H, idx, lines):
    """세로용 — 화면 위쪽에 두 줄 (기존 시연 3편과 같은 스타일)."""
    top, bottom = lines
    p = ASSETS / f"pres_t{idx}.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def center(y, text, size, color):
        f = font(size)
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y), text, font=f,
               fill=color, stroke_width=8, stroke_fill=(0, 0, 0, 225))

    y = 300
    if top:
        center(y, top, 68, WHITE)
        y += 96
    if bottom:
        big = bottom == "집 가"
        center(y, bottom, 76 if big else 68, PURPLE if big else WHITE)
    img.save(p)
    return p


# ---------- 마지막 화면 ----------

def end_png(W, H):
    """발표용 마무리 — 로고만, 링크 안내 없음."""
    p = ASSETS / "pres_end.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 330
    logo = DESKTOP / "zipga_logo.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lw = 760
        lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
        img.alpha_composite(lg, ((W - lw) // 2, y))
        y += lg.height + 50
    f = font(64)
    text = "점수가 낮으면, 집에 갈 시간"
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y), text, font=f,
           fill=PURPLE, stroke_width=5, stroke_fill=(0, 0, 0, 220))
    img.save(p)
    return p


def cta_png(W, H):
    """쇼츠/릴스용 CTA — 로고 + 안내 + 실제 링크 주소."""
    p = ASSETS / "pres_cta.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = [70, 520, W - 70, 1420]
    d.rounded_rectangle(box, radius=48, fill=(12, 10, 20, 238))
    d.rounded_rectangle(box, radius=48, outline=(139, 92, 246), width=4)

    y = 600
    logo = DESKTOP / "zipga_logo.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lw = 600
        lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
        img.alpha_composite(lg, ((W - lw) // 2, y))
        y += lg.height + 60

    for text, size, color, gap in [
        ("지금 바로 해보세요", 72, WHITE, 104),
        ("설치 없이 링크만", 46, GREY, 96),
        (LINK, 44, PURPLE, 84),
        ("링크는 설명란에", 44, GREY, 0),
    ]:
        f = font(size)
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y), text, font=f, fill=color)
        y += gap
    assert y <= box[3], "CTA 글자가 상자 밖으로 넘칩니다"
    img.save(p)
    return p


# ---------- ffmpeg ----------

def run(args):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[ffmpeg 오류]\n" + (r.stderr or "")[-1200:])
        return False
    return True


def probe(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())


def make_seg(W, H, tall, idx, kind, src, start, dur, cap):
    out = TMP / f"s{idx}.mp4"
    if tall:
        if kind == "phone":
            base = f"[0:v]{PHONE_CROP},scale={W}:{H},setpts=PTS-STARTPTS[a];"
        else:
            # 가로 원본을 세로 화면에: 흐린 배경 위에 가로폭 맞춰 얹기
            base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"boxblur=26:2,eq=brightness=-0.13,setpts=PTS-STARTPTS[bg];"
                    f"[0:v]scale={W}:-2,setpts=PTS-STARTPTS[fg];"
                    f"[bg][fg]overlay=0:(H-h)/2[a];")
        overlays = "[a][1:v]overlay=0:0[b];[b][2:v]overlay=0:0,format=yuv420p[v]"
        extra_in = ["-i", str(ASSETS / "watermark.png")]
    else:
        if kind == "phone":
            # 세로 녹화(흰 UI)는 블러 배경이 뿌옇게 뭉개진다 -> 어두운 브랜드색 배경
            base = (f"color=c={BG_DARK}:s={W}x{H}:d={dur}:r=30[bg];"
                    f"[0:v]{PHONE_CROP},scale=-2:{H},setpts=PTS-STARTPTS[fg];"
                    f"[bg][fg]overlay=(W-w)/2:0:shortest=1[a];")
        else:
            base = f"[0:v]scale={W}:{H},setpts=PTS-STARTPTS[a];"
        overlays = "[a][1:v]overlay=0:0,format=yuv420p[v]"
        extra_in = []

    args = ["ffmpeg", "-y", "-v", "error",
            "-ss", str(start), "-t", str(dur), "-i", str(DESKTOP / src),
            "-i", str(cap), *extra_in,
            "-filter_complex", base + overlays,
            "-map", "[v]", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30",
            "-t", str(dur), str(out)]
    print(f"  [{idx}] {'게임화면' if kind == 'phone' else '시연'} {src} {start}s~ ({dur}초)")
    return out if run(args) else None


def make_card(W, H, png, sec, name, label):
    out = TMP / f"{name}.mp4"
    args = ["ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"color=c={BG_DARK}:s={W}x{H}:d={sec}:r=30",
            "-i", str(png),
            "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p[v]",
            "-map", "[v]", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-t", str(sec), str(out)]
    print(f"  [{label}] ({sec}초)")
    return out if run(args) else None


def find_bgm():
    if not BGM_DIR.exists():
        return None
    for f in sorted(BGM_DIR.iterdir()):
        if f.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}:
            return f
    return None


def add_bgm(src, bgm, out, vol):
    dur = probe(src)
    return run(["ffmpeg", "-y", "-v", "error",
                "-i", str(src), "-stream_loop", "-1", "-i", str(bgm),
                "-filter_complex",
                f"[1:a]volume={vol},afade=t=in:st=0:d=1.5,"
                f"afade=t=out:st={max(0, dur - 2):.2f}:d=2,"
                f"atrim=duration={dur},aresample=48000[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shorts", action="store_true",
                    help="쇼츠/릴스용 세로 버전 (CTA·링크 포함)")
    ap.add_argument("--no-bgm", action="store_true", help="배경음 없이")
    a = ap.parse_args()

    tall = a.shorts
    W, H = (1080, 1920) if tall else (1920, 1080)
    out_path = OUT_SHORTS if tall else OUT_PRES
    bgm_vol = 0.16 if tall else 0.12

    TMP.mkdir(exist_ok=True)
    for f in {D1, D2, D3, P1}:
        if not (DESKTOP / f).exists():
            print(f"[오류] 원본 없음: {f}")
            sys.exit(1)

    print(f"=== {'쇼츠·릴스용 (세로)' if tall else '발표용 (가로)'} {W}x{H} ===")
    parts = []
    for i, (kind, src, start, dur, wide, lines) in enumerate(SEGS, 1):
        cap = caption_tall(W, H, i, lines) if tall else caption_wide(W, H, i, wide)
        f = make_seg(W, H, tall, i, kind, src, start, dur, cap)
        if not f:
            sys.exit(1)
        parts.append(f)

    if tall:
        last = make_card(W, H, cta_png(W, H), CTA_SEC, "cta", "CTA·링크")
    else:
        last = make_card(W, H, end_png(W, H), END_SEC, "end", "마무리")
    if not last:
        sys.exit(1)
    parts.append(last)

    lst = TMP / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    joined = TMP / "joined.mp4"
    if not run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c", "copy", str(joined)]):
        sys.exit(1)

    bgm = None if a.no_bgm else find_bgm()
    if bgm and add_bgm(joined, bgm, out_path, bgm_vol):
        print(f"  BGM: {bgm.name}")
    else:
        joined.replace(out_path)
        print("  BGM: 없음" if not bgm else "  BGM 적용 실패 — 무음으로 저장")

    print(f"\n=== 완성 ===\n  {out_path}\n  {probe(out_path):.1f}초 · {W}x{H}")


if __name__ == "__main__":
    main()
