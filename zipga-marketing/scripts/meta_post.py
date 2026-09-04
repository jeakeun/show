#!/usr/bin/env python3
"""인스타그램 릴스 · 스레드 게시.

두 플랫폼 모두 Meta의 "컨테이너 생성 → 게시" 2단계 방식이다.
  1) 미디어 컨테이너를 만든다 (creation_id를 받음)
  2) 서버가 미디어를 처리할 때까지 기다린다
  3) 게시한다

** 가장 중요한 제약 **
  Meta는 미디어를 직접 업로드받지 않는다. 공개 URL을 주면 서버가 그걸 내려받는다.
  공식 문서: "we cURL media used in publishing attempts, so the media must be
  hosted on a publicly accessible server"
  → 로컬 영상 파일을 그대로 줄 수 없다. upload_media.py로 먼저 공개 URL을 만들어야 한다.

준비물 (환경변수):
  IG_USER_ID          인스타그램 프로페셔널 계정의 IG User ID
  IG_ACCESS_TOKEN     instagram_business_content_publish 권한이 있는 토큰
  THREADS_USER_ID     스레드 사용자 ID
  THREADS_ACCESS_TOKEN

사용법:
  python3 meta_post.py instagram --video-url https://.../video.mp4 --caption-file cap.txt
  python3 meta_post.py threads   --video-url https://.../video.mp4 --text-file txt.txt
  python3 meta_post.py threads   --text-file txt.txt              # 텍스트만

  --dry-run 을 붙이면 실제 전송 없이 보낼 내용만 출력한다.

게시 제한: 인스타 24시간 100건, 스레드 24시간 250건. 주 2회에는 무관하다.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IG_BASE = "https://graph.facebook.com/v21.0"
TH_BASE = "https://graph.threads.net/v1.0"


def call(url, fields, dry_run, label):
    body = urllib.parse.urlencode(fields, encoding="utf-8").encode("utf-8")

    if dry_run:
        print(f"[dry-run] {label}: POST {url}")
        for k, v in fields.items():
            if "token" in k.lower():
                v = "(토큰 생략)"
            preview = str(v) if len(str(v)) < 200 else str(v)[:200] + " …(생략)"
            print(f"    {k}: {preview}")
        return {"id": "DRYRUN_ID"}

    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        print(f"[!] {label} 실패 HTTP {e.code}", file=sys.stderr)
        print(text, file=sys.stderr)
        # 재시도하지 않는다. 중복 게시를 막는 것이 성공보다 중요하다.
        sys.exit(1)
    except Exception as e:
        sys.exit(f"[!] {label} 요청 실패: {e}")


def get_json(url):
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        sys.exit(f"[!] 상태 조회 실패 HTTP {e.code}")


def read_text(path, inline):
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return inline or ""


def wait_ready(base, creation_id, token, dry_run, max_wait=300):
    """미디어 처리가 끝날 때까지 기다린다. 영상은 시간이 걸린다."""
    if dry_run:
        print("[dry-run] 미디어 처리 대기 생략")
        return

    waited = 0
    while waited < max_wait:
        time.sleep(15)
        waited += 15
        q = urllib.parse.urlencode(
            {"fields": "status_code,status", "access_token": token}
        )
        data = get_json(f"{base}/{creation_id}?{q}")
        code = data.get("status_code", "")
        print(f"    처리 상태: {code} ({waited}초 경과)")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"[!] 미디어 처리 실패: {data}")
    sys.exit(f"[!] {max_wait}초 안에 처리가 끝나지 않았습니다. 게시하지 않고 중단합니다.")


def post_instagram(args):
    user_id = os.environ.get("IG_USER_ID", "")
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    if not args.dry_run and not (user_id and token):
        sys.exit("[!] IG_USER_ID / IG_ACCESS_TOKEN 환경변수가 필요합니다.")

    caption = read_text(args.caption_file, args.caption)
    if not args.video_url:
        sys.exit("[!] 인스타그램은 --video-url 이 필요합니다. 공개 URL이어야 합니다.")

    fields = {
        "media_type": "REELS",
        "video_url": args.video_url,
        "caption": caption[:2200],
        "access_token": token,
    }
    res = call(f"{IG_BASE}/{user_id}/media", fields, args.dry_run, "IG 컨테이너 생성")
    cid = res.get("id")
    print(f"[+] 컨테이너 생성: {cid}")

    wait_ready(IG_BASE, cid, token, args.dry_run)

    res = call(
        f"{IG_BASE}/{user_id}/media_publish",
        {"creation_id": cid, "access_token": token},
        args.dry_run,
        "IG 게시",
    )
    print(f"[+] 인스타그램 게시 완료: {res}")


def post_threads(args):
    user_id = os.environ.get("THREADS_USER_ID", "")
    token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not args.dry_run and not (user_id and token):
        sys.exit("[!] THREADS_USER_ID / THREADS_ACCESS_TOKEN 환경변수가 필요합니다.")

    text = read_text(args.text_file, args.text)

    fields = {"access_token": token, "text": text[:500]}
    if args.video_url:
        fields["media_type"] = "VIDEO"
        fields["video_url"] = args.video_url
    else:
        fields["media_type"] = "TEXT"

    res = call(f"{TH_BASE}/{user_id}/threads", fields, args.dry_run, "스레드 컨테이너 생성")
    cid = res.get("id")
    print(f"[+] 컨테이너 생성: {cid}")

    if args.video_url:
        wait_ready(TH_BASE, cid, token, args.dry_run)
    elif not args.dry_run:
        # 문서 권장: 게시 전 평균 30초 대기
        print("    30초 대기...")
        time.sleep(30)

    res = call(
        f"{TH_BASE}/{user_id}/threads_publish",
        {"creation_id": cid, "access_token": token},
        args.dry_run,
        "스레드 게시",
    )
    print(f"[+] 스레드 게시 완료: {res}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="target", required=True)

    i = sub.add_parser("instagram", help="인스타그램 릴스 게시")
    i.add_argument("--video-url", required=True, help="공개적으로 접근 가능한 영상 URL")
    i.add_argument("--caption")
    i.add_argument("--caption-file")
    i.add_argument("--dry-run", action="store_true")

    t = sub.add_parser("threads", help="스레드 게시")
    t.add_argument("--video-url", help="공개 URL. 없으면 텍스트만 게시")
    t.add_argument("--text")
    t.add_argument("--text-file")
    t.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    if args.target == "instagram":
        post_instagram(args)
    else:
        post_threads(args)


if __name__ == "__main__":
    main()
