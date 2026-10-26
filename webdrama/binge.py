# -*- coding: utf-8 -*-
"""몰아보기 롱폼: 이미 쇼츠로 올린 회차를 10화씩 이어 붙여 유튜브 롱폼으로 올린다.

왜: 쇼츠는 조회수당 수익이 롱폼의 약 1/10이고, 수익 창출 조건도 쇼츠는 90일 1,000만 회,
롱폼은 1년 4,000시간이다. 10화 묶음(회당 길이에 따라 약 10~15분)은 롱폼 시청 시간을 쌓고, 8분이 넘으면 중간 광고도 붙는다.

- 묶음: 1~10화, 11~20화 … (config binge.every) + 시즌 전체 1~30화 (binge.season_full)
- 차례: 묶음의 마지막 회차가 유튜브에 올라간 **다음 업로드 날**. 하루에 몰아보기는 한 편만.
- 화면: landscape = 가로 16:9 (가운데 세로 영상 + 흐린 배경, TV·PC 시청용), vertical = 세로 그대로
- 업로드 실패는 자동 재시도하지 않는다 (중복 게시 방지). 다시: python drama.py binge 1-10 --force
"""
import os
import shutil
import tempfile
from pathlib import Path

from common import CONFIG, ROOT, STATE_PATH, ep_dir, episode_numbers, find_bin, load_status, read_json
from editor import _ass_text, _probe, _run, clip_path

BINGES_DIR = ROOT / "binges"
LW, LH = 1920, 1080   # 가로 화면
TW, TH = 1280, 720    # 썸네일


def cfg() -> dict:
    c = {"enabled": True, "every": 10, "season_full": True, "layout": "landscape"}
    c.update(CONFIG.get("binge", {}))
    c["every"] = max(2, int(c["every"]))
    return c


def key(a: int, b: int) -> str:
    return f"{a}-{b}"


def parse_range(s: str) -> tuple[int, int]:
    try:
        a, b = (int(x) for x in s.replace("~", "-").split("-"))
    except ValueError:
        raise SystemExit(f"범위는 1-10 처럼 적어 주세요: {s}")
    if not 1 <= a < b:
        raise SystemExit(f"범위가 이상합니다: {s}")
    return a, b


def candidates(last: int) -> list[tuple[int, int]]:
    """last 화까지 있을 때 만들 수 있는 묶음. 작은 묶음 먼저 (21~30화 → 1~30화 순)."""
    c = cfg()
    every = c["every"]
    out = [(k - every + 1, k) for k in range(every, last + 1, every)]
    season = int(CONFIG.get("season_episodes", 30))
    if c["season_full"] and season > every and last >= season and (1, season) not in out:
        out.append((1, season))
    return sorted(out, key=lambda r: (r[1], r[1] - r[0]))


def _yt(n: int) -> dict:
    return load_status(n).get("published", {}).get("youtube", {})


def due(today: str) -> tuple[int, int] | None:
    """지금 올릴 묶음. 모든 회차가 유튜브에 올라갔고, 마지막 회차가 오늘보다 전에 올라간 것."""
    nums = set(episode_numbers())
    done = read_json(STATE_PATH, {}).get("binges", {})
    for a, b in candidates(max(nums, default=0)):
        if key(a, b) in done:          # 성공했거나, 실패해서 사람이 다시 올리기로 한 것
            continue
        if not all(k in nums and _yt(k).get("ok") for k in range(a, b + 1)):
            continue
        if _yt(b).get("at", "")[:10] >= today:
            continue                    # 마지막 회차를 오늘 올렸으면 다음 업로드 날에
        return a, b
    return None


def blocked() -> list[tuple[int, int, list[int]]]:
    """회차는 다 올라갔는데(published_done) 유튜브 기록이 없는 회차 때문에 영영 안 올라갈 묶음."""
    nums = set(episode_numbers())
    done = read_json(STATE_PATH, {}).get("binges", {})
    out = []
    for a, b in candidates(max(nums, default=0)):
        eps = range(a, b + 1)
        if key(a, b) in done or not all(k in nums and load_status(k).get("published_done") for k in eps):
            continue
        missing = [k for k in eps if not _yt(k).get("ok")]
        if missing:
            out.append((a, b, missing))
    return out


def next_preview() -> tuple[int, int] | None:
    """미리보기용: 아직 안 올린 묶음 중 모든 회차가 편집까지 끝난 첫 묶음."""
    nums = set(episode_numbers())
    done = read_json(STATE_PATH, {}).get("binges", {})
    for a, b in candidates(max(nums, default=0)):
        if not done.get(key(a, b), {}).get("ok") and all(k in nums and load_status(k).get("built")
                                                        for k in range(a, b + 1)):
            return a, b
    return None


