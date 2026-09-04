"""전체 파이프라인 오케스트레이터.

사용법:
  python -m src.pipeline                 # auto: 매일 쇼츠, 지정 요일엔 롱폼도
  python -m src.pipeline --type shorts   # 쇼츠 1편
  python -m src.pipeline --type longform # 롱폼 1편
  python -m src.pipeline --no-upload     # 업로드 없이 영상 제작까지만 (테스트용)
"""
import argparse
import datetime
import json
import logging
import sys
import traceback

from . import config
from .scriptgen import generate_script
from .trends import collect_trends, save_trends
from .tts import make_narration
from .uploader import upload_video
from .video import make_background, make_thumbnail, render_animated, render_video

log = logging.getLogger("pipeline")


def setup_logging(date_str: str) -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(
                config.LOGS_DIR / f"{date_str}.log", encoding="utf-8"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_one(video_type: str, trend_items: list[dict], upload: bool,
            companion: dict | None = None, tag: str = "") -> tuple[dict, str | None]:
    date_str = datetime.date.today().isoformat()
    folder = video_type + (f"_{tag}" if tag else "")
    workdir = config.OUTPUT_DIR / date_str / folder
    workdir.mkdir(parents=True, exist_ok=True)

    save_trends(trend_items, workdir)

    log.info("[%s] 대본 생성 중...", video_type)
    meta = generate_script(trend_items, video_type, companion=companion)
    if companion and companion.get("video_id"):
        meta["description"] = (
            meta["description"].rstrip()
            + f"\n\n▶ 이 이야기의 풀버전: https://youtu.be/{companion['video_id']}"
        )
    (workdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("[%s] 주제: %s / 제목: %s", video_type, meta["topic"], meta["title"])

    log.info("[%s] TTS 내레이션 + 자막 생성 중...", video_type)
    mp3_path, srt_path = make_narration(meta["script"], video_type, workdir)

    log.info("[%s] 영상 렌더링 중...", video_type)
    scenes = meta.get("scenes") or [{"emoji": "💡", "keyword": meta["topic"][:20]}]
    try:
        video_path = render_animated(
            scenes, meta["title"], mp3_path, srt_path, video_type, workdir
        )
    except Exception:
        log.warning(
            "[%s] 애니메이션 렌더 실패 → 정지 배경 폴백:\n%s",
            video_type, traceback.format_exc(),
        )
        bg_path = make_background(meta["title"], video_type, workdir)
        video_path = render_video(bg_path, mp3_path, srt_path, video_type, workdir)
    log.info("[%s] 렌더링 완료: %s", video_type, video_path)

    thumbnail = None
    if video_type == "longform":
        try:
            thumb_title = meta.get("thumbnail_title") or meta["title"]
            thumbnail = make_thumbnail(thumb_title, meta.get("scenes") or [], workdir)
            log.info("[%s] 썸네일 생성 완료", video_type)
        except Exception:
            log.warning("[%s] 썸네일 생성 실패 (무시):\n%s",
                        video_type, traceback.format_exc())

    video_id = None
    if upload:
        log.info("[%s] 유튜브 업로드 중...", video_type)
        video_id = upload_video(video_path, meta, thumbnail=thumbnail)
        log.info("[%s] 업로드 완료: https://youtu.be/%s", video_type, video_id)
    else:
        log.info("[%s] 업로드 생략 (--no-upload)", video_type)

    config.save_used_topic(meta["topic"])
    return meta, video_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type", choices=["auto", "shorts", "longform"], default="auto"
    )
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--tag", default="", help="같은 날 2회차 실행 시 폴더 구분용 (예: pm)")
    args = parser.parse_args()

    today = datetime.date.today()
    setup_logging(today.isoformat())
    config.ensure_dirs()

    longform_day = today.weekday() in config.CONFIG.get("longform_weekdays", [6])
    upload = not args.no_upload

    log.info("=== 파이프라인 시작: %s (롱폼 날: %s) ===", today, longform_day)

    try:
        trend_items = collect_trends()
        log.info("트렌드 %d건 수집 완료", len(trend_items))
    except Exception:
        log.error("트렌드 수집 실패:\n%s", traceback.format_exc())
        return 1

    failed = False
    if args.type in ("longform", "shorts"):
        try:
            run_one(args.type, trend_items, upload, tag=args.tag)
        except Exception:
            failed = True
            log.error("[%s] 실패:\n%s", args.type, traceback.format_exc())
    else:
        # auto: 롱폼 날엔 롱폼 먼저 → 쇼츠는 그 롱폼의 예고편으로 (설명란에 링크)
        companion = None
        if longform_day:
            try:
                lf_meta, lf_id = run_one("longform", trend_items, upload)
                companion = {
                    "topic": lf_meta["topic"],
                    "title": lf_meta["title"],
                    "video_id": lf_id,
                }
            except Exception:
                failed = True
                log.error("[longform] 실패 (쇼츠는 일반 모드로 진행):\n%s",
                          traceback.format_exc())
        try:
            run_one("shorts", trend_items, upload, companion=companion)
        except Exception:
            failed = True
            log.error("[shorts] 실패:\n%s", traceback.format_exc())

    log.info("=== 파이프라인 종료 ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
