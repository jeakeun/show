"""지원서 변경 테스트 실행.

  python batch_run.py --dry-run                  # 가짜 모델로 흐름만 (비용 없음, 저장 안 함)
  python batch_run.py --only 008,009,010         # 고른 공고만 실제 모델로
  python batch_run.py                            # 평가셋 공고 전체를 실제 모델로
  python batch_run.py --max-usd 3                # 비용 상한 (기본 5달러, 넘으면 멈춤)
  python batch_run.py --baseline --only 001      # 기준선: 에이전트 1개가 한 번에 쓰기 (비교용)

결과는 eval/results/batch-날짜/ (기준선은 baseline-날짜/) 에 공고별 파일과 요약으로 남는다. 승인·지원 이력 등록은 하지 않는다.
상한은 공고를 새로 시작하기 전에만 본다. 공고 하나를 도는 중에는 멈추지 않으므로 마지막 공고만큼 넘을 수 있다.
"""
import argparse
import sys
from datetime import datetime

from jobfit.batch import (all_sources, report_baseline_one, report_one, run_baseline_one, run_one,
                          summary, summary_baseline)
from jobfit.career import Retriever, load_chunks
from jobfit.config import ROOT, Config, api_key


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="쉼표로 구분한 공고 번호 (예: 008,009)")
    ap.add_argument("--max-usd", type=float, default=5.0)
    ap.add_argument("--baseline", action="store_true", help="에이전트 1개짜리 기준선으로 실행")
    args = ap.parse_args()

    cfg = Config()
    if args.dry_run:
        from jobfit.fake import FakeLLM
        llm, label = FakeLLM(), "가짜 모델"
    else:
        from run import load_env
        load_env(ROOT / ".env")
        if not api_key():
            print("API 키가 없습니다. 환경 변수 JOBFIT_API_KEY (또는 jobfit-agent/.env) 에 넣거나 --dry-run 으로 실행하세요.")
            return 1
        from jobfit.llm import ClaudeLLM
        llm, label = ClaudeLLM(cfg), f"작성자 {cfg.writer.model} · 생각 강도 {cfg.writer.effort}"

    wanted = {x.strip() for x in args.only.split(",") if x.strip()}
    postings = [p for p in sorted((ROOT / "eval" / "postings").glob("*.md")) if not wanted or p.stem in wanted]
    chunks = load_chunks(cfg.sources, cfg.source_root, cfg.chunk_size, cfg.chunk_overlap)
    if args.baseline:
        sources = all_sources(chunks)
        run, report, summarize, prefix = (lambda p: run_baseline_one(llm, sources, p)), report_baseline_one, summary_baseline, "baseline"
        label = "기준선 · " + label
    else:
        retriever = Retriever(chunks)
        run, report, summarize, prefix = (lambda p: run_one(llm, retriever, cfg, p)), report_one, summary, "batch"
    out_dir = ROOT / "eval" / "results" / f"{prefix}-{datetime.now():%Y%m%d-%H%M}"

    results, spent = [], 0.0
    for p in postings:
        if spent >= args.max_usd:
            print(f"비용 상한 US${args.max_usd} 도달 → {p.stem} 부터 멈춤")
            break
        print(f"{p.stem} 진행 중...", flush=True)
        r = run(p)
        spent += r["cost"]
        results.append(r)
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{p.stem}.md").write_text(report(r), encoding="utf-8")

    text = summarize(results, label)
    if not args.dry_run and results:
        (out_dir / "summary.md").write_text(text, encoding="utf-8")
        print(f"저장: {out_dir}")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
