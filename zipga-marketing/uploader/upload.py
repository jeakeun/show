# 원클릭 업로더 — watch/ 폴더의 영상·글을 5개 채널에 올립니다.
#   전체:      업로드.bat        (python upload.py)
#   플랫폼별:  유튜브만.bat 등    (python upload.py --only youtube)
#
# 각 채널은 config.json 에서 enabled=true + 인증 정보가 있으면 "자동 업로드",
# 아니면 "보조 모드"(페이지 열기 + 문구 클립보드 복사 + 파일 선택)로 동작합니다.
# 자세한 사용법은 "마케팅자동화 설명서.md" 를 읽으세요.
import argparse
import csv
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCH = HERE / "watch"
DONE = HERE / "uploaded"
SECRETS = HERE / "secrets"
CONFIG_PATH = HERE / "config.json"
LOG = HERE / "uploads_log.csv"
VIDEO_EXT = {".mp4", ".mov", ".m4v"}

DEFAULT_CONFIG = {
    "_안내": "설명서를 보고 채널별로 연결하세요. enabled 가 false 면 보조 모드로 동작합니다.",
    "youtube": {
        "enabled": False,
        "privacy": "private",
        "client_secret_file": "secrets/client_secret.json"
    },
    "instagram": {
        "enabled": False,
        "ig_user_id": "",
        "access_token": "",
        "api_version": "v23.0",
        "share_to_feed": True
    },
    "threads": {
        "enabled": False,
        "threads_user_id": "",
        "access_token": ""
    },
    "naver_blog": {
        "enabled": False,
        "access_token": "",
        "category_no": "",
        "_안내": "네이버 개발자센터에서 '블로그' API 사용 신청 후 OAuth 액세스 토큰이 필요합니다"
    },
    "tistory": {
        "enabled": False,
        "blog_name": "",
        "_안내": "티스토리는 Open API가 종료돼 자동 업로드가 불가합니다. 보조 모드만 지원합니다"
    },
    "default_caption": "게임 점수로 귀가 시간을 정하는 사이트, 집가.\n평균 40점 미만이면 화면에 뜨는 두 글자 — \"집 가\"\n설치 없이 링크로 바로. 곧 열립니다. 댓글에 \"점수\" 남겨주세요.\n\n#집가 #귀가 #모임"
}

# key, 표시이름, 종류(video=영상 업로드 / post=글 발행), 보조모드에서 열 주소
PLATFORMS = [
    ("youtube",    "유튜브",       "video", "https://studio.youtube.com/"),
    ("instagram",  "인스타그램",   "video", "https://business.facebook.com/latest/reels_composer"),
    ("threads",    "쓰레드",       "post",  "https://www.threads.net/"),
    ("naver_blog", "네이버 블로그", "post",  "https://blog.naver.com/GoBlogWrite.naver"),
    ("tistory",    "티스토리",     "post",  "https://www.tistory.com/"),
]
PLATFORM_KEYS = [p[0] for p in PLATFORMS]


# ---------- 공용 ----------

