"""에이전트와 팀의 설계도 형식.

설계도는 YAML 파일(teams/*.yaml)로 저장된다. 사람이 직접 써도 되고, 설계 에이전트가 써도 된다.
이 파일에는 형식만 있고, "좋은 설계인가"는 rules.py 가 따로 검사한다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

ModelAlias = Literal["opus", "sonnet", "haiku"]
Effort = Literal["low", "medium", "high"]


class AgentSpec(BaseModel):
    """에이전트 1명 = 모델 + 지시문 + 도구 + 반복 상한."""

    name: str = Field(description="영문 소문자·숫자·밑줄만. 예: data_scout")
    role: str = Field(description="한 줄 역할 (한국어)")
    why_separate: str = Field(
        default="",
        description="이 에이전트가 왜 따로 맥락을 가져야 하는가. 직함이 아니라 맥락·도구·견제 이유로 쓴다",
    )
    model: ModelAlias = Field(description="opus(어려운 판단) / sonnet(일반 작성·분석) / haiku(단순 정리·검사)")
    effort: Effort = Field(default="medium", description="생각 깊이. low / medium / high")
    tools: list[str] = Field(default_factory=list, description="쓸 도구 이름 목록. 도구 목록에 있는 것만")
    instructions: str = Field(description="이 에이전트의 지시문. 무엇을 보고 무엇을 돌려줄지 구체적으로")
    max_turns: int = Field(default=6, description="모델 호출 상한 (1~12)")


class Stage(BaseModel):
    """단계 1개. 에이전트가 1명이면 혼자, 2명 이상이면 동시에(병렬) 일한다."""

    agents: list[str] = Field(description="이 단계에서 일할 에이전트 이름. 2명 이상이면 동시에 실행")


class ReviewSpec(BaseModel):
    """마지막 단계 결과를 다른 에이전트가 검토하고, 고칠 게 있으면 다시 쓰게 한다."""

    reviewer: str = Field(description="검토 에이전트 이름. 단계(stages)에는 넣지 않는다")
    criteria: list[str] = Field(description="통과 기준 목록")
    max_rounds: int = Field(default=2, description="검토 최대 횟수 (1~3)")


class TeamSpec(BaseModel):
    """팀 설계도."""

    name: str = Field(description="팀 이름. 영문 소문자·숫자·하이픈. 예: weekly-report-review")
    situation: str = Field(description="이 팀이 맡는 상황·일 (한국어)")
    why_not_single: str = Field(
        default="",
        description="에이전트 1명으로 안 되는 이유. 1명 팀이면 빈 문자열",
    )
    agents: list[AgentSpec]
    stages: list[Stage] = Field(description="실행 순서. 앞 단계 결과가 다음 단계로 넘어간다")
    review: Optional[ReviewSpec] = Field(default=None, description="검토 루프. 필요 없으면 null")
    budget_usd: float = Field(default=0.5, description="이 팀 1회 실행 예산(달러). 넘으면 자동 중단")

    def agent(self, name: str) -> AgentSpec:
        for a in self.agents:
            if a.name == name:
                return a
        raise KeyError(name)

    def has_agent(self, name: str) -> bool:
        return any(a.name == name for a in self.agents)

    def shape(self) -> str:
        """구조를 사람이 읽는 말로 (코드가 계산)."""
        parts = []
        for st in self.stages:
            n = len(st.agents)
            parts.append(f"동시 {n}명" if n > 1 else "1명")
        text = " → ".join(parts) if parts else "(단계 없음)"
        if self.review:
            text += f" → 검토 루프(최대 {self.review.max_rounds}회)"
        return text


class SpecError(Exception):
    pass


def _str_presenter(dumper, data):
    # 여러 줄 문자열은 | 블록으로 저장해 사람이 읽고 고치기 쉽게
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(str, _str_presenter)


def team_to_yaml(team: TeamSpec) -> str:
    return yaml.dump(
        team.model_dump(), Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000
    )


def save_team(team: TeamSpec, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(team_to_yaml(team), encoding="utf-8")
    return path


def load_team(path: Path) -> TeamSpec:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SpecError(f"팀 파일이 없습니다: {path}") from None
    except yaml.YAMLError as e:
        raise SpecError(f"YAML 문법 오류: {e}") from None
    if not isinstance(data, dict):
        raise SpecError("팀 파일 맨 위는 '이름: 값' 형태여야 합니다")
    try:
        return TeamSpec.model_validate(data)
    except ValidationError as e:
        lines = []
        for err in e.errors():
            where = ".".join(str(x) for x in err["loc"])
            lines.append(f"- {where}: {err['msg']}")
        raise SpecError("팀 파일 형식 오류:\n" + "\n".join(lines)) from None
