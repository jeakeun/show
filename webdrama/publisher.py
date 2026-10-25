# -*- coding: utf-8 -*-
"""완성 회차를 유튜브 쇼츠·인스타 릴스·틱톡에 올린다.

실패해도 자동 재시도하지 않는다 (중복 게시 방지). 플랫폼별 결과는 회차 status.json 에 남는다.
"""
import time
from pathlib import Path

import requests

from common import CONFIG, SECRETS_DIR, STATE_PATH, read_json, write_json

AI_NOTICE = "※ 이 드라마의 영상과 음성은 AI로 제작되었습니다. 이야기와 인물은 모두 허구입니다."


class NotStarted(RuntimeError):
    """업로드를 시작하기 전에 실패 (로그인·설정 문제). 아무것도 안 올라갔으니 다음에 다시 해도 된다."""


def yt_description(s: str) -> str:
    """유튜브 설명란 한도는 5000 '바이트'(한글 3바이트)이고 <> 는 쓸 수 없다."""
    s = s.replace("<", "(").replace(">", ")")
    b = s.encode("utf-8")[:4900]
    return b.decode("utf-8", errors="ignore")


def texts(bible: dict, n: int, ep: dict) -> dict:
    tags = list(dict.fromkeys(ep.get("hashtags", []) + bible.get("hashtags", [])))
    tag_line = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
    title = f"[{bible['title']}] {n}화 · {ep['title']}"
    return {
        "title": title[:100],
        "description": f"{ep['caption_ko']}\n\n{tag_line}\n\n{AI_NOTICE}",
        "short": f"{title}\n\n{ep['caption_ko']}\n\n{tag_line} #AI드라마",
    }


# ---------- 유튜브 ----------

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
YT_TOKEN = SECRETS_DIR / "yt_token.json"


def _youtube():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if YT_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(YT_TOKEN), YT_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        YT_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        secret = Path(CONFIG["platforms"]["youtube"]["client_secret"])
        if not secret.exists():
            raise RuntimeError(f"client_secret.json 이 없습니다: {secret}")
        print("브라우저가 열리면 '웹드라마 채널'을 고르고 허용하세요 (최초 1회).")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), YT_SCOPES)
        creds = flow.run_local_server(port=0)
        SECRETS_DIR.mkdir(exist_ok=True)
        YT_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def youtube_whoami() -> str:
    yt = _youtube()
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    return items[0]["snippet"]["title"] if items else "(채널 없음)"


def _playlist(yt, bible: dict, state_key: str = "youtube_playlist", title: str = "") -> str:
    """시리즈 재생목록 (처음 한 번 만들고 series/state.json 에 ID 저장). 쇼츠 회차용과 롱폼 몰아보기용 따로."""
    state = read_json(STATE_PATH, {})
    pid = state.get(state_key)
    if pid:
        return pid
    r = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title or f"{bible['title']} 회차별 보기", "description": bible["logline"],
                    "defaultLanguage": "ko"},
        "status": {"privacyStatus": "public"},
    }).execute()
    state = read_json(STATE_PATH, {})
    state[state_key] = r["id"]
    write_json(STATE_PATH, state)
    return r["id"]