def load_config():
    """설정을 읽고, 새로 생긴 항목이 있으면 채워 넣습니다 (기존 값은 유지)."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[안내] 처음 실행이라 config.json 을 만들었습니다: {CONFIG_PATH}")
        print("       지금은 모든 채널이 '보조 모드'입니다. 연결 방법은 설명서를 보세요.\n")
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    added = []
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            added.append(k)
    if added:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[안내] config.json 에 새 항목을 추가했습니다: {', '.join(added)}\n")
    return cfg


def get_caption(item, cfg, platform_key=None):
    """문구를 찾습니다. 채널 전용 문구가 있으면 그걸 우선합니다.

    찾는 순서
      1) 영상이름.youtube.txt   ← 채널 전용 (채널마다 다른 글을 쓸 때)
      2) 영상이름.txt           ← 공용
      3) config.json 의 기본 문구
    """
    if platform_key:
        per = item.with_suffix(f".{platform_key}.txt")
        if per.exists():
            return per.read_text(encoding="utf-8").strip()
    txt = item.with_suffix(".txt")
    if txt.exists():
        return txt.read_text(encoding="utf-8").strip()
    return cfg.get("default_caption", "").strip()


def caption_source(item, platform_key):
    """어느 문구 파일을 썼는지 사람이 볼 수 있게 알려줍니다."""
    if item.with_suffix(f".{platform_key}.txt").exists():
        return f"{platform_key} 전용 문구"
    if item.with_suffix(".txt").exists():
        return "공용 문구"
    return "기본 문구(config.json)"


def title_from(caption, item, limit=95):
    first = caption.splitlines()[0].strip() if caption else item.stem
    first = first or item.stem
    return (first[:limit] + "…") if len(first) > limit else first


def copy_clipboard(text):
    """한글 안 깨지게 임시 UTF-8 파일을 거쳐 클립보드에 복사."""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            tmp = f.name
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Content -Raw -Encoding UTF8 '{tmp}' | Set-Clipboard"],
            capture_output=True)
        Path(tmp).unlink(missing_ok=True)
        return True
    except Exception:
        return False


def select_in_explorer(path):
    try:
        subprocess.Popen(["explorer", "/select,", str(path)])
    except Exception:
        pass


def log_row(item, platform, mode, result):
    exists = LOG.exists()
    with open(LOG, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["시각", "파일", "플랫폼", "방식", "결과"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), item.name, platform, mode, result])


# ---------- 유튜브 (Data API) ----------

def upload_youtube(video, caption, cfg):
    y = cfg["youtube"]
    secret = HERE / y["client_secret_file"]
    if not secret.exists():
        return None, f"client_secret.json 이 없습니다 ({secret}) — 설명서 3장 참고"
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return None, "라이브러리 미설치 — 업로드.bat 을 다시 실행하면 자동 설치됩니다"

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    token_file = SECRETS / "yt_token.json"
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("  [유튜브] 브라우저가 열리면 구글 계정으로 로그인해 허용해주세요 (최초 1회)")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    svc = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": title_from(caption, video), "description": caption, "categoryId": "22"},
        "status": {"privacyStatus": y.get("privacy", "private"), "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), chunksize=1024 * 1024 * 4, resumable=True)
    req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    print("  [유튜브] 업로드 중...", end="", flush=True)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f" {int(status.progress() * 100)}%", end="", flush=True)
    print(" 완료")
    return f"https://youtu.be/{response['id']}", None


# ---------- 인스타그램 릴스 (Graph API, 파일 직접 업로드) ----------

def upload_instagram(video, caption, cfg):
    ig = cfg["instagram"]
    if not (ig.get("ig_user_id") and ig.get("access_token")):
        return None, "ig_user_id / access_token 이 비어 있습니다 — 설명서 4장 참고"
    try:
        import requests
    except ImportError:
        return None, "라이브러리 미설치 — 업로드.bat 을 다시 실행하면 자동 설치됩니다"

    v = ig.get("api_version", "v23.0")
    base = f"https://graph.facebook.com/{v}"
    token = ig["access_token"]

    r = requests.post(f"{base}/{ig['ig_user_id']}/media", data={
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "share_to_feed": str(ig.get("share_to_feed", True)).lower(),
        "access_token": token,
    }).json()
    if "id" not in r:
        return None, f"컨테이너 생성 실패: {r.get('error', {}).get('message', r)}"
    container = r["id"]
    upload_uri = r.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{v}/{container}"

    size = video.stat().st_size
    print("  [인스타] 영상 전송 중...", flush=True)
    with open(video, "rb") as f:
        up = requests.post(upload_uri, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size),
        }, data=f).json()
    if not up.get("success"):
        return None, f"영상 전송 실패: {up}"

    for _ in range(60):  # 최대 5분 대기
        st = requests.get(f"{base}/{container}", params={
            "fields": "status_code", "access_token": token}).json()
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            return None, f"처리 실패: {st}"
        time.sleep(5)
    else:
        return None, "처리 대기 시간 초과 — 잠시 후 다시 실행해보세요"

    pub = requests.post(f"{base}/{ig['ig_user_id']}/media_publish", data={
        "creation_id": container, "access_token": token}).json()
    if "id" not in pub:
        return None, f"발행 실패: {pub.get('error', {}).get('message', pub)}"
    return f"게시 완료 (media id {pub['id']})", None


# ---------- 쓰레드 (텍스트 글) ----------

def post_threads(item, caption, cfg):
    th = cfg["threads"]
    if not th.get("access_token"):
        return None, "access_token 이 비어 있습니다 — 설명서 5장 참고"
    try:
        import requests
    except ImportError:
        return None, "라이브러리 미설치 — 업로드.bat 을 다시 실행하면 자동 설치됩니다"

    if len(caption) > 500:
        return None, f"글이 {len(caption)}자입니다. 쓰레드는 500자까지만 됩니다"

    base = "https://graph.threads.net/v1.0"
    token = th["access_token"]
    uid = th.get("threads_user_id")
    if not uid:
        me = requests.get(f"{base}/me", params={"fields": "id", "access_token": token}).json()
        uid = me.get("id")
        if not uid:
            return None, f"user id 조회 실패: {me}"

    r = requests.post(f"{base}/{uid}/threads", data={
        "media_type": "TEXT", "text": caption, "access_token": token}).json()
    if "id" not in r:
        return None, f"작성 실패: {r.get('error', {}).get('message', r)}"
    time.sleep(3)
    pub = requests.post(f"{base}/{uid}/threads_publish", data={
        "creation_id": r["id"], "access_token": token}).json()
    if "id" not in pub:
        return None, f"발행 실패: {pub.get('error', {}).get('message', pub)}"
    return f"게시 완료 (id {pub['id']})", None


# ---------- 네이버 블로그 (오픈 API) ----------

def post_naver_blog(item, caption, cfg):
    nb = cfg["naver_blog"]
    if not nb.get("access_token"):
        return None, "access_token 이 비어 있습니다 — 네이버 개발자센터에서 블로그 API 신청 후 발급"
    try:
        import requests
    except ImportError:
        return None, "라이브러리 미설치 — 업로드.bat 을 다시 실행하면 자동 설치됩니다"

    lines = caption.splitlines()
    title = title_from(caption, item, limit=100)
    body = "\n".join(lines[1:]).strip() or caption

    data = {"title": title, "contents": body}
    if nb.get("category_no"):
        data["categoryNo"] = str(nb["category_no"])

    r = requests.post("https://openapi.naver.com/blog/writePost.json",
                      headers={"Authorization": f"Bearer {nb['access_token']}"},
                      data=data)
    try:
        j = r.json()
    except Exception:
        return None, f"응답 해석 실패 (HTTP {r.status_code}): {r.text[:200]}"

    msg = j.get("message", {})
    if isinstance(msg, dict) and msg.get("status") == "200":
        return "게시 완료", None
    return None, f"발행 실패: {j}"


# ---------- 티스토리 (API 종료 — 보조 모드만) ----------

def post_tistory(item, caption, cfg):
    return None, ("티스토리는 Open API가 종료돼 자동 발행이 불가능합니다. "
                  "config.json 에서 enabled 를 false 로 두고 보조 모드로 올리세요")


HANDLERS = {
    "youtube": upload_youtube,
    "instagram": upload_instagram,
    "threads": post_threads,
    "naver_blog": post_naver_blog,
    "tistory": post_tistory,
}


# ---------- 보조 모드 ----------

def assist(name, key, url, kind, item, caption, dry_run, cfg):
    print(f"  [{name}] 보조 모드 — 문구를 복사하고 페이지를 엽니다")
    if dry_run:
        return "보조(테스트)"

    if key == "tistory" and cfg["tistory"].get("blog_name"):
        url = f"https://{cfg['tistory']['blog_name']}.tistory.com/manage/newpost/"

    copy_clipboard(caption)
    webbrowser.open(url)
    if kind == "video":
        select_in_explorer(item)
        print("      1) 탐색기에 선택된 영상을 페이지로 드래그")
        print("      2) 문구 칸에 Ctrl+V")
    else:
        print("      문구가 복사돼 있습니다. 글쓰기 칸에 Ctrl+V 하세요")
    input(f"      올렸으면 엔터를 눌러 다음으로 → ")
    return "보조"


# ---------- 메인 ----------

def main():
    ap = argparse.ArgumentParser(description="집가 업로더")
    ap.add_argument("--only", choices=PLATFORM_KEYS, help="이 채널에만 올립니다")
    ap.add_argument("--dry-run", action="store_true", help="실제 업로드·창 열기 없이 흐름만 확인")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (WATCH, DONE, SECRETS):
        d.mkdir(exist_ok=True)
    cfg = load_config()

    targets = [p for p in PLATFORMS if (args.only is None or p[0] == args.only)]

    videos = sorted(p for p in WATCH.iterdir() if p.suffix.lower() in VIDEO_EXT)
    if not videos:
        print(f"watch 폴더에 영상이 없습니다.\n→ 영상을 여기에 넣고 다시 실행하세요: {WATCH}")
        return

    scope = targets[0][1] if args.only else "전체 채널"
    print(f"=== 업로더 — 영상 {len(videos)}개 · {scope} ===\n")

    for video in videos:
        print(f"■ {video.name}")

        all_ok = True
        for key, name, kind, url in targets:
            caption = get_caption(video, cfg, key)          # 채널 전용 문구 우선
            print(f"  [{name}] 문구: {caption_source(video, key)}")
            enabled = cfg.get(key, {}).get("enabled", False)
            if enabled and not args.dry_run:
                try:
                    result, err = HANDLERS[key](video, caption, cfg)
                except Exception as e:
                    result, err = None, f"예외: {e}"
                if err:
                    print(f"  [{name}][실패] {err}")
                    log_row(video, name, "자동", f"실패: {err}")
                    all_ok = False
                else:
                    print(f"  [{name}] {result}")
                    log_row(video, name, "자동", result)
            elif enabled and args.dry_run:
                print(f"  [{name}] 자동 업로드 대상 (테스트라 건너뜀)")
            else:
                mode = assist(name, key, url, kind, video, caption, args.dry_run, cfg)
                if not args.dry_run:
                    # 보조 모드는 "안내만 함"이라는 뜻 — 실제 발행 여부는 사람만 압니다
                    log_row(video, name, mode, "보조 모드 안내함(발행 여부 미확인)")

        if args.dry_run:
            print()
            continue

        # 채널 하나만 돌린 경우에는 파일을 옮기지 않습니다 (다른 채널에 또 올려야 하므로)
        if args.only:
            print("  (한 채널만 올렸으므로 watch 폴더에 그대로 둡니다)")
        else:
            move = all_ok or input("  이 영상 처리가 끝났나요? uploaded 폴더로 옮길까요 (y/n): ").strip().lower() == "y"
            if move:
                shutil.move(str(video), DONE / video.name)
                for extra in [video.with_suffix(".txt")] +                              [video.with_suffix(f".{k}.txt") for k in PLATFORM_KEYS]:
                    if extra.exists():
                        shutil.move(str(extra), DONE / extra.name)
                print("  → uploaded/ 로 이동 완료")
        print()

    print("=== 끝 — 기록은 uploads_log.csv 에 남았습니다 ===")


if __name__ == "__main__":
    main()
