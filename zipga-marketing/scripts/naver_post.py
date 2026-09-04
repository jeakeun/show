#!/usr/bin/env python3
"""네이버 블로그 · 카페 글쓰기.

네이버 오픈API 문서: https://naver.github.io/naver-openapi-guide/apilist.html
  블로그 글쓰기   POST https://openapi.naver.com/blog/writePost.json
  카페 글쓰기     POST https://openapi.naver.com/v1/cafe/{clubid}/menu/{menuid}/articles

준비물:
  네이버 개발자센터에서 애플리케이션 등록 → 사용 API에 "네이버 블로그" / "카페" 추가
  → 로그인 오픈API(OAuth 2.0)로 access token 발급

  환경변수:
    NAVER_ACCESS_TOKEN   OAuth 2.0 액세스 토큰 (필수)

사용법:
  # 블로그
  python3 naver_post.py blog --title "제목" --content-file 본문.html --tags "술게임,앱개발"

  # 카페
  python3 naver_post.py cafe --clubid 12345678 --menuid 5 \\
      --title "제목" --content-file 본문.txt

  --dry-run 을 붙이면 실제 전송 없이 보낼 내용만 출력한다.

주의:
  * 이 스크립트는 재시도하지 않는다. 실패는 실패로 끝낸다. 자동 재시도가 중복 게시를 만든다.
  * 응답 본문을 그대로 출력한다. 네이버 API는 오류 사유를 본문에 담아 보내므로 반드시 읽을 것.
"""

import argparse
import os
import sys
import urllib.parse
import urllib.request

TOKEN = os.environ.get("NAVER_ACCESS_TOKEN", "")
BLOG_URL = "https://openapi.naver.com/blog/writePost.json"
CAFE_URL = "https://openapi.naver.com/v1/cafe/{clubid}/menu/{menuid}/articles"


def read_content(args):
    if args.content_file:
        with open(args.content_file, encoding="utf-8") as f:
            return f.read()
    if args.content:
        return args.content
    sys.exit("[!] --content 또는 --content-file 중 하나가 필요합니다.")


def post(url, fields, dry_run):
    """네이버 오픈API는 form-urlencoded(UTF-8) 본문을 받는다."""
    body = urllib.parse.urlencode(fields, encoding="utf-8").encode("utf-8")

    if dry_run:
        print(f"[dry-run] POST {url}")
        for k, v in fields.items():
            preview = v if len(str(v)) < 200 else str(v)[:200] + " …(생략)"
            print(f"  {k}: {preview}")
        print("[dry-run] 실제로 보내지 않았습니다.")
        return

    if not TOKEN:
        sys.exit("[!] NAVER_ACCESS_TOKEN 환경변수가 비어 있습니다.")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header(
        "Content-Type", "application/x-www-form-urlencoded; charset=utf-8"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            print(f"[+] HTTP {resp.status}")
            print(text)
            if resp.status != 200:
                sys.exit(1)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        print(f"[!] HTTP {e.code}", file=sys.stderr)
        print(text, file=sys.stderr)
        # 재시도하지 않는다. 중복 게시를 막는 것이 성공보다 중요하다.
        sys.exit(1)
    except Exception as e:
        sys.exit(f"[!] 요청 실패: {e}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="target", required=True)

    b = sub.add_parser("blog", help="네이버 블로그에 글쓰기")
    b.add_argument("--title", required=True)
    b.add_argument("--content")
    b.add_argument("--content-file")
    b.add_argument("--tags", default="", help="쉼표 구분")
    b.add_argument("--category", default="", help="카테고리 번호 (listCategory.json으로 조회)")
    b.add_argument("--dry-run", action="store_true")

    c = sub.add_parser("cafe", help="네이버 카페에 글쓰기")
    c.add_argument("--clubid", required=True)
    c.add_argument("--menuid", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--content")
    c.add_argument("--content-file")
    c.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    content = read_content(args)

    if args.target == "blog":
        fields = {"title": args.title, "contents": content}
        if args.tags:
            fields["tags"] = args.tags
        if args.category:
            fields["categoryNo"] = args.category
        post(BLOG_URL, fields, args.dry_run)
    else:
        url = CAFE_URL.format(clubid=args.clubid, menuid=args.menuid)
        post(url, {"subject": args.title, "content": content}, args.dry_run)


if __name__ == "__main__":
    main()
