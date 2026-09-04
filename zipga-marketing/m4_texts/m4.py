# M4 텍스트 생성 — 클립마다 인스타 캡션 / 쓰레드 글 / 쇼츠 제목을 만듦
# 프롬프트는 prompts/ 폴더의 텍스트 파일 — 마케팅 담당이 이 파일만 고치면 톤이 바뀝니다.
# 스켈레톤 단계에서는 변수 치환(템플릿)으로 생성합니다. 나중에 클로드 API 호출로 교체하는 자리를 표시해 뒀습니다.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import DATA, ROOT, info, load_account, load_config, read_csv, warn, write_csv

TAG = "M4"
TEXTS = DATA / "texts.csv"
TEXTS_FIELDS = ["clip_id", "platform", "body", "hashtags", "account", "version"]
PLATFORM_PROMPT = {
    "instagram": "instagram.txt",
    "threads": "threads.txt",
    "youtube": "shorts_title.txt",
}


def _render(template, variables):
    out = template
    for k, v in variables.items():
        out = out.replace("{" + k + "}", str(v))
    return out.strip()


def run(account_id="a"):
    cfg = load_config()
    account = load_account(account_id)
    manifest = read_csv(DATA / "clips" / "manifest.csv")
    if not manifest:
        warn(TAG, "clips/manifest.csv 가 없습니다. M3를 먼저 실행하세요.")
        return False

    prompts = {}
    for platform, fname in PLATFORM_PROMPT.items():
        p = ROOT / "prompts" / fname
        if not p.exists():
            warn(TAG, f"프롬프트 파일 없음: prompts/{fname}")
            return False
        prompts[platform] = p.read_text(encoding="utf-8")

    limits = cfg["limits"]
    old = [r for r in read_csv(TEXTS) if r.get("account") != account_id]
    prev_versions = {}
    for r in read_csv(TEXTS):
        if r.get("account") == account_id:
            key = (r["clip_id"], r["platform"])
            prev_versions[key] = max(prev_versions.get(key, 0), int(r.get("version", 1)))
            old.append(r)  # 이전 버전도 남김 (A/B 비교용)

    rows = []
    for clip in manifest:
        variables = {
            "app_name": cfg["app_name"],
            "first_sentence": clip["first_sentence"],
            "persona": account["persona"],
        }
        for platform, template in prompts.items():
            body = _render(template, variables)
            limit = limits.get(f"{platform}_max_chars")
            if limit and len(body) > int(limit):
                warn(TAG, f"{clip['clip_id']}/{platform}: {len(body)}자 — 제한 {limit}자 초과")
            ver = prev_versions.get((clip["clip_id"], platform), 0) + 1
            rows.append({
                "clip_id": clip["clip_id"], "platform": platform, "body": body,
                "hashtags": cfg["hashtags"].get(platform, ""),
                "account": account_id, "version": ver,
            })

    write_csv(TEXTS, old + rows, TEXTS_FIELDS)
    info(TAG, f"완료 — 계정 '{account_id}' 문구 {len(rows)}건 생성, data/texts.csv 갱신")
    info(TAG, "톤을 바꾸려면 prompts/ 폴더의 txt 파일만 고치고 다시 실행하세요")
    return True


if __name__ == "__main__":
    from lib.common import ensure_dirs
    ensure_dirs()
    run(sys.argv[1] if len(sys.argv) > 1 else "a")
