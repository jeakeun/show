# ComfyUI 완성본 가져오기 — ComfyUI output 폴더의 새 영상을 watch/ 로 복사합니다.
#   사용법: 가져오기.bat 더블클릭
#   지난번 가져간 이후에 새로 생긴 영상만 가져오며, webm 은 mp4 로 자동 변환합니다.
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCH = HERE / "watch"
STATE = HERE / ".comfy_fetch_state.json"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}

# ComfyUI 가 완성본을 저장하는 폴더 (자동 탐색 순서)
OUTPUT_CANDIDATES = [
    Path(r"C:\Users\User\AppData\Local\Comfy-Desktop\ComfyUI-Shared\output"),
    Path(r"D:\aivideos\ga\ComfyUI\output"),
]


def find_output_dir():
    for p in OUTPUT_CANDIDATES:
        if p.exists():
            return p
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    WATCH.mkdir(exist_ok=True)

    out_dir = find_output_dir()
    if not out_dir:
        print("[오류] ComfyUI output 폴더를 찾지 못했습니다.")
        print("       comfy_fetch.py 상단의 OUTPUT_CANDIDATES 에 폴더 경로를 추가하세요.")
        return

    last = 0.0
    if STATE.exists():
        last = json.loads(STATE.read_text(encoding="utf-8")).get("last", 0.0)

    new_videos = sorted(
        (p for p in out_dir.rglob("*")
         if p.suffix.lower() in VIDEO_EXT and p.stat().st_mtime > last),
        key=lambda p: p.stat().st_mtime)

    if not new_videos:
        print(f"새로 만든 영상이 없습니다.\n(보는 곳: {out_dir})")
        print("ComfyUI 에서 영상을 만든 뒤 다시 실행하세요.")
        return

    print(f"=== ComfyUI 새 영상 {len(new_videos)}개 발견 ===\n")
    copied = 0
    for v in new_videos:
        dst = WATCH / (v.stem + ".mp4")
        n = 1
        while dst.exists():
            n += 1
            dst = WATCH / f"{v.stem}_{n}.mp4"
        if v.suffix.lower() == ".webm":
            print(f"  변환 중: {v.name} → {dst.name}")
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", str(v), "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", str(dst)],
                capture_output=True)
            if not dst.exists():
                print(f"  [경고] 변환 실패, 원본 그대로 복사: {v.name}")
                shutil.copy2(v, WATCH / v.name)
        else:
            shutil.copy2(v, dst)
            print(f"  가져옴: {v.name} → watch\\{dst.name}")
        copied += 1

    STATE.write_text(json.dumps({"last": time.time()}), encoding="utf-8")
    print(f"\n=== 완료 — {copied}개를 watch 폴더로 가져왔습니다 ===")
    print("다음 단계:")
    print("  1. (선택) 같은 이름의 .txt 로 문구 넣기")
    print("  2. 업로드.bat 더블클릭 → 3개 채널 업로드")


if __name__ == "__main__":
    main()
