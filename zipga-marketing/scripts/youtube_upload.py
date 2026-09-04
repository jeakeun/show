#!/usr/bin/env python3
"""유튜브 영상 업로드.

준비물:
  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

  client_secret.json  — Google Cloud Console에서 OAuth 클라이언트(데스크톱 앱)로 받은 파일
  token.json          — 최초 1회 브라우저 인증 후 자동 생성됨

사용법:
  python3 youtube_upload.py --file 영상.mp4 --title "제목" --description-file 설명.txt \\
      --tags "술게임,회식" --privacy public

  --privacy: public / unlisted / private
  --dry-run: 실제 업로드 없이 인증과 파라미터만 확인

참고: API 프로젝트가 감사(audit)를 통과하기 전에는 업로드한 영상이 비공개로 잠긴다.
      privacy를 public으로 줘도 그렇다. 감사 신청은 README 참조.
"""

import argparse
import json
import os
import sys
import time

CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "client_secret.json")
TOKEN_FILE = os.environ.get("YT_TOKEN", "token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            return creds
        except Exception as e:
            print(f"[!] 토큰 갱신 실패: {e}", file=sys.stderr)
            print("[!] token.json을 지우고 다시 인증하세요.", file=sys.stderr)

    if not os.path.exists(CLIENT_SECRET):
        sys.exit(f"[!] {CLIENT_SECRET} 이 없습니다. Google Cloud Console에서 받아 두세요.")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"[+] 인증 완료. {TOKEN_FILE} 저장됨.")
    return creds


def upload(args):
    if not os.path.exists(args.file):
        sys.exit(f"[!] 영상 파일이 없습니다: {args.file}")

    description = args.description or ""
    if args.description_file:
        with open(args.description_file, encoding="utf-8") as f:
            description = f.read()

    body = {
        "snippet": {
            "title": args.title[:100],
            "description": description[:5000],
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "categoryId": args.category,
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if args.dry_run:
        print("[dry-run] 업로드하지 않고 파라미터만 출력합니다.")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        size_mb = os.path.getsize(args.file) / 1024 / 1024
        print(f"[dry-run] 파일 확인: {args.file} ({size_mb:.1f} MB)")
        print("[dry-run] 실제 업로드는 --dry-run 을 빼고 실행하세요.")
        return

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        sys.exit(
            "[!] 라이브러리가 없습니다. 아래를 실행하세요:\n"
            "    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    youtube = build("youtube", "v3", credentials=get_credentials())
    media = MediaFileUpload(args.file, chunksize=4 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"    업로드 중... {int(status.progress() * 100)}%")
        except HttpError as e:
            # 5xx는 재시도, 4xx는 즉시 중단(할당량 초과·권한 문제 등)
            if e.resp.status in (500, 502, 503, 504) and retries < 5:
                retries += 1
                wait = 2 ** retries
                print(f"[!] 서버 오류 {e.resp.status}, {wait}초 후 재시도 ({retries}/5)")
                time.sleep(wait)
                continue
            sys.exit(f"[!] 업로드 실패: {e}")

    vid = response["id"]
    print(f"[+] 업로드 완료: https://youtu.be/{vid}")
    print(f"[+] 공개 상태: {response['status']['privacyStatus']}")
    if response["status"].get("uploadStatus") == "rejected":
        print("[!] 영상이 거부되었습니다:", response["status"].get("rejectionReason"))
    print(json.dumps({"video_id": vid, "url": f"https://youtu.be/{vid}"}, ensure_ascii=False))
    return vid


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="업로드할 영상 파일")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--description-file", help="설명을 파일에서 읽기 (UTF-8)")
    p.add_argument("--tags", default="")
    p.add_argument("--category", default="22", help="기본 22 = People & Blogs")
    p.add_argument(
        "--privacy", default="public", choices=["public", "unlisted", "private"]
    )
    p.add_argument("--dry-run", action="store_true")
    upload(p.parse_args())


if __name__ == "__main__":
    main()
