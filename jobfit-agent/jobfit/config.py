"""설정: 역할별 모델과 생각 강도, 경력 문서 위치, 한도. 바꿀 때는 여기만 고친다."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # jobfit-agent/
SHOW_ROOT = ROOT.parent                          # 지금은 show 저장소 안에 있음

KEY_NAMES = ("JOBFIT_API_KEY", "ANTHROPIC_API_KEY")


def api_key() -> str | None:
    """JOBFIT_API_KEY 를 먼저 본다. 클라우드 세션은 ANTHROPIC_API_KEY 를 Claude Code 자체용으로 관리해서
    사용자가 넣은 값이 빠지기 때문이다. 이름을 따로 두면 다른 자동화의 키와도 섞이지 않는다."""
    return next((os.environ[k] for k in KEY_NAMES if os.environ.get(k)), None)


@dataclass(frozen=True)
class Role:
    model: str
    effort: str        # low | medium | high | xhigh | max (생각을 얼마나 깊게 할지)
    max_tokens: int    # 생각 토큰까지 포함한 출력 한도. 낮게 잡으면 답이 잘린다 (유튜브 회고 9/13 사건)


# 근거로 쓸 경력 문서와 그 종류. "운영" = 실제로 운영한 경험, "학습" = 공부하며 실험한 것.
# 검증가가 "학습을 실무처럼" 쓴 문장을 잡을 때 이 구분을 쓴다.
DEFAULT_SOURCES = (
    ("README.md", "운영"),
    ("docs/멀티에이전트/02-내-설계결정-기록.md", "운영"),
    ("docs/멀티에이전트/03-LangChain-LangGraph-LangFlow.md", "학습"),
    ("docs/멀티에이전트/04-RAG.md", "학습"),
    ("docs/멀티에이전트/05-레거시-시스템-연계.md", "학습"),
)

# 근거로 쓰면 안 되는 부분 (2-2 단계, 2026-10-27). 001 재현에서 LangChain 질문에 가장 높게 잡힌 "운영" 조각이
# "아직 약한 곳"(프레임워크 실전 경험이 없다는 목록)과 이 프로젝트 자신(개발 중)이었다.
# (문서, 절 제목에 든 말, 바꿀 종류 또는 None=뺌, 이유)
SOURCE_RULES = (
    ("README.md", "이 저장소 구조", None, "폴더 지도. 경력이 아니다"),
    ("docs/멀티에이전트/02-내-설계결정-기록.md", "아직 약한 곳", None, "없는 경험 목록. 키워드가 겹쳐 근거로 잡혔다"),
    ("README.md", "market-compass", "학습", "개발 중인 프로젝트는 운영 경험이 아니다"),
    ("docs/멀티에이전트/02-내-설계결정-기록.md", "ADR-10", "학습", "market-compass (개발 중)"),
)
# 표 한 줄·인용 한 줄에서 뺄 말. 운영 중인 프로젝트 표에 개발 중인 것이 한 줄씩 섞여 있다.
# "마지막 갱신" 줄은 커밋마다 바뀌어서, 넣어 두면 README를 고칠 때마다 근거가 달라진다.
DROP_LINES = ("jobfit-agent", "webdrama", "market-compass", "마지막 갱신")


@dataclass(frozen=True)
class Config:
    # 처음엔 모든 역할이 같은 모델이고 생각 강도만 다르다.
    # 더 싼 모델로 바꿀지는 평가셋으로 재본 뒤 정한다 (설계 결정 J-12).
    analyzer: Role = Role("claude-opus-5-5", "low", 16000)
    writer: Role = Role("claude-opus-5-5", "high", 64000)
    verifier: Role = Role("claude-opus-5-5", "medium", 16000)

    sources: tuple = DEFAULT_SOURCES
    source_root: Path = SHOW_ROOT
    output_dir: Path = ROOT / "private" / "output"   # 깃 제외 폴더

    source_rules: tuple = SOURCE_RULES
    drop_lines: tuple = DROP_LINES

    # 검색 방식 (2-2). 셋 다 끄면 2-1 단계 방식과 같다. eval_retrieval.py 가 하나씩 켜 보며 비교한다.
    clean_sources: bool = True  # 근거가 아닌 부분 빼기
    match_words: bool = True    # 영어는 단어 통째로 + 동의어 사전
    per_kind: int = 2           # 운영·학습 문서에서 각각 최소 몇 개씩 가져올지 (0이면 상위 k개만)

    top_k: int = 3              # 요구 항목마다 가져올 근거 조각 수 (종류 상관없이 점수 순)
    max_requirements: int = 15  # 요구 항목이 너무 많으면 자름 (병렬 호출 수 상한)
    max_rewrites: int = 2       # 검증 실패 시 다시 쓰기 상한 (처음 1번 + 다시 2번)
    max_human_revisions: int = 2
    chunk_size: int = 600
    chunk_overlap: int = 80


# 비용 계산용 단가 (US$ / 100만 토큰, 2026-10 기준). 실제 청구액은 콘솔에서 확인한다.
PRICE_PER_MTOK = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
}
