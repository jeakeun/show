"""매일 유튜브 인기 급상승 영상을 수집해 '지금 사람들이 관심 갖는 주제' 데이터를 만든다.

주의: 남의 영상 콘텐츠를 가져오는 것이 아니라, 제목/태그/카테고리 같은
공개 메타데이터만 분석해 오리지널 영상의 주제 선정에 활용한다.
"""
import json
from pathlib import Path

from googleapiclient.discovery import build

from .config import CONFIG, YOUTUBE_API_KEY


def collect_trends(max_results: int = 50) -> list[dict]:
    """인기 급상승 영상 메타데이터 목록을 반환한다."""
    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY가 없습니다. secrets/.env 에 추가하세요. (README 참고)"
        )
    yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    resp = (
        yt.videos()
        .list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=CONFIG["region"],
            maxResults=max_results,
        )
        .execute()
    )
    items = []
    for v in resp.get("items", []):
        sn = v.get("snippet", {})
        st = v.get("statistics", {})
        items.append(
            {
                "title": sn.get("title", ""),
                "channel": sn.get("channelTitle", ""),
                "category_id": sn.get("categoryId", ""),
                "tags": sn.get("tags", [])[:8],
                "views": int(st.get("viewCount", 0)),
            }
        )
    items.sort(key=lambda x: x["views"], reverse=True)
    return items


def save_trends(items: list[dict], workdir: Path) -> Path:
    out = workdir / "trends.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
