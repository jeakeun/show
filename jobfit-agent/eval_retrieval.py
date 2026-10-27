"""근거 검색 채점: 검색 방식을 하나씩 켜 보며 정답 근거와 비교한다 (2-2 단계). 모델 호출 없음, 비용 없음.

    python eval_retrieval.py            # 결과를 eval/results/retrieval-날짜.md 에 저장
    python eval_retrieval.py --no-save  # 화면에만 출력
    python eval_retrieval.py --ai-judge --estimate   # AI 근거 판정가 채점에 드는 토큰·비용 추정 (토큰 세기는 무료)
    python eval_retrieval.py --ai-judge --dry-run    # 가짜 판정가로 흐름 확인 (비용 없음)
    python eval_retrieval.py --ai-judge              # 실제 판정가로 채점 (API 키 필요, 비용 발생, 공고당 1번 호출)
"""
import argparse
import sys
from datetime import datetime

from jobfit.config import PRICE_PER_MTOK, ROOT, Config, api_key
from jobfit.retrieval_eval import VARIANTS, compare, judge_inputs, load_gold, report, run_ai_judge


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--ai-judge", action="store_true", help="키워드 판정 대신 AI 근거 판정가로 판정 (2-3)")
    ap.add_argument("--estimate", action="store_true", help="--ai-judge 비용만 추정하고 끝냄")
    ap.add_argument("--dry-run", action="store_true", help="--ai-judge 를 가짜 판정가로")
    args = ap.parse_args()
    if args.ai_judge:
        return ai_judge(args)
    text = report(compare())
    print(text)
    if not args.no_save:
        path = ROOT / "eval" / "results" / f"retrieval-{datetime.now():%Y%m%d-%H%M}.md"
        path.write_text(text, encoding="utf-8")
        print(f"저장: {path.relative_to(ROOT)}")
    return 0


def ai_judge(args) -> int:
    from jobfit import prompts
    cfg, gold = Config(), load_gold()
    if args.estimate:
        from jobfit.llm import ClaudeLLM
        client = ClaudeLLM(cfg).client
        total = 0
        for pid, x in judge_inputs(cfg, gold).items():
            reqs = [f["req"] for f in x["found"]]
            user = f"{prompts.evidence_block(x['sources'])}\n\n<요구 항목>\n{prompts.judge_items(reqs, x['candidates'])}\n</요구 항목>"
            n = client.messages.count_tokens(model=cfg.judge.model, system=prompts.JUDGE,
                                             messages=[{"role": "user", "content": user}]).input_tokens
            total += n
            print(f"{pid}: 입력 {n:,} 토큰")
        price = PRICE_PER_MTOK[cfg.judge.model]
        low, high = total * price["input"] / 1e6, (total * price["input"] + 7 * 4000 * price["output"]) / 1e6
        print(f"합계 입력 {total:,} 토큰 → 약 US${low:.2f} ~ {high:.2f} (출력·생각을 공고당 0~4천 토큰으로 가정)")
        return 0
    if args.dry_run:
        from jobfit.fake import FakeLLM
        llm = FakeLLM()
    else:
        if not api_key():
            print("API 키가 없습니다 (JOBFIT_API_KEY 또는 jobfit-agent/.env).")
            return 1
        from jobfit.llm import ClaudeLLM
        llm = ClaudeLLM(cfg)
    results = compare([VARIANTS[0], VARIANTS[-1]], gold)
    results[-1] = ("키워드 판정 (2-2 검색)", results[-1][1])
    results.append(("AI 근거 판정가 + 코드 검사" + (" (가짜)" if args.dry_run else ""), run_ai_judge(llm, cfg, gold)))
    text = report(results, ai_judge=True) + "\n## 호출별 비용\n" + llm.cost_summary() + "\n"
    print(text)
    if not args.no_save and not args.dry_run:
        path = ROOT / "eval" / "results" / f"judge-{datetime.now():%Y%m%d-%H%M}.md"
        path.write_text(text, encoding="utf-8")
        print(f"저장: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
