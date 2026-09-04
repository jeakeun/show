"""영상 렌더링 엔진.

기본: 대본 내용에 맞는 장면(scene)별 애니메이션 배경
  - 장면마다 다른 그라데이션 + 크로스페이드 전환
  - 내용에 맞는 이모지가 둥실거리며 등장 (스케일 팝인 + 바운스)
  - 위로 떠오르는 파티클, 키워드 자막, 상단 타이틀
프레임을 PIL로 그려 ffmpeg stdin(rawvideo)으로 파이프하고,
자막(SRT)은 ffmpeg subtitles 필터로 굽는다.

애니메이션 실패 시 정지 배경(make_background + render_video)으로 폴백한다.
"""
import math
import random
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import CONFIG, KOREAN_FONT, find_ffmpeg

FPS = 30
EMOJI_FONT = r"C:\Windows\Fonts\seguiemj.ttf"
BGM_DIR = Path(__file__).resolve().parent.parent / "assets" / "bgm"
BGM_VOLUME = 0.12  # 내레이션 대비 배경음악 크기


def _pick_bgm(seed: str) -> Path | None:
    """assets/bgm 폴더에서 곡 하나를 고른다 (없으면 None → BGM 없이 렌더)."""
    if not BGM_DIR.exists():
        return None
    tracks = sorted(
        p for p in BGM_DIR.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".wav")
    )
    if not tracks:
        return None
    return tracks[sum(ord(c) for c in seed) % len(tracks)]

# 차분하고 세련된 그라데이션 색상 조합 (위, 아래)
PALETTES = [
    ((16, 24, 48), (60, 30, 90)),
    ((10, 35, 45), (20, 90, 100)),
    ((40, 15, 35), (120, 40, 70)),
    ((15, 30, 25), (35, 95, 75)),
    ((25, 25, 30), (80, 60, 30)),
    ((20, 20, 55), (30, 70, 130)),
]


def probe_duration(media_path: Path) -> float:
    ffprobe = str(Path(find_ffmpeg()).parent / "ffprobe.exe")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


# ──────────────────────────── 레이어 프리렌더 ────────────────────────────

def _gradient_base(w: int, h: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)],
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    # 비네트를 베이스에 미리 구움 (프레임당 비용 0)
    vin = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vin)
    vd.ellipse([-int(w * 0.3), -int(h * 0.3), int(w * 1.3), int(h * 1.3)], fill=255)
    vin = vin.filter(ImageFilter.GaussianBlur(min(w, h) // 8))
    black = Image.new("RGB", (w, h), (4, 5, 16))
    return Image.composite(img, black, vin)


def _text_layer(w: int, h: int, text: str, font_size: int, cy: int,
                fill=(255, 255, 255), wrap: int = 0) -> Image.Image:
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(KOREAN_FONT, font_size)
    lines = textwrap.wrap(text, width=wrap)[:4] if wrap else [text]
    line_h = int(font_size * 1.35)
    y0 = cy - (line_h * len(lines)) // 2
    for i, line in enumerate(lines):
        bbox = d.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = y0 + i * line_h
        d.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200))
        d.text((x, y), line, font=font, fill=fill + (255,))
    return layer


