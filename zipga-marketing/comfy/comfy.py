# 콤피(ComfyUI) 자동 연결 — 꺼져 있으면 켜고, 영상까지 만들어 주는 도구.
#   python comfy.py --check                 서버 확인 (꺼져 있으면 자동으로 켬)
#   python comfy.py --scenes scenes.txt     한 줄에 한 장면씩 적힌 파일로 영상 생성 + 이어붙이기
#   python comfy.py --prompt "..."          장면 하나만 빠르게 생성
# 옵션: --mp 1.0 (화질) --sec 5 (장면 길이) --out 파일명.mp4 --draft (빠른 저화질)
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = "http://127.0.0.1:8188"
SHARED = Path(os.environ["LOCALAPPDATA"]) / "Comfy-Desktop" / "ComfyUI-Shared"
OUT_DIR = SHARED / "output"
WATCH = HERE.parent / "uploader" / "watch"
LOG = HERE / "server.log"

# 워크플로 안에서 값을 바꿀 위치 (workflow_api.json 기준)
N_PROMPT = "140:131"   # MiniMaxH3ImageToVideo
N_SEED = "140:129"     # RandomNoise
N_RES = "115"          # ResolutionSelector
N_SEC = "140:133"      # PrimitiveFloat (장면 길이 초)
N_SAVE = "92"          # SaveVideo

NOTEXT = (" Absolutely no text, no letters, no words, no readable writing,"
          " no signage text, no captions, no watermarks, no logos anywhere in frame.")


def log(msg):
    print(msg, flush=True)


def api(path, data=None, timeout=10):
    url = HOST + path
    if data is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def alive():
    try:
        api("/system_stats", timeout=3)
        return True
    except Exception:
        return False


def find_install():
    """Comfy Desktop 설치 위치에서 파이썬과 ComfyUI 폴더를 찾습니다."""
    cfg = Path(os.environ["APPDATA"]) / "Comfy Desktop" / "installations.json"
    if cfg.exists():
        for entry in json.loads(cfg.read_text(encoding="utf-8")):
            p = entry.get("installPath")
            if not p:
                continue
            comfy = Path(p) / "ComfyUI"
            py = comfy / ".venv" / "Scripts" / "python.exe"
            if py.exists() and (comfy / "main.py").exists():
                return py, comfy
    return None, None


