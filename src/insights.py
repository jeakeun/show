"""주간 성과 학습: 채널 영상들의 공개 통계를 분석해 플레이북을 갱신한다.

플레이북(data/playbook.md)은 매일 대본 생성 프롬프트에 주입되어,
잘 터진 주제/제목 패턴이 다음 영상들에 반영된다 (자기 학습 루프).

사용법: python -m src.insights   (매주 일요일 저녁 작업 스케줄러가 실행)
"""
import datetime
import json
import sys

import anthropic
from googleapiclient.discovery import build

from .config import (
    ANTHROPIC_API_KEY,
    CONFIG,
    DATA_DIR,
    LOGS_DIR,
    YOUTUBE_API_KEY,
    ensure_dirs,
)

PLAYBOOK_FILE = DATA_DIR / "playbook.md"

ANALYSIS_PROMPT = """당신은 유튜브 채널 성장 전략가입니다. 아래는 지식/호기심 쇼츠 채널
'1분호기심'의 영상별 공개 통계입니다 (최신순):

{stats}

이 데이터에서 패턴을 찾아, 다음 영상 대본을 쓰는 작가에게 줄 "플레이북"을 작성하세요.
데이터가 적으면 적은 대로 조심스럽게 해석하고, 표본 부족을 명시하세요.

플레이북 형식 (마크다운, 전체 800자 이내):
## 잘 통한 것
- (조회수/참여가 좋았던 주제·제목 패턴과 그 이유 추정)
## 피할 것
- (반응이 약했던 패턴)
## 다음 주 실험
- (시도해볼 주제 각도나 제목 스타일 1~2개)

플레이북 텍스트만 출력하세요 (다른 말 금지)."""


def fetch_video_stats() -> list[dict]:
    """채널의 최근 업로드 50개의 공개 통계를 가져온다 (API 키만 사용)."""
    channel_id = CONFIG["channel_url"].rstrip("/").split("/")[-1]
    yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    ch = yt.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = yt.playlistItems().list(
        part="contentDetails", playlistId=uploads_pl, maxResults=50
    ).execute()
    video_ids = [i["contentDetails"]["videoId"] for i in items.get("items", [])]
    if not video_ids:
        return []

    videos = yt.videos().list(
        part="snippet,statistics,contentDetails", id=",".join(video_ids)
    ).execute()

    stats = []
    for v in videos.get("items", []):
        sn, st = v["snippet"], v.get("statistics", {})
        stats.append({
            "title": sn["title"],
            "published": sn["publishedAt"][:10],
            "duration": v["contentDetails"]["duration"],
            "views": int(st.get("viewCount", 0)),
            "likes": int(st.get("likeCount", 0)),
            "comments": int(st.get("commentCount", 0)),
        })
    stats.sort(key=lambda x: x["published"], reverse=True)
    return stats


def update_playbook() -> None:
    ensure_dirs()
    stats = fetch_video_stats()
    if len(stats) < 3:
        print(f"영상이 {len(stats)}개뿐이라 분석을 건너뜁니다 (3개 이상 필요)")
        return

    stats_text = "\n".join(
        f"- [{s['published']}] {s['title']} | 조회 {s['views']:,} · "
        f"좋아요 {s['likes']} · 댓글 {s['comments']} · 길이 {s['duration']}"
        for s in stats
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=CONFIG["model"],
        max_tokens=2000,
        messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(stats=stats_text)}],
    )
    playbook = "".join(b.text for b in msg.content if b.type == "text").strip()

    today = datetime.date.today().isoformat()
    PLAYBOOK_FILE.write_text(
        f"(마지막 분석: {today}, 영상 {len(stats)}개 기준)\n\n{playbook}",
        encoding="utf-8",
    )
    # 분석 이력도 남겨둠
    (DATA_DIR / "stats_history.jsonl").open("a", encoding="utf-8").write(
        json.dumps({"date": today, "stats": stats}, ensure_ascii=False) + "\n"
    )
    print(f"플레이북 갱신 완료 ({len(stats)}개 영상 분석)")
    print(playbook)


if __name__ == "__main__":
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        update_playbook()
    except Exception as e:
        print(f"실패: {e}", file=sys.stderr)
        sys.exit(1)