def _emoji_sprite(emoji: str, size: int) -> Image.Image:
    """글로우를 깐 이모지 스프라이트 (RGBA). anchor='mm'로 글리프 종류와 무관하게 중앙 정렬."""
    pad = size // 2
    canvas = size + pad * 2
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    glow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([pad // 2, pad // 2, canvas - pad // 2, canvas - pad // 2],
               fill=(255, 230, 160, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(size // 8)))
    try:
        # 변형 선택자(FE0F 등)가 붙으면 PIL 폭 계산이 어긋나므로 제거
        glyph_text = emoji.replace("️", "").replace("‍", "‍")
        font = ImageFont.truetype(EMOJI_FONT, size)
        # 넉넉한 임시 캔버스에 그린 뒤, 실제 픽셀 영역(bbox)을 찾아 재중앙정렬
        tmp = Image.new("RGBA", (canvas * 2, canvas * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((canvas, canvas), glyph_text, font=font,
                                 anchor="mm", embedded_color=True)
        bbox = tmp.getbbox()
        if bbox:
            glyph = tmp.crop(bbox)
            img.paste(glyph, ((canvas - glyph.width) // 2,
                              (canvas - glyph.height) // 2), glyph)
    except Exception:
        pass  # 이모지 렌더 실패 시 글로우만
    return img


def _particle_sprite(r: int) -> Image.Image:
    img = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, r * 2 - 1, r * 2 - 1], fill=(255, 245, 210, 110))
    return img.filter(ImageFilter.GaussianBlur(r // 3))


def _ease_out_back(t: float) -> float:
    """팝인용 이징 (살짝 오버슈트)."""
    c1, c3 = 1.70158, 2.70158
    t -= 1
    return 1 + c3 * t * t * t + c1 * t * t


def _parse_srt_intervals(srt_path: Path) -> list[tuple[float, float]]:
    """SRT에서 (시작, 끝) 초 단위 발화 구간을 뽑는다 → 캐릭터 립싱크용."""
    def ts(s: str) -> float:
        hh, mm, rest = s.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

    intervals = []
    for line in srt_path.read_text(encoding="utf-8").splitlines():
        if "-->" in line:
            a, b = [p.strip() for p in line.split("-->")]
            intervals.append((ts(a), ts(b)))
    return intervals


# ──────────────────────── 마스코트 캐릭터 '호기' ────────────────────────
# 물음표 더듬이가 달린 노란 블롭 캐릭터. 매 프레임 PIL 도형으로 그린다.
# mouth_open: 0(다문 미소)~1(활짝), blink: 눈 감음, wave: 손 흔들기 위상(없으면 None)

CHAR_W, CHAR_H = 420, 540
_BODY = (255, 206, 84)
_BODY_DARK = (225, 165, 40)
_OUTLINE = (92, 62, 18)


MOODS = ("neutral", "surprised", "happy", "thinking")


def _draw_character(t: float, mouth_open: float, blink: bool,
                    wave_phase: float | None, mood: str = "neutral") -> Image.Image:
    img = Image.new("RGBA", (CHAR_W, CHAR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if mood not in MOODS:
        mood = "neutral"

    # 물음표 더듬이 (생각할 땐 더 크게 살랑거림)
    sway = math.sin(t * (4.0 if mood == "thinking" else 2.3)) * (10 if mood == "thinking" else 6)
    d.line([(210, 155), (213 + sway * 0.4, 118), (208 + sway, 95)],
           fill=_OUTLINE, width=11, joint="curve")
    qfont = ImageFont.truetype(KOREAN_FONT, 86)
    qx, qy = 178 + sway, -4
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (2, 2), (-2, 2)):
        d.text((qx + dx, qy + dy), "?", font=qfont, fill=_OUTLINE)
    d.text((qx, qy), "?", font=qfont, fill=(255, 216, 90))

    # 생각 중일 땐 머리 옆에 점점점 말풍선
    if mood == "thinking":
        for i in range(3):
            phase = (t * 1.5 - i * 0.33) % 1.5
            if phase < 1.0:
                r = 8 + i * 4
                a = int(200 * (1 - phase))
                d.ellipse([330 + i * 32 - r, 140 - i * 26 - r,
                           330 + i * 32 + r, 140 - i * 26 + r],
                          fill=(255, 255, 255, a))

    # 놀랐을 땐 머리 주변 강조선
    if mood == "surprised":
        for ang_deg in (-55, -25, 5):
            a = math.radians(ang_deg)
            x1, y1 = 210 + 175 * math.cos(a), 300 + 185 * math.sin(a)
            x2, y2 = 210 + 210 * math.cos(a), 300 + 225 * math.sin(a)
            d.line([(x1, y1), (x2, y2)], fill=(255, 235, 140), width=8)

    # 팔
    d.line([(70, 350), (28, 400 + math.sin(t * 1.9) * 8)],
           fill=_BODY_DARK, width=26, joint="curve")
    if wave_phase is not None:
        wx = 385 + math.sin(wave_phase) * 22
        wy = 250 - abs(math.sin(wave_phase)) * 30
        d.line([(345, 340), (wx, wy)], fill=_BODY_DARK, width=26, joint="curve")
        d.ellipse([wx - 20, wy - 20, wx + 20, wy + 20], fill=_BODY)
    elif mood == "thinking":
        pass  # 생각 포즈의 팔은 몸통 위에 그려야 해서 맨 마지막에 처리
    else:
        d.line([(350, 350), (392, 402 + math.sin(t * 2.1 + 1) * 8)],
               fill=_BODY_DARK, width=26, joint="curve")

    # 발
    d.ellipse([110, 490, 190, 532], fill=_BODY_DARK)
    d.ellipse([230, 490, 310, 532], fill=_BODY_DARK)

    # 몸통 (숨쉬는 스쿼시, 웃을 땐 통통 튀는 느낌)
    squash = math.sin(t * (4.5 if mood == "happy" else 2.0)) * (6 if mood == "happy" else 4)
    d.ellipse([50, 150 + squash, 370, 512], fill=_BODY, outline=_OUTLINE, width=7)
    d.ellipse([95, 200 + squash, 325, 400], fill=(255, 226, 130))  # 하이라이트

    # 눈: 감정별 모양
    ex = -7 + math.sin(t * 0.6) * 4
    if mood == "thinking":
        ex, ey_shift = 10, -14  # 위쪽을 올려다봄
    else:
        ey_shift = 0
    for cx in (150, 270):
        if mood == "happy":
            # 기분 좋게 휘어진 눈웃음 (∩)
            d.arc([cx - 32, 252, cx + 32, 320], start=180, end=360,
                  fill=_OUTLINE, width=10)
        elif blink:
            d.line([(cx - 30, 285), (cx + 30, 285)], fill=_OUTLINE, width=9)
        elif mood == "surprised":
            # 커진 흰자 + 작아진 동공
            d.ellipse([cx - 40, 230, cx + 40, 332], fill=(255, 255, 255),
                      outline=_OUTLINE, width=6)
            d.ellipse([cx - 9 + ex, 272, cx + 9 + ex, 300], fill=(45, 32, 18))
            d.ellipse([cx - 1 + ex, 276, cx + 7 + ex, 286], fill=(255, 255, 255))
        else:
            d.ellipse([cx - 34, 240, cx + 34, 326], fill=(255, 255, 255),
                      outline=_OUTLINE, width=5)
            d.ellipse([cx - 14 + ex, 268 + ey_shift, cx + 14 + ex, 312 + ey_shift],
                      fill=(45, 32, 18))
            d.ellipse([cx - 2 + ex, 274 + ey_shift, cx + 10 + ex, 288 + ey_shift],
                      fill=(255, 255, 255))

    # 눈썹: 놀람(치켜올림) / 생각(한쪽 찌푸림)
    if mood == "surprised":
        d.arc([116, 196, 184, 240], start=200, end=340, fill=_OUTLINE, width=8)
        d.arc([236, 196, 304, 240], start=200, end=340, fill=_OUTLINE, width=8)
    elif mood == "thinking":
        d.line([(118, 226), (182, 214)], fill=_OUTLINE, width=8)
        d.line([(238, 210), (302, 224)], fill=_OUTLINE, width=8)

    # 볼터치 (웃을 땐 진하게)
    cheek_a = 210 if mood == "happy" else 160
    d.ellipse([92, 330, 136, 358], fill=(255, 150, 130, cheek_a))
    d.ellipse([284, 330, 328, 358], fill=(255, 150, 130, cheek_a))

    # 입 (립싱크 + 감정별 기본형)
    mcx, mcy = 210, 385
    if mouth_open < 0.15:
        if mood == "happy":
            d.arc([mcx - 46, mcy - 34, mcx + 46, mcy + 22], start=10, end=170,
                  fill=_OUTLINE, width=9)
        elif mood == "thinking":
            d.line([(mcx - 22, mcy + 2), (mcx + 22, mcy - 6)], fill=_OUTLINE, width=8)
        elif mood == "surprised":
            d.ellipse([mcx - 16, mcy - 18, mcx + 16, mcy + 18],
                      fill=(88, 40, 34), outline=_OUTLINE, width=5)
        else:
            d.arc([mcx - 34, mcy - 26, mcx + 34, mcy + 14], start=15, end=165,
                  fill=_OUTLINE, width=8)
    else:
        mw = 24 if mood == "surprised" else 30  # 놀라면 동그란 입
        mh = int(10 + (46 if mood == "surprised" else 40) * mouth_open)
        d.ellipse([mcx - mw, mcy - mh // 2, mcx + mw, mcy + mh // 2],
                  fill=(88, 40, 34), outline=_OUTLINE, width=5)
        if mouth_open > 0.55 and mood != "surprised":
            d.ellipse([mcx - 16, mcy + mh // 2 - 14, mcx + 16, mcy + mh // 2],
                      fill=(255, 120, 110))

    # 생각 포즈: 턱에 손 괴기 (몸통 위에 보이도록 마지막에 그림)
    if mood == "thinking" and wave_phase is None:
        d.line([(354, 390), (322, 436)], fill=_BODY_DARK, width=26, joint="curve")
        d.ellipse([238, 406, 296, 452], fill=_BODY, outline=_OUTLINE, width=5)
    return img


# ──────────────────────────── 메인 렌더 ────────────────────────────

def render_animated(scenes: list[dict], title: str, mp3_path: Path, srt_path: Path,
                    video_type: str, workdir: Path) -> Path:
    """scenes: [{'emoji': '🎮', 'keyword': '게임의 유혹'}, ...]"""
    cfg = CONFIG[video_type]
    w, h = cfg["width"], cfg["height"]
    is_shorts = video_type == "shorts"
    out_path = workdir / "video.mp4"

    duration = probe_duration(mp3_path) + 0.5
    total_frames = int(duration * FPS)
    n_scenes = max(1, len(scenes))
    scene_frames = total_frames / n_scenes
    fade_frames = min(12, int(scene_frames * 0.15))

    rng = random.Random(title)  # 같은 영상은 같은 연출 (재현 가능)
    palette_order = rng.sample(range(len(PALETTES)), min(n_scenes, len(PALETTES)))

    # 프리렌더: 장면별 배경/이모지/키워드, 공통 타이틀/파티클
    bases, sprites, keywords = [], [], []
    emoji_size = int(w * (0.38 if is_shorts else 0.22))
    for i, sc in enumerate(scenes):
        top, bottom = PALETTES[palette_order[i % len(palette_order)]]
        bases.append(_gradient_base(w, h, top, bottom))
        sprites.append(_emoji_sprite(sc.get("emoji", "💡"), emoji_size))
        keywords.append(_text_layer(
            w, h, sc.get("keyword", ""), int(w * (0.055 if is_shorts else 0.033)),
            int(h * (0.60 if is_shorts else 0.63)), fill=(255, 216, 90)))

    display_title = title.replace("#Shorts", "").strip()
    title_layer = _text_layer(
        w, h, display_title, int(w * (0.062 if is_shorts else 0.04)),
        int(h * (0.13 if is_shorts else 0.10)), wrap=14 if is_shorts else 24)

    p_sprite = _particle_sprite(int(w * 0.012))
    particles = [
        {
            "x0": rng.uniform(0, w),
            "y0": rng.uniform(0, h),
            "speed": rng.uniform(h * 0.02, h * 0.06),  # px/초 (위로)
            "sway": rng.uniform(15, 45),
            "phase": rng.uniform(0, math.tau),
        }
        for _ in range(26 if is_shorts else 34)
    ]

    margin_v = 55 if is_shorts else 40
    style = (
        f"FontName=Malgun Gothic,FontSize={cfg['subtitle_font_size']},Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
        f"Alignment=2,MarginV={margin_v}"
    )
    vf = f"[0:v]subtitles={srt_path.name}:force_style='{style}',format=yuv420p[vout]"
    bgm = _pick_bgm(title)
    cmd = [
        find_ffmpeg(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
        "-i", mp3_path.name,
    ]
    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm)]
        cmd += ["-filter_complex",
                f"{vf};[2:a]volume={BGM_VOLUME}[bg];"
                "[1:a][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                "-map", "[vout]", "-map", "[aout]"]
    else:
        cmd += ["-filter_complex", vf, "-map", "[vout]", "-map", "1:a"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path.name,
    ]
    err_log = open(workdir / "ffmpeg_err.log", "wb")
    proc = subprocess.Popen(cmd, cwd=workdir, stdin=subprocess.PIPE, stderr=err_log)

    ps_w, ps_h = p_sprite.size
    sp_cx, sp_cy = w // 2, int(h * (0.41 if is_shorts else 0.45))

    # 캐릭터 립싱크용 발화 구간 + 배치
    speech = _parse_srt_intervals(srt_path)
    speech_i = 0
    char_h = int(h * (0.24 if is_shorts else 0.33))
    char_w = int(char_h * CHAR_W / CHAR_H)
    char_x = w - char_w - int(w * 0.02)
    char_y0 = h - char_h - int(h * (0.085 if is_shorts else 0.06))
    try:
        for f in range(total_frames):
            t = f / FPS
            idx = min(int(f / scene_frames), n_scenes - 1)
            frame_in_scene = f - int(idx * scene_frames)

            # 배경 (장면 크로스페이드)
            if idx + 1 < n_scenes and frame_in_scene >= scene_frames - fade_frames:
                blend_t = (frame_in_scene - (scene_frames - fade_frames)) / fade_frames
                frame = Image.blend(bases[idx], bases[idx + 1], max(0.0, min(1.0, blend_t)))
            else:
                frame = bases[idx].copy()

            # 파티클 (위로 떠오르며 좌우로 흔들림)
            for p in particles:
                py = (p["y0"] - p["speed"] * t) % (h + ps_h) - ps_h
                px = p["x0"] + p["sway"] * math.sin(p["phase"] + t * 0.8)
                frame.paste(p_sprite, (int(px), int(py)), p_sprite)

            # 이모지: 장면 시작 시 팝인 → 이후 둥실거림 + 은은한 스케일 펄스
            # (단, 첫 장면은 0초부터 완성된 화면 - 쇼츠 피드에 보이는 첫 프레임 최적화)
            if idx == 0:
                pop = 1.0
            else:
                pop = _ease_out_back(min(1.0, frame_in_scene / 10)) if frame_in_scene < 10 else 1.0
            pulse = 1.0 + 0.025 * math.sin(t * 2.1)
            scale = max(0.05, pop * pulse)
            sp = sprites[idx]
            sw, sh = int(sp.width * scale), int(sp.height * scale)
            resized = sp.resize((sw, sh), Image.BILINEAR)
            bob = int(h * 0.008 * math.sin(t * 1.7))
            frame.paste(resized, (sp_cx - sw // 2, sp_cy - sh // 2 + bob), resized)

            # 키워드 + 타이틀
            frame.paste(keywords[idx], (0, 0), keywords[idx])
            frame.paste(title_layer, (0, 0), title_layer)

            # 마스코트 캐릭터 (립싱크 + 눈깜빡임 + 장면 시작 시 손인사)
            while speech_i < len(speech) and t > speech[speech_i][1]:
                speech_i += 1
            speaking = (speech_i < len(speech)
                        and speech[speech_i][0] - 0.05 <= t <= speech[speech_i][1])
            mouth = 0.15 + 0.85 * abs(math.sin(t * 12.0)) if speaking else 0.0
            blink = (t % 3.4) < 0.12
            wave = t * 9 if frame_in_scene < FPS * 1.1 else None
            mood = scenes[idx].get("mood") or (
                "surprised" if idx == 0
                else "happy" if idx == n_scenes - 1
                else "thinking" if idx % 2 else "neutral"
            )
            char = _draw_character(t, mouth, blink, wave, mood).resize(
                (char_w, char_h), Image.BILINEAR)
            char_bob = int(4 * math.sin(t * 2.0))
            frame.paste(char, (char_x, char_y0 + char_bob), char)

            try:
                proc.stdin.write(frame.tobytes())
            except (BrokenPipeError, OSError):
                # -shortest 도달로 ffmpeg가 먼저 정상 종료한 경우
                break
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        proc.wait()
        err_log.close()

    if proc.returncode != 0 or not out_path.exists():
        tail = (workdir / "ffmpeg_err.log").read_text(
            encoding="utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg 애니메이션 렌더링 실패 (code {proc.returncode}):\n{tail}")
    return out_path


# ──────────────────────────── 롱폼 썸네일 ────────────────────────────

def make_thumbnail(title: str, scenes: list[dict], workdir: Path) -> Path:
    """클릭률용 커스텀 썸네일 (1280x720): 큰 제목 + 이모지 + 놀란 호기."""
    w, h = 1280, 720
    rng = random.Random(title)
    top, bottom = rng.choice(PALETTES)
    img = _gradient_base(w, h, top, bottom).convert("RGBA")

    # 오른쪽: 주제 이모지 (위) + 놀란 표정의 호기 (아래)
    emoji = (scenes[0].get("emoji") if scenes else "💡") or "💡"
    sp = _emoji_sprite(emoji, 320)
    img.alpha_composite(sp, (w - sp.width + 40, -40))
    char = _draw_character(0.0, 0.75, False, None, "surprised").resize(
        (380, int(380 * CHAR_H / CHAR_W)), Image.BILINEAR)
    img.alpha_composite(char, (w - 400, h - char.height + 30))

    # 왼쪽: 큰 제목 (흰 글씨 + 두꺼운 검은 외곽선, 핵심 줄은 노란색)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(KOREAN_FONT, 108)
    lines = textwrap.wrap(title.replace("#Shorts", "").strip(), width=9)[:3]
    line_h = 138
    y0 = (h - line_h * len(lines)) // 2 - 20
    for i, line in enumerate(lines):
        fill = (255, 216, 60) if i == len(lines) - 1 else (255, 255, 255)
        d.text((60, y0 + i * line_h), line, font=font, fill=fill,
               stroke_width=10, stroke_fill=(10, 10, 20))

    thumb_path = workdir / "thumbnail.jpg"
    img.convert("RGB").save(thumb_path, quality=90)
    return thumb_path


# ──────────────────────────── 정지화면 폴백 ────────────────────────────

def make_background(title: str, video_type: str, workdir: Path) -> Path:
    cfg = CONFIG[video_type]
    w, h = cfg["width"], cfg["height"]
    top, bottom = random.choice(PALETTES)
    img = _gradient_base(w, h, top, bottom)
    is_shorts = video_type == "shorts"
    layer = _text_layer(w, h, title.replace("#Shorts", "").strip(),
                        int(w * (0.075 if is_shorts else 0.045)),
                        int(h * (0.16 if is_shorts else 0.12)),
                        wrap=12 if is_shorts else 22)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, layer)
    bg_path = workdir / "bg.png"
    img.convert("RGB").save(bg_path)
    return bg_path


def render_video(bg_path: Path, mp3_path: Path, srt_path: Path,
                 video_type: str, workdir: Path) -> Path:
    cfg = CONFIG[video_type]
    out_path = workdir / "video.mp4"
    margin_v = 130 if video_type == "shorts" else 50
    style = (
        f"FontName=Malgun Gothic,FontSize={cfg['subtitle_font_size']},Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
        f"Alignment=2,MarginV={margin_v}"
    )
    cmd = [
        find_ffmpeg(), "-y",
        "-loop", "1", "-framerate", "30", "-i", bg_path.name,
        "-i", mp3_path.name,
        "-vf", f"subtitles={srt_path.name}:force_style='{style}',format=yuv420p",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path.name,
    ]
    result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 렌더링 실패:\n{result.stderr[-3000:]}")
    return out_path
