# -*- coding: utf-8 -*-
"""웹드라마 반자동 공용: 경로·설정·비밀키·ffmpeg·폰 알림."""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERIES_DIR = ROOT / "series"
EPISODES_DIR = ROOT / "episodes"
SECRETS_DIR = ROOT / "secrets"
CONFIG_PATH = ROOT / "config.json"
BIBLE_PATH = SERIES_DIR / "bible.json"
STATE_PATH = SERIES_DIR / "state.json"

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)


def setup_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env() -> None:
    """ANTHROPIC_API_KEY: webdrama/secrets/.env 우선, 없으면 yt-auto 의 .env 를 같이 쓴다."""
    from dotenv import load_dotenv
    for p in (SECRETS_DIR / ".env", Path(CONFIG.get("fallback_env", ""))):
        if p and p.is_file():
            load_dotenv(p, encoding="utf-8-sig")
            if os.getenv("ANTHROPIC_API_KEY"):
                return


def read_json(path: Path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def write_json(path: Path, data) -> None:
    """임시 파일에 쓴 뒤 바꿔 끼운다 (쓰다 끊겨도 반쯤 쓴 파일이 남지 않게)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_bible() -> dict:
    bible = read_json(BIBLE_PATH)
    if not bible:
        raise SystemExit("시리즈 설정(series/bible.json)이 없습니다. 먼저 0_시리즈만들기.bat 을 실행하세요.")
    return bible


def ep_dir(n: int) -> Path:
    return EPISODES_DIR / f"ep{n:03d}"


def episode_numbers() -> list[int]:
    if not EPISODES_DIR.exists():
        return []
    return sorted(int(p.name[2:]) for p in EPISODES_DIR.glob("ep[0-9][0-9][0-9]") if (p / "script.json").exists())


def load_status(n: int) -> dict:
    return read_json(ep_dir(n) / "status.json", {})


def save_status(n: int, status: dict) -> None:
    write_json(ep_dir(n) / "status.json", status)


def find_bin(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    hits = list(base.glob(f"Gyan.FFmpeg*/**/bin/{name}.exe"))
    if hits:
        return str(hits[0])
    raise SystemExit(f"{name} 를 찾을 수 없습니다. 'winget install Gyan.FFmpeg' 로 설치하세요.")


def notify(title: str, message: str) -> None:
    """D:\\notify 의 폰 푸시. 없거나 실패해도 조용히 넘어간다."""
    try:
        sys.path.insert(0, CONFIG.get("notify_dir", r"D:\notify"))
        from push import push
        push(title, message)
    except Exception:
        pass
