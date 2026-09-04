# 시연영상으로 세로 홍보영상 3편 만들기
#   실제 시연 장면(가로 1920x1080)을 세로 9:16 화면에 얹고,
#   콤피가 만든 분위기 컷을 앞뒤에 붙여 한 편으로 만듭니다.
#
#   실행: python build_demo_videos.py            (3편 전부)
#         python build_demo_videos.py --only A   (한 편만)
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TMP = HERE / "_tmp_demo"
DESKTOP = Path("C:/Users/User/OneDrive/Desktop")
OUTDIR = HERE.parent / "uploader" / "watch"
AI_CLIP = OUTDIR / "_AI_분위기컷.mp4"      # 콤피 생성 (분위기컷 + 택시)

W, H = 1080, 1920
FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
WHITE = (255, 255, 255)
PURPLE = (196, 168, 255)

# 시연 원본 (전부 위에서 내려다본 앵글 — 얼굴 안 나옴)
D1 = "집가 시연영상.mp4"
D2 = "집가 시연영상2.mp4"
D3 = "집가 시연영상3.mp4"
# 폰 녹화 (세로 1080x2340) — 실제 게임 화면 클로즈업
P1 = "집가1.mp4"
P2 = "집가2.mp4"
P3 = "집가3.mp4"
PHONE_CROP = "crop=1080:1920:0:285"   # 브라우저 주소창·하단바 제거

BGM_DIR = HERE.parent / "bgm"          # 여기에 음악 파일을 넣으면 자동으로 깔립니다
BGM_VOL = 0.16                          # 배경음 크기 (0~1)

# (종류, 파일, 시작초, 길이, 자막윗줄, 자막아랫줄)
#   종류 real = 시연영상 / ai = 콤피 분위기컷
VIDEOS = {
    "A": {
        "out": "22_시연_모이기.mp4",
        "segs": [
            ("ai",   None, 0.4, 3.0, "친구들이랑 모였을 때", ""),
            ("real", D1,   3.0, 6.5, "QR 하나로", "다 같이 한 방에"),
            ("real", D1,   9.5, 5.0, "설치도 가입도 없이", "링크만 누르면 끝"),
        ],
    },
    "B": {
        "out": "23_시연_게임.mp4",
        "segs": [
            ("real",  D3, 50.0, 5.0, "정해진 시간마다", "다 같이 미니게임"),
            ("phone", P1, 46.0, 5.0, "아무 데나 두드리기", ""),
            ("phone", P1, 87.0, 5.0, "게임은 계속 바뀝니다", ""),
            ("real",  D2, 22.0, 4.5, "점수가 쌓입니다", ""),
        ],
    },
    "C": {
        "out": "24_시연_집가.mp4",
        "segs": [
            ("real", D2, 20.0, 5.5, "3판 평균 40점 아래면", ""),
            ("real", D3, 88.0, 5.5, "화면에 두 글자", "집 가"),
            ("ai",   None, 5.6, 4.5, "택시까지 바로", "이어집니다"),
        ],
    },
}


def font(size):
    return ImageFont.truetype(FONT_BD, size)