def ensure_server(wait_sec=240):
    """서버가 꺼져 있으면 직접 켜고, 준비될 때까지 기다립니다."""
    if alive():
        log("[콤피] 이미 켜져 있습니다")
        return True

    py, comfy = find_install()
    if not py:
        log("[콤피][오류] ComfyUI 설치 위치를 못 찾았습니다. Comfy Desktop을 한 번 실행해 주세요.")
        return False

    log("[콤피] 서버가 꺼져 있어 직접 켭니다... (처음엔 1~3분 걸려요)")
    args = [str(py), "main.py", "--port", "8188",
            "--extra-model-paths-config", str(HERE / "comfy_paths.yaml"),
            "--output-directory", str(OUT_DIR),
            "--input-directory", str(SHARED / "input")]
    flags = (0x00000008 | 0x08000000) if os.name == "nt" else 0  # DETACHED | NO_WINDOW
    with open(LOG, "w", encoding="utf-8") as lf:
        subprocess.Popen(args, cwd=str(comfy), stdout=lf, stderr=subprocess.STDOUT,
                         creationflags=flags)

    for i in range(wait_sec // 5):
        time.sleep(5)
        if alive():
            log(f"[콤피] 준비 완료 ({(i + 1) * 5}초)")
            return True
    log(f"[콤피][오류] 시간 안에 안 켜졌습니다. 로그를 확인하세요: {LOG}")
    return False


def build(prompt, seed, mp, sec, aspect="9:16 (Portrait Widescreen)"):
    wf = json.loads((HERE / "workflow_api.json").read_text(encoding="utf-8"))
    wf[N_PROMPT]["inputs"]["prompt"] = prompt
    wf[N_SEED]["inputs"]["noise_seed"] = int(seed)
    wf[N_RES]["inputs"]["megapixels"] = float(mp)
    wf[N_RES]["inputs"]["aspect_ratio"] = aspect
    wf[N_SEC]["inputs"]["value"] = float(sec)
    wf[N_SAVE]["inputs"].pop("video-preview", None)
    return wf


def generate(prompt, seed, mp, sec, label="", tries=3):
    """장면 하나를 만듭니다. 실패하면 자동으로 다시 시도합니다."""
    for attempt in range(1, tries + 1):
        f = _generate_once(prompt, seed, mp, sec, label)
        if f:
            return f
        if attempt < tries:
            log(f"[콤피] 30초 후 다시 시도합니다{label} ({attempt}/{tries})")
            time.sleep(30)
    return None


def _generate_once(prompt, seed, mp, sec, label=""):
    wf = build(prompt, seed, mp, sec)
    res = api("/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())}, timeout=30)
    pid = res.get("prompt_id")
    if not pid:
        log(f"[콤피][실패] 큐 등록 안 됨: {res}")
        return None
    log(f"[콤피] 생성 중{label}...")
    start = time.time()
    while time.time() - start < 3600:
        time.sleep(10)
        try:
            hist = api(f"/history/{pid}", timeout=10)
        except Exception:
            continue
        if pid not in hist:
            continue
        entry = hist[pid]
        status = entry.get("status", {})
        if not status.get("completed"):
            if status.get("status_str") == "error":
                log(f"[콤피][실패] 생성 오류{label}")
                return None
            continue
        for node_out in entry.get("outputs", {}).values():
            for item in node_out.get("images", []) + node_out.get("videos", []):
                f = OUT_DIR / item.get("subfolder", "") / item["filename"]
                if f.exists():
                    log(f"[콤피] 완료{label} — {f.name} ({time.time() - start:.0f}초)")
                    return f
        log(f"[콤피][실패] 결과 파일을 못 찾음{label}")
        return None
    log(f"[콤피][실패] 시간 초과{label}")
    return None


def concat(files, out_path):
    """여러 장면을 한 편으로 이어붙입니다."""
    if len(files) == 1:
        shutil.copy2(files[0], out_path)
        return out_path
    args = ["ffmpeg", "-y", "-v", "error"]
    for f in files:
        args += ["-i", str(f)]
    streams = "".join(f"[{i}:v][{i}:a]" for i in range(len(files)))
    args += ["-filter_complex", f"{streams}concat=n={len(files)}:v=1:a=1[v][a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "slow", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out_path)]
    subprocess.run(args, capture_output=True)
    return out_path if out_path.exists() else None


def main():
    ap = argparse.ArgumentParser(description="콤피 자동 연결 · 영상 생성")
    ap.add_argument("--check", action="store_true", help="서버만 확인/켜기")
    ap.add_argument("--scenes", help="한 줄에 한 장면씩 적힌 텍스트 파일")
    ap.add_argument("--prompt", help="장면 하나만 생성")
    ap.add_argument("--out", default="새영상.mp4", help="결과 파일명 (watch 폴더에 저장)")
    ap.add_argument("--mp", type=float, default=1.0, help="화질 (0.4=초안, 1.0=고화질)")
    ap.add_argument("--sec", type=float, default=5.0, help="장면당 길이(초)")
    ap.add_argument("--seed", type=int, default=424200)
    ap.add_argument("--draft", action="store_true", help="빠른 저화질 (--mp 0.4)")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.draft:
        args.mp = 0.4

    if not ensure_server():
        sys.exit(1)
    if args.check:
        return

    prompts = []
    if args.scenes:
        p = Path(args.scenes)
        if not p.is_absolute():
            p = HERE / p
        prompts = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                   if l.strip() and not l.startswith("#")]
    elif args.prompt:
        prompts = [args.prompt]
    else:
        log("할 일이 없습니다. --scenes 또는 --prompt 를 주세요 (--help 로 사용법 확인)")
        return

    WATCH.mkdir(parents=True, exist_ok=True)
    log(f"=== 장면 {len(prompts)}개 · 화질 {args.mp}MP · 장면당 {args.sec}초 ===")
    files = []
    for i, text in enumerate(prompts, 1):
        f = generate(text + NOTEXT, args.seed + i * 613, args.mp, args.sec,
                     f" [{i}/{len(prompts)}]")
        if f:
            files.append(f)
    if not files:
        log("만들어진 영상이 없습니다.")
        sys.exit(1)

    out = WATCH / args.out
    if concat(files, out):
        log(f"\n=== 완성 — uploader\\watch\\{out.name} ===")
        log("업로드.bat 을 눌러 올리면 됩니다")
    else:
        log("이어붙이기 실패 — 개별 장면은 콤피 output 폴더에 있습니다")


if __name__ == "__main__":
    main()
