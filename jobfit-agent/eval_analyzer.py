"""공고 분석가 평가: 평가셋의 모든 공고로 분석가를 돌려 정답표와 비교한다.

  python eval_analyzer.py --dry-run   # 가짜 모델로 채점 흐름만 확인 (비용 없음)
  python eval_analyzer.py             # 실제 분석가로 채점 (API 키 필요, 공고 수만큼 호출)

결과는 eval/results/ 에 날짜별로 남긴다. 지시문을 바꿀 때마다 돌려서 나아졌는지 숫자로 본다.
"""
import argparse
import json
import os
import sys
from datetime import datetime

from jobfit import evaluate as ev
from jobfit.config import ROOT, Config
from jobfit.posting import read_posting


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        from jobfit.fake import FakeLLM
        llm, label = FakeLLM(), "가짜 모델"
    else:
        from run import load_env
        load_env(ROOT / ".env")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY 가 없습니다. --dry-run 으로 흐름만 확인할 수 있습니다.")
            return 1
        from jobfit.llm import ClaudeLLM
        cfg = Config()
        llm, label = ClaudeLLM(cfg), f"{cfg.analyzer.model} · 생각 강도 {cfg.analyzer.effort}"

    rows, details, recalls, precisions, type_hits = [], [], [], [], []
    for ans_path in sorted((ROOT / "eval" / "answers").glob("*.json")):
        pid = ans_path.stem
        answer = json.loads(ans_path.read_text(encoding="utf-8"))
        posting = read_posting(ROOT / "eval" / "postings" / f"{pid}.md")
        result = llm.analyze(posting)
        req = ev.requirement_scores(answer["requirements"], result["requirements"])
        company = result.get("company") or {}
        hit = ev.company_type_hit(answer, company)
        recalls.append(req["recall"])
        precisions.append(req["precision"])
        if hit is not None:
            type_hits.append(hit)
        mr = answer.get("mentor_reading") or {}
        rows.append(f"| {pid} | {req['matched']}/{req['gold']} ({ev.pct(req['recall'])}) | "
                    f"{req['matched']}/{req['pred']} ({ev.pct(req['precision'])}) | "
                    f"{mr.get('company_type', '-')} | {company.get('company_type', '-')} ({company.get('confidence', '-')}) | "
                    f"{'-' if hit is None else ('⭕' if hit else '❌')} |")
        details.append("\n".join([
            f"### {pid}",
            f"- 놓친 정답 항목: {'; '.join(req['missed']) or '없음'}",
            f"- 정답에 없는 항목: {'; '.join(req['extra']) or '없음'}",
            f"- 멘토 지표: {', '.join(mr.get('metrics_they_care_about') or []) or '-'}",
            f"- 분석가 지표: {', '.join(company.get('key_metrics') or []) or '-'}",
            f"- 분석가 근거 문구: {' / '.join(company.get('basis') or []) or '-'}",
        ]))

    def avg(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None

    now = datetime.now()
    report = "\n\n".join([
        f"# 공고 분석가 평가 ({now:%Y-%m-%d %H:%M}, {label})",
        f"평균 재현율 {ev.pct(avg(recalls))} · 평균 정밀도 {ev.pct(avg(precisions))} · "
        f"회사 유형 일치 {sum(type_hits)}/{len(type_hits)} (멘토가 해석한 공고만)",
        "| 공고 | 재현율 | 정밀도 | 멘토 유형 | 분석가 유형 (확신도) | 일치 |\n|---|---|---|---|---|---|\n" + "\n".join(rows),
        "## 공고별 상세 (사람이 확인할 것)",
        *details,
        "## 비용\n" + llm.cost_summary(),
    ])
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "-dry" if args.dry_run else ""
    out = out_dir / f"analyzer-{now:%Y%m%d-%H%M}{suffix}.md"
    if not args.dry_run:
        out.write_text(report, encoding="utf-8")
    print(report.split("## 공고별 상세")[0])
    print("저장: " + (str(out) if not args.dry_run else "(dry-run 은 저장하지 않음)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
