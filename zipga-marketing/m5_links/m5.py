# M5 링크·측정 — 채널×형식별 Play 스토어 referrer 링크 생성 → data/links.csv
# 규칙: referrer 안의 utm 은 URL 인코딩 1번만, 전부 소문자 (마케팅 플랜 5장 체크리스트와 동일)
# 주간 지표 수집(구글 시트 append + 깃허브 액션)은 다음 단계 — 아래 TODO 참고.
import datetime
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, info, load_config, read_csv, write_csv

TAG = "M5"
LINKS = DATA / "links.csv"
LINKS_FIELDS = ["account", "channel", "format", "os", "url", "campaign_id"]


def build_link(package, account_id, channel, fmt, campaign):
    utm = f"utm_source={account_id}&utm_medium={channel}_{fmt}&utm_campaign={campaign}".lower()
    referrer = urllib.parse.quote(utm, safe="")  # 인코딩은 딱 한 번
    return f"https://play.google.com/store/apps/details?id={package}&referrer={referrer}"


def run(account_id="a"):
    cfg = load_config()
    package = cfg["play_package"]
    campaign = cfg["campaign"]
    if package.startswith("com.example"):
        info(TAG, f"패키지명이 아직 예시값({package})입니다 — 출시 전 config.json 에서 바꾸세요")

    old = [r for r in read_csv(LINKS) if r.get("account") != account_id]
    rows = []
    for channel in cfg["channels"]:
        for fmt in cfg["formats"]:
            rows.append({
                "account": account_id, "channel": channel, "format": fmt, "os": "android",
                "url": build_link(package, account_id, channel, fmt, campaign),
                "campaign_id": f"{campaign}_{account_id}_{channel}_{fmt}",
            })
    write_csv(LINKS, old + rows, LINKS_FIELDS)
    info(TAG, f"완료 — 계정 '{account_id}' 링크 {len(rows)}개 생성, data/links.csv 갱신")
    # TODO(M5 담당): 주 1회 플랫폼 인사이트 → 구글 시트 append + 실패 시 깃허브 이슈 자동 생성
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    run(sys.argv[1] if len(sys.argv) > 1 else "a")
