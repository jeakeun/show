"""공용 설정 로더: config.json + secrets/.env 를 읽어 전역 설정을 제공한다."""
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = ROOT / "secrets"
OUTPUT_DIR = ROOT / "output"
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

load_dotenv(SECRETS_DIR / ".env")

with open(ROOT / "config.json", encoding="utf-8") as f:
    CONFIG = json.load(f)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

CLIENT_SECRET_FILE = SECRETS_DIR / "client_secret.json"
TOKEN_FILE = SECRETS_DIR / "token.json"

USED_TOPICS_FILE = DATA_DIR / "used_topics.json"

KOREAN_FONT = r"C:\Windows\Fonts\malgunbd.ttf"
if not Path(KOREAN_FONT).exists():
    KOREAN_FONT = r"C:\Windows\Fonts\malgun.ttf"


def find_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p:
        return p
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    hits = list(base.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"))
    if hits:
        return str(hits[0])
    raise RuntimeError(
        "ffmpeg를 찾을 수 없습니다. 'winget install Gyan.FFmpeg' 로 설치하세요."
    )


def ensure_dirs() -> None:
    for d in (SECRETS_DIR, OUTPUT_DIR, LOGS_DIR, DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_used_topics() -> list:
    if USED_TOPICS_FILE.exists():
        return json.loads(USED_TOPICS_FILE.read_text(encoding="utf-8"))
    return []


def save_used_topic(topic: str) -> None:
    topics = load_used_topics()
    topics.append(topic)
    USED_TOPICS_FILE.write_text(
        json.dumps(topics[-200:], ensure_ascii=False, indent=2), encoding="utf-8"
    )
