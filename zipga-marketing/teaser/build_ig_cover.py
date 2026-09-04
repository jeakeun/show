# 인스타 릴스 커버 만들기 (1080x1920)
#   릴스는 피드/그리드에서 가운데 정사각형(1080x1080)만 잘려 보입니다.
#   그래서 로고와 핵심 문구를 그 안에 넣습니다.
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
LOGO = Path("C:/Users/User/OneDrive/Desktop/zipga_logo.png")

W, H = 1080, 1920
SQ_TOP = (H - W) // 2          # 그리드에서 잘려 보이는 정사각형 영역 (420 ~ 1500)
FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
WHITE = (255, 255, 255)
PURPLE = (196, 168, 255)


def font(size):
    return ImageFont.truetype(FONT_BD, size)


def centered(d, y, text, f, fill, stroke=8):
    bbox = d.textbbox((0, 0), text, font=f)
    x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
    d.text((x, y), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 230))


def main():
    frame = OUT / "_thumb_frame.png"
    if frame.exists():
        bg = Image.open(frame).convert("RGB").resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(6))
    else:
        bg = Image.new("RGB", (W, H), (26, 18, 46))
    img = bg.convert("RGBA")
    ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=(12, 8, 24, 120))
    d = ImageDraw.Draw(img)

    # --- 아래부터는 전부 가운데 정사각형(420~1500) 안 ---
    y = SQ_TOP + 70
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        lw = 620
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        img.alpha_composite(logo, ((W - lw) // 2, y))
        y += logo.height + 60

    centered(d, y, "이런 게임 있으면", font(76), WHITE)
    y += 104
    centered(d, y, "해보실 건가요?", font(84), PURPLE)
    y += 130
    centered(d, y, "점수 낮으면 집 가", font(48), (225, 225, 240), stroke=6)

    bottom = y + 66
    assert bottom <= SQ_TOP + W, f"정사각형 영역 초과: {bottom} > {SQ_TOP + W}"

    img.convert("RGB").save(OUT / "ig_cover.jpg", quality=93)
    print(f"ig_cover.jpg 생성 · 정사각형 {SQ_TOP}~{SQ_TOP + W} 안에 {SQ_TOP + 70}~{bottom} 배치")


if __name__ == "__main__":
    main()
