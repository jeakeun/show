# 티저 합성용 이미지 소재 생성
#   - 폰 프레임 PNG (가운데가 뚫린 베젤 + 그림자)
#   - 구간별 자막 PNG
# 실행: python build_assets.py
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920                 # 최종 캔버스 (9:16)
SCREEN_W, SCREEN_H = 620, 1102    # 폰 안 화면 크기 (9:16)
SCREEN_X = (W - SCREEN_W) // 2    # 230
SCREEN_Y = 470
BEZEL = 18                        # 베젤 두께
RADIUS = 46                       # 폰 모서리 둥글기

FONT_BD = "C:/Windows/Fonts/malgunbd.ttf"
FONT_RG = "C:/Windows/Fonts/malgun.ttf"
LOGO = Path("C:/Users/User/OneDrive/Desktop/zipga_logo.png")
ICON = Path("C:/Users/User/OneDrive/Desktop/zipga_icon.png")
PURPLE = (139, 92, 246)
WHITE = (255, 255, 255)


def font(path, size):
    return ImageFont.truetype(path, size)


def make_phone_frame():
    """가운데가 뚫린 폰 베젤 + 바깥 그림자."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    body = (SCREEN_X - BEZEL, SCREEN_Y - BEZEL,
            SCREEN_X + SCREEN_W + BEZEL, SCREEN_Y + SCREEN_H + BEZEL)

    # 그림자
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [body[0], body[1] + 14, body[2], body[3] + 22], radius=RADIUS, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    img = Image.alpha_composite(img, shadow)

    # 폰 몸체 (검정) — 안쪽을 뚫어 화면이 보이게
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(body, radius=RADIUS, fill=(18, 18, 22, 255))
    d.rounded_rectangle(
        [SCREEN_X, SCREEN_Y, SCREEN_X + SCREEN_W, SCREEN_Y + SCREEN_H],
        radius=RADIUS - BEZEL, fill=(0, 0, 0, 0))

    # 테두리 하이라이트
    d.rounded_rectangle(body, radius=RADIUS, outline=(90, 90, 100, 255), width=3)
    img.save(OUT / "phone_frame.png")
    print("phone_frame.png")


def draw_text_center(d, y, text, f, fill, stroke=6):
    bbox = d.textbbox((0, 0), text, font=f)
    x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
    d.text((x, y), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 210))


def make_caption(name, top_lines=None, bottom_lines=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if top_lines:
        y = 150
        for i, (text, size, color) in enumerate(top_lines):
            draw_text_center(d, y, text, font(FONT_BD, size), color)
            y += int(size * 1.35)
    if bottom_lines:
        total = sum(int(s * 1.35) for _, s, _ in bottom_lines)
        y = H - 210 - total
        for text, size, color in bottom_lines:
            draw_text_center(d, y, text, font(FONT_BD, size), color)
            y += int(size * 1.35)
    img.save(OUT / f"{name}.png")
    print(f"{name}.png")


def make_cta():
    """마지막 CTA 카드 — 배경 위에 반투명 판 + 문구."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, 520, W - 70, 1400], radius=48, fill=(12, 10, 20, 232))
    d.rounded_rectangle([70, 520, W - 70, 1400], radius=48, outline=PURPLE, width=4)

    y = 640
    for text, size, color, gap in [
        ("이런 게임 있으면", 76, WHITE, 96),
        ("해보실 건가요?", 76, PURPLE, 150),
        ("댓글 남겨주시면", 52, (225, 225, 235), 68),
        ("링크 보내드릴게요", 52, (225, 225, 235), 130),
        ("설치 없이 링크로 바로", 40, (160, 160, 175), 0),
    ]:
        f = font(FONT_BD if size >= 52 else FONT_RG, size)
        bbox = d.textbbox((0, 0), text, font=f)
        x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
        d.text((x, y), text, font=f, fill=color)
        y += gap
    img.save(OUT / "cta.png")
    print("cta.png")


