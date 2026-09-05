"""YouTube Data API로 완성된 영상을 업로드한다.

최초 1회는 브라우저에서 구글 계정 동의가 필요하다 (README의 OAuth 설정 참고).
이후에는 secrets/token.json 의 토큰이 자동 갱신된다.
"""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .config import CLIENT_SECRET_FILE, CONFIG, TOKEN_FILE

# force-ssl = 업로드 + 썸네일 + 댓글 작성까지 포함하는 전체 권한
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        if not CLIENT_SECRET_FILE.exists():
            raise RuntimeError(
                "secrets/client_secret.json 이 없습니다. README의 OAuth 설정을 먼저 진행하세요."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE), SCOPES
        )
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_video(video_path: Path, meta: dict,
                 thumbnail: Path | None = None) -> str:
    """meta: title/description/tags/comment 를 포함한 dict. 반환: 업로드된 영상 ID."""
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)

    description = meta["description"].rstrip()
    channel_url = CONFIG.get("channel_url", "")
    if channel_url:
        description += (
            f"\n\n▶ 매일 아침 7시, 1분 만에 똑똑해지는 궁금증 배달\n"
            f"구독하기: {channel_url}?sub_confirmation=1"
        )

    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": description[:4900],
            "tags": meta.get("tags", [])[:20],
            "categoryId": "27",  # Education
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": CONFIG.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(
        str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True
    )
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    # 커스텀 썸네일 (실패해도 업로드는 유지)
    if thumbnail and thumbnail.exists():
        try:
            yt.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(thumbnail))
            ).execute()
        except Exception as e:
            print(f"썸네일 설정 실패 (무시): {e}")

    # 참여 유도 댓글 (실패해도 업로드는 유지)
    comment = meta.get("comment", "").strip()
    if comment:
        try:
            yt.commentThreads().insert(
                part="snippet",
                body={"snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment}},
                }},
            ).execute()
        except Exception as e:
            print(f"댓글 작성 실패 (무시): {e}")

    return video_id
