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

    top_k: int = 3              # 요구 항목마다 가져올 근거 조각 수
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
