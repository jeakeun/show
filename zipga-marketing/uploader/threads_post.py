# 쓰레드에 글 하나만 올립니다 (예약 실행용)
#
#   python threads_post.py --file watch/22_시연_모이기.threads.txt
#   python threads_post.py --file ... --dry-run     실제로 안 올리고 확인만
#
# upload.py 는 watch 폴더의 영상을 "전부" 처리하지만,
# 이 스크립트는 지정한 글 하나만 올립니다. 작업 스케줄러가 이걸 부릅니다.
#
# 쓰레드 API 에는 예약 기능이 없습니다. 그래서 이 PC 가 그 시각에 켜져 있어야 합니다.
import argparse
import csv
import datetime
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
LOG = HERE / "uploads_log.csv"
BASE = "https://graph.threads.net/v1.0"
MAX_LEN = 500


def log_result(text_file, result):
    """실제로 올라간 것만 기록합니다 (dry-run 은 기록하지 않습니다)."""
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["시각", "파일", "채널", "결과"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    text_file, "쓰레드", result])


def main():
    ap = argparse.ArgumentParser(description="쓰레드에 글 하나 올리기")
    ap.add_argument("--file", required=True, help="올릴 글이 담긴 txt 파일")
    ap.add_argument("--dry-run", action="store_true", help="올리지 않고 내용만 확인")
    a = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 쓰레드 발행 시작")

    path = Path(a.file)
    if not path.is_absolute():
        path = HERE / path
    if not path.exists():
        print(f"[오류] 글 파일이 없습니다: {path}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        print(f"[오류] 글이 비어 있습니다: {path}")
        sys.exit(1)
    if len(text) > MAX_LEN:
        print(f"[오류] 글이 {len(text)}자입니다. 쓰레드는 {MAX_LEN}자까지만 됩니다")
        sys.exit(1)

    print(f"  파일: {path.name} ({len(text)}자)")
    print("  ---\n" + "\n".join("  " + l for l in text.splitlines()) + "\n  ---")

    if a.dry_run:
        print("  (dry-run — 실제로 올리지 않았습니다)")
        return

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))["threads"]
    token, uid = cfg.get("access_token"), cfg.get("threads_user_id")
    if not (token and uid):
        print("[오류] config.json 의 threads.access_token / threads_user_id 가 비어 있습니다")
        sys.exit(1)

    import requests

    r = requests.post(f"{BASE}/{uid}/threads", timeout=30, data={
        "media_type": "TEXT", "text": text, "access_token": token}).json()
    if "id" not in r:
        print(f"[실패] 초안 생성: {r.get('error', {}).get('message', r)}")
        sys.exit(1)

    time.sleep(3)   # 쓰레드는 초안이 준비될 시간이 필요합니다
    pub = requests.post(f"{BASE}/{uid}/threads_publish", timeout=30, data={
        "creation_id": r["id"], "access_token": token}).json()
    if "id" not in pub:
        print(f"[실패] 발행: {pub.get('error', {}).get('message', pub)}")
        sys.exit(1)

    # 실패해도 재시도하지 않습니다 — 중복 게시가 더 나쁩니다 (CLAUDE.md 원칙 6)
    print(f"[완료] 게시됨 (id {pub['id']})")
    log_result(path.name, f"게시 완료 (id {pub['id']})")


if __name__ == "__main__":
    main()
