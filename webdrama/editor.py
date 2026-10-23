# -*- coding: utf-8 -*-
"""다운로드한 장면 영상을 회차 폴더로 가져오고, 한 편으로 편집한다 (ffmpeg)."""
import datetime
import json
import random
import shutil
import subprocess
from pathlib import Path

from common import CONFIG, find_bin

VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}
W, H = 1080, 1920


# ---------- 가져오기 ----------

def downloads_dir() -> Path:
    d = CONFIG.get("downloads_dir") or str(Path.home() / "Downloads")
    return Path(d)


def clip_path(folder: Path, i: int) -> Path:
    return folder / "clips" / f"{i:02d}.mp4"


def collect(folder: Path, ep: dict, since: float, shot: int | None = None) -> list[str]:
    """다운로드 폴더에서 since 이후 받은 영상을 받은 순서대로 빈 장면에 채운다.
    shot 을 주면 가장 최근 영상 하나로 그 장면만 교체한다."""
    (folder / "clips").mkdir(exist_ok=True)
    new = sorted((p for p in downloads_dir().iterdir()
                  if p.suffix.lower() in VIDEO_EXT and p.stat().st_mtime > since),
                 key=lambda p: p.stat().st_mtime)
    if not new:
        return []
    moves = []
    if shot:
        moves.append((new[-1], shot))
    else:
        empty = [i for i in range(1, len(ep["shots"]) + 1) if not clip_path(folder, i).exists()]
        moves = list(zip(new, empty))
    done = []
    for src, i in moves:
        dst = clip_path(folder, i)
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), dst)
        done.append(f"{i}번 장면 ← {src.name}")
    return done


# ---------- 편집 ----------

def _run(args: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg 오류:\n" + r.stderr[-1500:])


def _probe(path: Path) -> tuple[float, bool]:
    r = subprocess.run([find_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                        "-of", "json", str(path)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    dur = float(j.get("format", {}).get("duration", 0))
    has_audio = any(s.get("codec_type") == "audio" for s in j.get("streams", []))
    return dur, has_audio


def _t(sec: float) -> str:
    h, rem = divmod(max(sec, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ass_text(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def _subtitles(ep: dict, n: int, starts: list[float], durs: list[float], total: float) -> str:
    font = CONFIG.get("subtitle_font", "Malgun Gothic")
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,5,0,2,90,90,560,1
Style: Title,{font},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,3,14,0,8,80,80,260,1
Style: End,{font},72,&H0000D7FF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,3,16,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 1,{_t(0)},{_t(2.5)},Title,,0,0,0,,{_ass_text(f'{n}화 · ' + ep['title'])}"]
    for shot, st, du in zip(ep["shots"], starts, durs):
        lines = [d["line"] for d in shot["dialogue"] if d["line"].strip()]
        if not lines:
            continue
        weights = [max(len(l), 4) for l in lines]
        t = st + 0.15
        span = du - 0.3
        for line, w in zip(lines, weights):
            d = span * w / sum(weights)
            ev.append(f"Dialogue: 0,{_t(t)},{_t(t + d)},Sub,,0,0,0,,{_ass_text(line)}")
            t += d
    ending = CONFIG.get("ending_text", "")
    if ending:
        ev.append(f"Dialogue: 2,{_t(total - 2.0)},{_t(total)},End,,0,0,0,,{_ass_text(ending)}")
    return head + "\n".join(ev) + "\n"


def _pick_bgm() -> Path | None:
    d = Path(CONFIG.get("bgm_dir", ""))
    if not CONFIG.get("bgm_volume") or not d.is_dir():
        return None
    files = [p for p in d.iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".wav"}]
    return random.choice(files) if files else None


def build(folder: Path, ep: dict, n: int) -> tuple[Path, float, str]:
    ffmpeg = find_bin("ffmpeg")
    count = len(ep["shots"])
    missing = [i for i in range(1, count + 1) if not clip_path(folder, i).exists()]
    if missing:
        raise SystemExit(f"아직 없는 장면: {', '.join(map(str, missing))}번. 힉스필드에서 받은 뒤 2_영상가져오기.bat 을 실행하세요.")

    work = folder / "_work"
    work.mkdir(exist_ok=True)
    durs, parts = [], []
    for i in range(1, count + 1):
        src = clip_path(folder, i)
        dur, has_audio = _probe(src)
        out = work / f"n{i:02d}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps=30,setsar=1,format=yuv420p")
        args = [ffmpeg, "-y", "-i", str(src)]
        if not has_audio:
            args += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        args += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0", "-vf", vf,
                 "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(out)]
        _run(args)
        durs.append(_probe(out)[0])
        parts.append(out)

    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = work / "joined.mp4"
    _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=work)

    total = sum(durs)
    starts = [sum(durs[:i]) for i in range(count)]
    (work / "subs.ass").write_text(_subtitles(ep, n, starts, durs, total), encoding="utf-8")

    final = folder / "final.mp4"
    bgm = _pick_bgm()
    args = [ffmpeg, "-y", "-i", "joined.mp4"]
    if bgm:
        args += ["-stream_loop", "-1", "-i", str(bgm)]
        fa = (f"[1:a]volume={CONFIG['bgm_volume']}[b];[0:a][b]amix=inputs=2:duration=first:"
              f"dropout_transition=0:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        fa = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    args += ["-filter_complex", f"[0:v]subtitles=subs.ass[v];{fa}", "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
             "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", str(final)]
    _run(args, cwd=work)
    shutil.rmtree(work, ignore_errors=True)
    return final, total, (bgm.name if bgm else "")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")
