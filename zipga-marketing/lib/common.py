# 공용 유틸 — 모든 모듈이 여기 있는 함수만으로 파일을 읽고 씁니다.
# CSV는 utf-8-sig 로 저장해서 엑셀에서 바로 열어도 한글이 깨지지 않게 합니다.
import csv
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INBOX = ROOT / "inbox"
EXPORT = ROOT / "export"


def ensure_dirs():
    for d in [
        INBOX,
        DATA / "raw",
        DATA / "transcript",
        DATA / "clips",
        DATA / "samples",
        EXPORT,
    ]:
        d.mkdir(parents=True, exist_ok=True)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_config():
    return load_json(ROOT / "config.json")


def load_account(account_id):
    path = ROOT / "accounts" / f"{account_id}.json"
    if not path.exists():
        raise SystemExit(
            f"[오류] 계정 설정이 없습니다: accounts/{account_id}.json\n"
            f"       accounts/_template.json 을 복사해서 만드세요."
        )
    return load_json(path)


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_csv(path, row, fieldnames):
    path = Path(path)
    exists = path.exists()
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)


def has_cmd(name):
    return shutil.which(name) is not None


def run_cmd(args):
    """외부 명령 실행. 성공하면 stdout, 실패하면 None."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            return None
        return p.stdout
    except FileNotFoundError:
        return None


def info(tag, msg):
    print(f"  [{tag}] {msg}")


def warn(tag, msg):
    print(f"  [{tag}][경고] {msg}")
