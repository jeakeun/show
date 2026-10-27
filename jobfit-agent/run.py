"""실행: 공고 파일 하나로 맞춤 지원서 초안을 만든다.

  python run.py eval/postings/001.md              # 실제 실행 (JOBFIT_API_KEY 필요)
  python run.py eval/postings/001.md --dry-run    # 가짜 모델로 흐름만 확인 (비용 없음)
  python run.py eval/postings/001.md --baseline   # 에이전트 1개짜리 기준선 (비교용)
"""
import argparse
import os
import sys
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from jobfit.career import Retriever, load_career
from jobfit.config import ROOT, Config, api_key
from jobfit.graph import build
from jobfit.posting import read_posting


def load_env(path: Path) -> None:
    """jobfit-agent/.env 의 KEY=VALUE 를 환경 변수로 읽는다 (이미 있으면 덮어쓰지 않음)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def show(payload: dict) -> None:
    print("\n" + "=" * 60)
    print(f"적합도 {payload['fit_score']}점 (코드 계산)\n")
    print("[회사 읽기 — AI 추정, 행간은 직접 다시 확인]\n" + payload.get("company", "") + "\n")
    print(payload["fit_table"] + "\n")
    print(payload["draft"])
    if payload["issues"]:
        print("\n[남은 검증 의견]")
        for i in payload["issues"]:
            print(f"- [{i['problem']}] {i['sentence']} → {i['detail']}")
    print("=" * 60)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("posting", help="공고 파일 (예: eval/postings/001.md)")
    ap.add_argument("--dry-run", action="store_true", help="가짜 모델로 흐름만 확인")
    ap.add_argument("--baseline", action="store_true", help="에이전트 1개짜리 기준선으로 실행")
    args = ap.parse_args()

    cfg = Config()
    posting_path = Path(args.posting)
    posting = read_posting(posting_path)
    chunks = load_career(cfg)
    retriever = Retriever(chunks, cfg.match_words)
    print(f"경력 문서 조각 {len(chunks)}개를 색인했습니다.")

    if args.dry_run:
        from jobfit.fake import FakeLLM
        llm = FakeLLM()
    else:
        load_env(ROOT / ".env")
        if not api_key():
            print("API 키가 없습니다. 환경 변수 JOBFIT_API_KEY (또는 jobfit-agent/.env) 에 넣거나 --dry-run 으로 실행하세요.")
            return 1
        from jobfit.llm import ClaudeLLM
        llm = ClaudeLLM(cfg)

    if args.baseline:
        # 기준선: 근거 검색 없이 모든 조각을 근거로 주고 한 번에 쓰게 한다
        from jobfit.batch import all_sources
        print(llm.baseline(posting, all_sources(chunks)))
        print("\n[비용]\n" + llm.cost_summary())
        return 0

    app = build(llm, retriever, cfg, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": posting_path.stem}}
    result = app.invoke({"posting_id": posting_path.stem, "posting": posting}, config)
    while "__interrupt__" in result:
        show(result["__interrupt__"][0].value)
        answer = input("\n승인 / 폐기 / 수정할 점을 적어 주세요 > ")
        result = app.invoke(Command(resume=answer), config)

    state = app.get_state(config).values
    print(f"\n결정: {state.get('decision')}")
    if state.get("output_path"):
        print(f"저장: {state['output_path']}")
    print(f"쓴 횟수(마지막 라운드): {state.get('attempts')} · 근거 조각 {len(state.get('sources') or {})}개")
    print("\n[비용]\n" + llm.cost_summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
