# 집가 마케팅 파이프라인 — 관통 실행
#   python run.py --account=a          M1~M6 를 순서대로 실행
#   python run.py --account=a --export ready 항목을 발행용 폴더로 내보내기
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from lib.common import ensure_dirs
from m1_input import m1
from m2_transcribe import m2
from m3_clips import m3
from m4_texts import m4
from m5_links import m5
from m6_queue import m6


def main():
    ap = argparse.ArgumentParser(description="집가 마케팅 자동화 파이프라인")
    ap.add_argument("--account", default="a", help="계정 아이디 (accounts/*.json 파일명)")
    ap.add_argument("--export", action="store_true", help="ready 항목을 export/ 폴더로 내보내기")
    args = ap.parse_args()

    ensure_dirs()

    if args.export:
        m6.export()
        return

    stages = [
        ("M1 입력·정규화", lambda: m1.run()),
        ("M2 전사·자막", lambda: m2.run()),
        ("M3 클립 생성", lambda: m3.run()),
        ("M4 텍스트 생성", lambda: m4.run(args.account)),
        ("M5 링크 생성", lambda: m5.run(args.account)),
        ("M6 발행 큐", lambda: m6.run(args.account)),
    ]

    print(f"=== 집가 마케팅 파이프라인 · 계정 '{args.account}' ===\n")
    for name, fn in stages:
        print(f"▶ {name}")
        ok = fn()
        if not ok:
            print(f"\n중단: {name} 에서 멈췄습니다. 위 경고를 확인하세요.")
            sys.exit(1)
        print()

    print("=== 6단계 통과 ===")
    print("다음 할 일:")
    print("  1. data/clips/manifest.csv 를 열어 쓸 클립 고르기")
    print("  2. data/queue.csv 에서 올릴 항목의 status 를 ready 로 바꾸기")
    print("  3. python run.py --export  → export/ 폴더의 영상+문구를 각 앱에 업로드")


if __name__ == "__main__":
    main()
