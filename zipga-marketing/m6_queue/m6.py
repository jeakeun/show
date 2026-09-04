# M6 발행 큐 — manifest + texts + links 를 합쳐 "이 클립 + 이 문구 + 이 링크를 언제 어디에" 한 줄로
# status 는 draft → ready → published 순서로만 바뀌고, published 는 절대 다시 내보내지 않습니다.
# --export : status 가 ready 인 항목을 export/{날짜}/{platform}/ 폴더에 영상 + caption.txt 로 묶어 내보냄
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, EXPORT, info, load_config, read_csv, warn, write_csv

TAG = "M6"
QUEUE = DATA / "queue.csv"
QUEUE_FIELDS = ["clip_id", "platform", "account", "publish_at", "body", "link", "status"]
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _next_slots(slots, count):
    """설정된 요일·시간 슬롯으로 앞으로의 발행 시각을 count개 만듦."""
    out, day = [], datetime.date.today() + datetime.timedelta(days=1)
    while len(out) < count:
        for wd, hhmm in slots:
            if day.weekday() == WEEKDAYS[wd.lower()]:
                out.append(f"{day.isoformat()} {hhmm}")
        day += datetime.timedelta(days=1)
    return out[:count]


def run(account_id="a"):
    cfg = load_config()
    manifest = read_csv(DATA / "clips" / "manifest.csv")
    texts = [r for r in read_csv(DATA / "texts.csv") if r["account"] == account_id]
    links = {(r["channel"]): r["url"] for r in read_csv(DATA / "links.csv")
             if r["account"] == account_id and r["format"] in ("reels", "shorts", "bio")}
    if not (manifest and texts and links):
        warn(TAG, "manifest / texts / links 중 빠진 게 있습니다. M3~M5를 먼저 실행하세요.")
        return False

    # 클립·플랫폼별 최신 버전 문구만 사용
    latest = {}
    for t in texts:
        key = (t["clip_id"], t["platform"])
        if key not in latest or int(t["version"]) > int(latest[key]["version"]):
            latest[key] = t

    existing = read_csv(QUEUE)
    keep = [r for r in existing if r["account"] != account_id or r["status"] == "published"]
    frozen = {(r["clip_id"], r["platform"]) for r in keep if r["account"] == account_id}

    new_rows = []
    for clip in manifest:
        for platform in cfg["channels"]:
            key = (clip["clip_id"], platform)
            if key in frozen:
                continue  # published 는 손대지 않음
            t = latest.get(key)
            if not t:
                continue
            new_rows.append({
                "clip_id": clip["clip_id"], "platform": platform, "account": account_id,
                "publish_at": "", "body": (t["body"] + "\n" + t["hashtags"]).strip(),
                "link": links.get(platform, ""), "status": "draft",
            })

    for row, slot in zip(new_rows, _next_slots(cfg["publish_slots"], len(new_rows))):
        row["publish_at"] = slot

    seen = set()
    for r in new_rows:
        k = (r["publish_at"][:10], r["platform"], r["account"])
        if k in seen:
            warn(TAG, f"같은 날 같은 플랫폼에 2개 이상 배정: {k}")
        seen.add(k)

    write_csv(QUEUE, keep + new_rows, QUEUE_FIELDS)
    info(TAG, f"완료 — 계정 '{account_id}' 큐 {len(new_rows)}건, data/queue.csv 갱신 (전부 draft)")
    info(TAG, "올릴 것을 골라 queue.csv 의 status 를 ready 로 바꾼 뒤 --export 하세요")
    return True


def export():
    rows = read_csv(QUEUE)
    ready = [r for r in rows if r["status"] == "ready"]
    if not ready:
        warn(TAG, "status 가 ready 인 항목이 없습니다. queue.csv 에서 ready 로 바꿔주세요.")
        return False
    today = datetime.date.today().isoformat()
    for r in ready:
        dst = EXPORT / today / r["platform"]
        dst.mkdir(parents=True, exist_ok=True)
        clip = DATA / "clips" / f"{r['clip_id']}.mp4"
        if clip.exists():
            shutil.copy2(clip, dst / clip.name)
        caption = (dst / f"{r['clip_id']}_caption.txt")
        caption.write_text(f"{r['body']}\n\n링크: {r['link']}\n예약: {r['publish_at']}\n", encoding="utf-8")
    info(TAG, f"내보내기 완료 — export/{today}/ 에 {len(ready)}건 (발행 담당은 이 폴더만 열면 됩니다)")
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    if "--export" in sys.argv:
        export()
    else:
        run(sys.argv[1] if len(sys.argv) > 1 else "a")