def make_caption(name, top, bottom):
    """자막 PNG — 위쪽에 큰 글씨, 아래쪽에 보조 문구."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def center(y, text, size, color):
        f = font(size)
        bb = d.textbbox((0, 0), text, font=f)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        d.text((x, y), text, font=f, fill=color, stroke_width=8,
               stroke_fill=(0, 0, 0, 225))

    y = 300
    if top:
        center(y, top, 68, WHITE)
        y += 96
    if bottom:
        center(y, bottom, 76 if bottom == "집 가" else 68,
               PURPLE if bottom == "집 가" else WHITE)
    img.save(ASSETS / f"demo_{name}.png")
    return ASSETS / f"demo_{name}.png"


def make_cta():
    """마지막 CTA — 로고 + 링크 안내."""
    p = ASSETS / "demo_cta.png"
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, 560, W - 70, 1360], radius=48, fill=(12, 10, 20, 236))
    d.rounded_rectangle([70, 560, W - 70, 1360], radius=48, outline=(139, 92, 246), width=4)

    logo_p = DESKTOP / "zipga_logo.png"
    y = 640
    if logo_p.exists():
        lg = Image.open(logo_p).convert("RGBA")
        lw = 600
        lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
        img.alpha_composite(lg, ((W - lw) // 2, y))
        y += lg.height + 60

    for text, size, color, gap in [
        ("지금 바로 해보세요", 72, WHITE, 108),
        ("설치 없이 링크만", 48, (200, 200, 215), 84),
        ("링크는 설명란에", 56, PURPLE, 0),
    ]:
        f = font(size)
        bb = d.textbbox((0, 0), text, font=f)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        d.text((x, y), text, font=f, fill=color)
        y += gap
    img.save(p)
    return p


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[ffmpeg 오류]\n" + (r.stderr or "")[-1200:])
        return False
    return True


def make_segment(idx, kind, src, start, dur, cap_png, tag):
    """세로 폰 녹화는 화면을 꽉 채우고, 가로 영상은 흐린 배경 위에 얹습니다."""
    out = TMP / f"{tag}_{idx}.mp4"
    path = AI_CLIP if kind == "ai" else (DESKTOP / src)

    if kind == "phone":
        base = (f"[0:v]{PHONE_CROP},scale={W}:{H},setpts=PTS-STARTPTS[a];")
    else:
        base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=26:2,eq=brightness=-0.13,setpts=PTS-STARTPTS[bg];"
                f"[0:v]scale={W}:-2,setpts=PTS-STARTPTS[fg];"
                f"[bg][fg]overlay=0:(H-h)/2[a];")

    args = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(start), "-t", str(dur), "-i", str(path),
        "-i", str(cap_png),
        "-i", str(ASSETS / "watermark.png"),
        "-filter_complex",
        base + "[a][1:v]overlay=0:0[b];[b][2:v]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
        "-t", str(dur), str(out),
    ]
    label = {"real": "시연", "phone": "게임화면", "ai": "AI컷"}[kind]
    print(f"  [{idx}] {label} {src or ''} {start}s~ ({dur}초)")
    return out if run(args) else None


def find_bgm():
    """bgm 폴더에 음악 파일이 있으면 첫 번째 것을 씁니다."""
    if not BGM_DIR.exists():
        return None
    for f in sorted(BGM_DIR.iterdir()):
        if f.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}:
            return f
    return None


def add_bgm(video, bgm, out):
    """영상에 배경음을 깔고 앞뒤로 페이드를 넣습니다."""
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip())
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(bgm),
        "-filter_complex",
        f"[1:a]volume={BGM_VOL},afade=t=in:st=0:d=1.2,"
        f"afade=t=out:st={max(0, dur - 1.5):.2f}:d=1.5,"
        f"atrim=duration={dur},aresample=48000[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out),
    ]
    return run(args)


def make_cta_seg(cta_png, tag, sec=4.0):
    out = TMP / f"{tag}_cta.mp4"
    args = [
        "ffmpeg", "-y", "-v", "error",
        "-stream_loop", "-1", "-i", str(AI_CLIP),
        "-i", str(cta_png),
        "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=30:2,eq=brightness=-0.16,trim=duration={sec},setpts=PTS-STARTPTS[bg];"
        f"[bg][1:v]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
        "-t", str(sec), str(out),
    ]
    print(f"  [CTA] ({sec}초)")
    return out if run(args) else None


def build(key, spec, cta_png):
    print(f"\n=== 영상 {key} — {spec['out']} ===")
    parts = []
    for i, (kind, src, start, dur, top, bottom) in enumerate(spec["segs"], 1):
        cap = make_caption(f"{key}{i}", top, bottom)
        f = make_segment(i, kind, src, start, dur, cap, key)
        if not f:
            return None
        parts.append(f)
    cta = make_cta_seg(cta_png, key)
    if not cta:
        return None
    parts.append(cta)

    lst = TMP / f"{key}_concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    out = OUTDIR / spec["out"]
    if not run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c", "copy", str(out)]):
        return None
    bgm = find_bgm()
    if bgm:
        tmp_out = TMP / f"{key}_bgm.mp4"
        if add_bgm(out, bgm, tmp_out):
            tmp_out.replace(out)
            print(f"  BGM 적용: {bgm.name}")
        else:
            print("  BGM 적용 실패 — 영상은 정상")

    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"  완성 → {out.name} ({float(dur):.1f}초)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(VIDEOS), help="한 편만 만들기")
    a = ap.parse_args()

    TMP.mkdir(exist_ok=True)
    if not AI_CLIP.exists():
        print(f"[오류] AI 분위기컷이 없습니다: {AI_CLIP}")
        print("       comfy 폴더에서 먼저 생성하세요.")
        sys.exit(1)
    for f in [D1, D2, D3]:
        if not (DESKTOP / f).exists():
            print(f"[오류] 시연영상 없음: {f}")
            sys.exit(1)

    bgm = find_bgm()
    print(f"BGM: {bgm.name if bgm else '없음 — bgm 폴더에 음악 파일을 넣으면 자동으로 깔립니다'}")

    cta = make_cta()
    keys = [a.only] if a.only else list(VIDEOS)
    done = [build(k, VIDEOS[k], cta) for k in keys]
    if all(done):
        print(f"\n=== 전부 완성 ({len(done)}편) — uploader\\watch 폴더 확인 ===")


if __name__ == "__main__":
    main()