def upload_youtube(video: Path, bible: dict, n: int, ep: dict) -> str:
    from googleapiclient.http import MediaFileUpload
    yt = _youtube()
    t = texts(bible, n, ep)
    body = {
        "snippet": {"title": t["title"], "description": yt_description(t["description"]),
                    "tags": [h.lstrip("#") for h in ep.get("hashtags", []) + bible.get("hashtags", [])][:20],
                    "categoryId": "24", "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": {"privacyStatus": CONFIG["platforms"]["youtube"].get("privacy", "public"),
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk(num_retries=5)  # 같은 업로드 안에서의 재시도라 중복 게시가 생기지 않는다
    vid = resp["id"]
    try:
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": _playlist(yt, bible),
            "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    except Exception as e:
        print(f"  재생목록 추가 실패 (무시): {e}")
    return f"https://youtube.com/shorts/{vid}"


def upload_youtube_long(video: Path, bible: dict, meta: dict, thumb: Path | None) -> tuple[str, str]:
    """몰아보기 롱폼 업로드. 반환: (주소, 덧붙일 말). 썸네일·재생목록 실패는 업로드 성공으로 친다."""
    from googleapiclient.http import MediaFileUpload
    try:
        yt = _youtube()
    except Exception as e:
        raise NotStarted(f"유튜브 로그인 실패: {e}") from e
    body = {
        "snippet": {"title": meta["title"], "description": yt_description(meta["description"]), "tags": meta["tags"],
                    "categoryId": "24", "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": {"privacyStatus": CONFIG.get("binge", {}).get(
                       "privacy", CONFIG["platforms"]["youtube"].get("privacy", "public")),
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk(num_retries=5)  # 같은 업로드 안에서의 재시도라 중복 게시가 생기지 않는다
    vid = resp["id"]
    notes = []
    if thumb and thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
            notes.append("썸네일 적용")
        except Exception as e:  # 새 채널은 휴대폰 인증 전에는 맞춤 썸네일이 막혀 있다
            notes.append(f"썸네일 실패(채널 휴대폰 인증 필요할 수 있음): {str(e)[:120]}")
    try:
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": _playlist(yt, bible, "youtube_binge_playlist", f"{bible['title']} 몰아보기 모음"),
            "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    except Exception as e:
        notes.append(f"재생목록 추가 실패(무시): {str(e)[:120]}")
    return f"https://youtu.be/{vid}", " · ".join(notes)


# ---------- 인스타그램 릴스 (Graph API resumable, 집가 uploader 와 같은 방식) ----------

def upload_instagram(video: Path, bible: dict, n: int, ep: dict) -> str:
    sec = read_json(SECRETS_DIR / "instagram.json", {})
    if not (sec.get("ig_user_id") and sec.get("access_token")):
        raise RuntimeError("secrets/instagram.json 에 ig_user_id, access_token 이 없습니다")
    v = CONFIG["platforms"]["instagram"].get("api_version", "v23.0")
    base = f"https://graph.facebook.com/{v}"
    token = sec["access_token"]
    r = requests.post(f"{base}/{sec['ig_user_id']}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": texts(bible, n, ep)["short"][:2200],
        "share_to_feed": "true", "access_token": token}, timeout=60).json()
    if "id" not in r:
        raise RuntimeError(f"컨테이너 생성 실패: {r.get('error', {}).get('message', r)}")
    container = r["id"]
    uri = r.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{v}/{container}"
    with open(video, "rb") as f:
        up = requests.post(uri, headers={"Authorization": f"OAuth {token}", "offset": "0",
                                         "file_size": str(video.stat().st_size)}, data=f, timeout=600).json()
    if not up.get("success"):
        raise RuntimeError(f"영상 전송 실패: {up}")
    for _ in range(60):
        st = requests.get(f"{base}/{container}", params={"fields": "status_code", "access_token": token},
                          timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"처리 실패: {st}")
        time.sleep(5)
    else:
        raise RuntimeError("처리 대기 시간 초과")
    pub = requests.post(f"{base}/{sec['ig_user_id']}/media_publish",
                        data={"creation_id": container, "access_token": token}, timeout=60).json()
    if "id" not in pub:
        raise RuntimeError(f"발행 실패: {pub.get('error', {}).get('message', pub)}")
    return f"media {pub['id']}"


# ---------- 틱톡 (Content Posting API, Direct Post) ----------

TT = "https://open.tiktokapis.com/v2"


def _tiktok_token() -> str:
    path = SECRETS_DIR / "tiktok.json"
    sec = read_json(path, {})
    if not sec.get("refresh_token"):
        raise RuntimeError("secrets/tiktok.json 에 client_key, client_secret, refresh_token 이 없습니다")
    r = requests.post(f"{TT}/oauth/token/", data={
        "client_key": sec["client_key"], "client_secret": sec["client_secret"],
        "grant_type": "refresh_token", "refresh_token": sec["refresh_token"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30).json()
    if "access_token" not in r:
        raise RuntimeError(f"틱톡 토큰 갱신 실패: {r}")
    sec["access_token"], sec["refresh_token"] = r["access_token"], r.get("refresh_token", sec["refresh_token"])
    write_json(path, sec)
    return sec["access_token"]


def upload_tiktok(video: Path, bible: dict, n: int, ep: dict) -> str:
    token = _tiktok_token()
    size = video.stat().st_size
    if size > 64 * 1024 * 1024:
        raise RuntimeError("영상이 64MB 를 넘어 한 번에 올릴 수 없습니다")
    init = requests.post(f"{TT}/post/publish/video/init/", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}, json={
        "post_info": {"title": texts(bible, n, ep)["short"][:2200],
                      "privacy_level": CONFIG["platforms"]["tiktok"].get("privacy_level", "SELF_ONLY"),
                      "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                      "is_aigc": True},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size,
                        "total_chunk_count": 1}}, timeout=60).json()
    data = init.get("data", {})
    if not data.get("upload_url"):
        raise RuntimeError(f"틱톡 업로드 준비 실패: {init.get('error', init)}")
    with open(video, "rb") as f:
        r = requests.put(data["upload_url"], headers={
            "Content-Type": "video/mp4", "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}"}, data=f, timeout=600)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"틱톡 영상 전송 실패: HTTP {r.status_code} {r.text[:200]}")
    return f"publish_id {data.get('publish_id')}"


HANDLERS = {"youtube": upload_youtube, "instagram": upload_instagram, "tiktok": upload_tiktok}
NAMES = {"youtube": "유튜브", "instagram": "인스타", "tiktok": "틱톡"}