def _stamp(sec: float) -> str:
    s = int(sec)
    h, m = divmod(s // 60, 60)
    return f"{h}:{m:02d}:{s % 60:02d}" if h else f"{m}:{s % 60:02d}"


# ---------- 만들기 ----------

def _thumb_ass(series: str, a: int, b: int) -> str:
    font = CONFIG.get("subtitle_font", "Malgun Gothic")
    right = TW - 760   # 오른쪽은 세로 영상 자리
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {TW}
PlayResY: {TH}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Series,{font},50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,7,60,{right},70,1
Style: Big,{font},130,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,8,0,4,60,{right},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,Series,,0,0,0,,{_ass_text(series)}
Dialogue: 0,0:00:00.00,0:00:10.00,Big,,0,0,0,,{{\\c&H00D7FF&}}{a}~{b}화\\N{{\\c&HFFFFFF&}}몰아보기
"""


def _thumbnail(work: Path, out: Path, series: str, a: int, b: int, last_final: Path) -> Path | None:
    """마지막 회차의 끊는 장면(자막 없는 원본 장면이 있으면 그것)에서 한 장 뽑아 1280×720 썸네일."""
    ffmpeg = find_bin("ffmpeg")
    script = read_json(ep_dir(b) / "script.json", {})
    raw = clip_path(ep_dir(b), len(script.get("shots", [])) or 1)
    src = raw if raw.exists() else last_final
    dur = _probe(src)[0]
    at = dur / 2 if src == raw else max(dur - 4.0, 0)
    frame = work / "frame.png"
    _run([ffmpeg, "-y", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1", str(frame)])
    (work / "thumb.ass").write_text(_thumb_ass(series, a, b), encoding="utf-8")
    fc = (f"[0:v]split=2[x][y];"
          f"[x]scale={TW}:{TH}:force_original_aspect_ratio=increase,crop={TW}:{TH},boxblur=20:2,"
          f"eq=brightness=-0.28[bg];[y]scale=-2:{TH}[fg];[bg][fg]overlay=W-w-50:0,subtitles=thumb.ass[v]")
    _run([ffmpeg, "-y", "-i", "frame.png", "-filter_complex", fc, "-map", "[v]", "-frames:v", "1",
          "-q:v", "3", out.name], cwd=work)
    os.replace(work / out.name, out)
    return out


def chapters(a: int, b: int) -> list[tuple[float, int, str]]:
    """회차별 시작 시각 (시작초, 화, 부제). 완성본이 하나라도 없으면 멈춘다."""
    out, t = [], 0.0
    for n in range(a, b + 1):
        f = ep_dir(n) / "final.mp4"
        if not f.exists():
            raise SystemExit(f"{n}화 완성본(final.mp4)이 없습니다. 지웠다면 python drama.py build {n} 로 다시 만드세요.")
        out.append((t, n, read_json(ep_dir(n) / "script.json")["title"]))
        t += _probe(f)[0]
    return out


def build(a: int, b: int, series: str) -> dict:
    """a~b화 final.mp4 를 이어 붙인다. 반환: path, seconds, chapters, thumb, thumb_error"""
    ffmpeg = find_bin("ffmpeg")
    chaps = chapters(a, b)
    parts = [ep_dir(n) / "final.mp4" for n in range(a, b + 1)]

    folder = BINGES_DIR / f"ep{a:03d}-{b:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="_work", dir=folder))  # 미리보기와 자동 실행이 겹쳐도 안 섞이게
    (work / "list.txt").write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    out = folder / "binge.mp4"
    args = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt"]
    if cfg()["layout"] == "vertical":
        args += ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy"]
    else:
        # 세로 영상(W×H)을 가운데에, 같은 영상을 흐리게 키워 양옆 배경으로 (작게 줄여 흐린 뒤 키워서 빠르게)
        bw, bh = LW // 4, LH // 4
        fc = (f"[0:v]split=2[x][y];"
              f"[x]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},boxblur=8:1,"
              f"scale={LW}:{LH},eq=brightness=-0.12,setsar=1[bg];"
              f"[y]scale=-2:{LH},setsar=1[fg];[bg][fg]overlay=(W-w)/2:0,format=yuv420p[v]")
        args += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-r", "30"]
    args += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "binge.mp4"]
    _run(args, cwd=work)
    os.replace(work / "binge.mp4", out)  # 미리보기로 열어 둔 파일이면 여기서 실패 → 알림

    thumb, thumb_error = None, ""
    try:
        thumb = _thumbnail(work, folder / "thumb.jpg", series, a, b, parts[-1])
    except (Exception, SystemExit) as e:   # 썸네일은 없어도 올린다
        thumb_error = str(e)[-300:]
    shutil.rmtree(work, ignore_errors=True)
    return {"path": out, "seconds": _probe(out)[0], "chapters": chaps, "thumb": thumb,
            "thumb_error": thumb_error}


# ---------- 업로드 문구 ----------

def texts(bible: dict, a: int, b: int, chapters: list, shorts_playlist: str = "") -> dict:
    season = int(CONFIG.get("season_episodes", 30))
    whole = a == 1 and b >= season
    title = f"[{bible['title']}] {a}~{b}화 몰아보기" + (" | 전편 정주행" if whole else "")
    lines = [bible["logline"], ""]
    if shorts_playlist:
        lines += [f"▶ 회차별로 보기: https://www.youtube.com/playlist?list={shorts_playlist}", ""]
    lines += [f"{_stamp(s)} {n}화 · {t}" for s, n, t in chapters]  # 0:00 부터 3개 이상이면 유튜브 챕터가 됨
    tags = list(dict.fromkeys(bible.get("hashtags", []) + ["#몰아보기", "#정주행", "#숏드라마", "#드라마몰아보기"]))
    tag_line = " ".join(x if x.startswith("#") else f"#{x}" for x in tags)
    from publisher import AI_NOTICE
    lines += ["", tag_line, "", AI_NOTICE]
    return {"title": title[:100], "description": "\n".join(lines),
            "tags": [x.lstrip("#") for x in tags][:20]}

