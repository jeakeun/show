"""근거 검색 채점: 검색 방식을 하나씩 켜 보며 정답 근거와 비교한다 (2-2 단계). 모델 호출 없음, 비용 없음.

    python eval_retrieval.py            # 결과를 eval/results/retrieval-날짜.md 에 저장
    python eval_retrieval.py --no-save  # 화면에만 출력
"""
import argparse
import sys
from datetime import datetime

from jobfit.config import ROOT
from jobfit.retrieval_eval import compare, report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()
    text = report(compare())
    print(text)
    if not args.no_save:
        path = ROOT / "eval" / "results" / f"retrieval-{datetime.now():%Y%m%d-%H%M}.md"
        path.write_text(text, encoding="utf-8")
        print(f"저장: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
