# 콤피(ACE-Step)로 배경음악 만들기
#   실행: python make_music.py                    (기본 분위기로 1곡)
#         python make_music.py --tags "lo-fi, chill" --sec 40
#         python make_music.py --out 밝은버전.mp3
#
# 결과는 zipga-marketing/bgm/ 에 저장됩니다.
# bgm 폴더에 파일이 있으면 영상 만들 때 자동으로 배경음으로 깔립니다.
import argparse
import json
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import comfy  # 같은 폴더의 comfy.py (서버 자동 기동 재사용)

HERE = Path(__file__).resolve().parent
BGM_DIR = HERE.parent / "bgm"
MODEL = "ace_step_v1_3.5b.safetensors"

# 집가 톤에 맞춘 기본 분위기 — 밝지만 과하지 않게, 가사 없음
DEFAULT_TAGS = ("lo-fi, chill, warm, gentle, night city, soft synth, "
                "light percussion, instrumental, no vocals, relaxed, hopeful")


def build_workflow(tags, seconds, seed):
    """ACE-Step 음악 생성 워크플로 (API 형식)."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": MODEL}},
        "2": {"class_type": "EmptyAceStepLatentAudio",
              "inputs": {"seconds": float(seconds), "batch_size": 1}},
        "3": {"class_type": "TextEncodeAceStepAudio",
              "inputs": {"tags": tags, "lyrics": "", "lyrics_strength": 1.0,
                         "clip": ["1", 1]}},
        "4": {"class_type": "ConditioningZeroOut",
              "inputs": {"conditioning": ["3", 0]}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": int(seed), "steps": 50, "cfg": 5.0,
                         "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0, "model": ["1", 0],
                         "positive": ["3", 0], "negative": ["4", 0],
                         "latent_image": ["2", 0]}},
        "6": {"class_type": "VAEDecodeAudio",
              "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveAudioMP3",
              "inputs": {"filename_prefix": "audio/zipga_bgm",
                         "quality": "V0", "audio": ["6", 0]}},
    }


def generate(tags, seconds, seed):
    wf = build_workflow(tags, seconds, seed)
    req = urllib.request.Request(
        comfy.HOST + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
        headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    pid = res.get("prompt_id")
    if not pid:
        print(f"[실패] 큐 등록 안 됨: {res}")
        return None

    print(f"음악 생성 중... ({seconds}초 분량)")
    start = time.time()
    while time.time() - start < 1800:
        time.sleep(8)
        try:
            hist = json.loads(urllib.request.urlopen(
                comfy.HOST + f"/history/{pid}", timeout=15).read().decode())
        except Exception:
            continue
        if pid not in hist:
            continue
        entry = hist[pid]
        st = entry.get("status", {})
        if not st.get("completed"):
            if st.get("status_str") == "error":
                msgs = st.get("messages", [])
                for m in msgs[-3:]:
                    print("  ", json.dumps(m, ensure_ascii=False)[:300])
                return None
            continue
        for node_out in entry.get("outputs", {}).values():
            for item in node_out.get("audio", []) + node_out.get("images", []):
                f = comfy.OUT_DIR / item.get("subfolder", "") / item["filename"]
                if f.exists():
                    print(f"  완료 ({time.time() - start:.0f}초) — {f.name}")
                    return f
        print("[실패] 결과 파일을 못 찾음")
        return None
    print("[실패] 시간 초과")
    return None


def main():
    ap = argparse.ArgumentParser(description="콤피로 배경음악 만들기")
    ap.add_argument("--tags", default=DEFAULT_TAGS, help="원하는 분위기 (영어)")
    ap.add_argument("--sec", type=float, default=45, help="길이(초)")
    ap.add_argument("--seed", type=int, default=777)
    ap.add_argument("--out", default="집가_배경음악.mp3", help="저장할 파일명")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    model_path = comfy.SHARED / "models" / "checkpoints" / MODEL
    if not model_path.exists():
        print(f"[오류] 음악 모델이 없습니다: {model_path}")
        print("       ACE-Step 모델을 먼저 받아야 합니다.")
        sys.exit(1)

    if not comfy.ensure_server():
        sys.exit(1)

    print(f"분위기: {args.tags}")
    f = generate(args.tags, args.sec, args.seed)
    if not f:
        sys.exit(1)

    BGM_DIR.mkdir(exist_ok=True)
    dst = BGM_DIR / args.out
    shutil.copy2(f, dst)
    print(f"\n=== 완성 ===\n  {dst}")
    print("  이제 영상을 다시 만들면 배경음으로 자동으로 깔립니다.")


if __name__ == "__main__":
    main()
