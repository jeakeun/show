# 유튜브 채널 배너 만들기 (2048x1152)
#   중요한 내용은 가운데 안전영역(1546x423) 안에만 넣습니다.
#   TV·PC·모바일에서 잘리는 범위가 달라서, 안전영역 밖은 배경만 보이게 합니다.
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
LOGO = Path("C:/Users/User/OneDrive/Desktop/zipga_logo.png")

W, H = 2048, 1152
SAFE_W, SAFE_H = 1546, 423          # 모든 기기에서 보이는 영역
SAFE_X, SAFE_Y = (W - SAFE_W) // 2, (H - SAFE_H) // 2

FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
PURPLE_DARK = (46, 28, 92)
PURPLE = (139, 92, 246)
WHITE = (255, 255, 255)


def font(size):
    return ImageFont.truetype(FONT_BD, size)


def gradient_bg():
    """보라 → 짙은 남보라 대각 그라데이션."""
    base = Image.new("RGB", (W, H), PURPLE_DARK)
    d = ImageDraw.Draw(base)
    for y in range(H):
        t = y / H
        r = int(78 + (24 - 78) * t)
        g = int(46 + (18 - 46) * t)
        b = int(150 + (58 - 150) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # 은은한 빛망울
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx, cy, rad, alpha in [(430, 250, 300, 60), (1650, 880, 360, 55), (1300, 200, 220, 45)]:
        gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(180, 140, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    return Image.alpha_composite(base.convert("RGBA"), glow)


def centered(d, y, text, f, fill, stroke=0):
    bbox = d.textbbox((0, 0), text, font=f)
    x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
    d.text((x, y), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=(20, 12, 40, 200))


def main():
    img = gradient_bg()
    d = ImageDraw.Draw(img)

    # 안전영역(1546x423) 안에 로고 + 문구를 모두 넣는다
    logo_h = 0
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        lw = 430
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        logo_h = logo.height
        img.alpha_composite(logo, ((W - lw) // 2, SAFE_Y + 14))

    y = SAFE_Y + 14 + logo_h + 18
    centered(d, y, "점수가 낮으면, 집에 갈 시간", font(52), WHITE, stroke=4)
    y += 74
    centered(d, y, "zip-ga-frontend.vercel.app", font(34), (214, 196, 255), stroke=3)

    bottom = y + 44
    assert bottom <= SAFE_Y + SAFE_H, f"안전영역 초과: {bottom} > {SAFE_Y + SAFE_H}"

    img.convert("RGB").save(OUT / "banner.jpg", quality=94)
    print(f"banner.jpg 생성 (2048x1152) · 안전영역 {SAFE_Y}~{SAFE_Y+SAFE_H} 안에 {SAFE_Y+14}~{bottom} 배치")


if __name__ == "__main__":
    main()