def make_cta_short():
    """15초 버전용 CTA — 문구를 줄여 빠르게 읽히게."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, 620, W - 70, 1300], radius=48, fill=(12, 10, 20, 235))
    d.rounded_rectangle([70, 620, W - 70, 1300], radius=48, outline=PURPLE, width=4)

    y = 730
    for text, size, color, gap in [
        ("해보실 건가요?", 88, WHITE, 130),
        ("댓글 남기면", 58, PURPLE, 78),
        ("링크 보내드려요", 58, PURPLE, 0),
    ]:
        f = font(FONT_BD, size)
        bbox = d.textbbox((0, 0), text, font=f)
        x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
        d.text((x, y), text, font=f, fill=color)
        y += gap
    img.save(OUT / "cta_short.png")
    print("cta_short.png")


def _fit(img, width):
    """가로 폭에 맞춰 비율 유지 축소."""
    w, h = img.size
    return img.resize((width, int(h * width / w)), Image.LANCZOS)


def make_cta_link():
    """링크 공개 후 CTA — 로고 + 설명란 링크 유도."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, 520, W - 70, 1400], radius=48, fill=(12, 10, 20, 236))
    d.rounded_rectangle([70, 520, W - 70, 1400], radius=48, outline=PURPLE, width=4)

    if LOGO.exists():
        logo = _fit(Image.open(LOGO).convert("RGBA"), 620)
        img.alpha_composite(logo, ((W - logo.width) // 2, 600))
        y = 600 + logo.height + 70
    else:
        y = 700

    for text, size, color, gap in [
        ("해보실 건가요?", 82, WHITE, 118),
        ("지금 바로 됩니다 · 설치 없이", 46, (200, 200, 215), 96),
        ("링크는 설명란에", 58, PURPLE, 0),
    ]:
        f = font(FONT_BD, size)
        bbox = d.textbbox((0, 0), text, font=f)
        x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
        d.text((x, y), text, font=f, fill=color)
        y += gap
    img.save(OUT / "cta_link.png")
    print("cta_link.png")


def make_watermark():
    """영상 우상단에 작게 올릴 로고 워터마크."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if LOGO.exists():
        logo = _fit(Image.open(LOGO).convert("RGBA"), 230)
        faded = Image.new("RGBA", logo.size, (0, 0, 0, 0))
        faded = Image.blend(faded, logo, 0.85)
        img.alpha_composite(faded, (W - logo.width - 46, 44))
    img.save(OUT / "watermark.png")
    print("watermark.png")


def make_thumbnail(frame_path=None):
    """유튜브 썸네일 — 아이콘 + 훅 문구."""
    bg = Image.new("RGB", (W, H), (16, 13, 24))
    if frame_path and Path(frame_path).exists():
        shot = Image.open(frame_path).convert("RGB").resize((W, H), Image.LANCZOS)
        bg = Image.blend(bg, shot, 0.55)
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(10, 8, 16, 90))

    if ICON.exists():
        icon = _fit(Image.open(ICON).convert("RGBA"), 560)
        img.alpha_composite(icon, ((W - icon.width) // 2, 380))

    y = 1080
    for text, size, color in [("이런 게임 있으면", 86, WHITE), ("해보실 건가요?", 96, (196, 168, 255))]:
        f = font(FONT_BD, size)
        bbox = d.textbbox((0, 0), text, font=f)
        x = (W - (bbox[2] - bbox[0])) // 2 - bbox[0]
        d.text((x, y), text, font=f, fill=color, stroke_width=9, stroke_fill=(0, 0, 0, 235))
        y += int(size * 1.35)

    f = font(FONT_BD, 52)
    tail = "점수 낮으면 집 가"
    bbox = d.textbbox((0, 0), tail, font=f)
    d.text(((W - (bbox[2] - bbox[0])) // 2 - bbox[0], y + 40), tail, font=f,
           fill=(235, 235, 245), stroke_width=7, stroke_fill=(0, 0, 0, 235))

    img.convert("RGB").save(OUT / "thumbnail.jpg", quality=92)
    print("thumbnail.jpg")


if __name__ == "__main__":
    make_phone_frame()
    make_caption("cap1", top_lines=[("친구들이 한 방에 모입니다", 62, WHITE)])
    make_caption("cap2", top_lines=[("정해진 시간마다 미니게임", 62, WHITE)],
                 bottom_lines=[("아무 데나 두드리기", 46, (200, 200, 215))])
    make_caption("cap3", top_lines=[("게임은 계속 바뀝니다", 62, WHITE)],
                 bottom_lines=[("틀린 그림 찾기", 46, (200, 200, 215))])
    make_caption("cap4", top_lines=[("3판 평균으로 점수가 남고", 62, WHITE)])
    make_caption("cap5", top_lines=[("40점 아래면", 62, WHITE), ("집 가", 96, PURPLE)])
    make_cta()
    make_cta_short()
    make_cta_link()
    make_watermark()
    print("\n완료 —", OUT)
