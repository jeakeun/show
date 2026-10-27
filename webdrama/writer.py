# -*- coding: utf-8 -*-
"""Claude 로 시리즈 설정(바이블)과 회차 대본·장면 지시문을 만든다.

Opus 5.5 + 서버 측 거절 대체(fallbacks="default", yt-auto src/llm.py 와 같은 방식) + JSON 스키마 출력.
"""
import json
import math
import re

import anthropic

from common import CONFIG, load_env

FALLBACK_BETA = "server-side-fallback-2026-07-01"

STR = {"type": "string"}
INT = {"type": "integer"}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _arr(item: dict) -> dict:
    return {"type": "array", "items": item}


BIBLE_SCHEMA = _obj({
    "title": STR,
    "logline": STR,
    "genre": STR,
    "tone": STR,
    "visual_style_en": STR,
    "characters": _arr(_obj({
        "id": STR, "name": STR, "role": STR, "age": INT,
        "personality": STR, "look_en": STR, "outfit_en": STR, "voice_en": STR,
    })),
    "locations": _arr(_obj({"id": STR, "name": STR, "look_en": STR})),
    "season_beats": _arr(STR),
    "hashtags": _arr(STR),
})

EPISODE_SCHEMA = _obj({
    "title": STR,
    "summary": STR,
    "payoff": STR,
    "cliffhanger": STR,
    "shots": _arr(_obj({
        "seconds": INT,
        "location_id": STR,
        "character_ids": _arr(STR),
        "action_ko": STR,
        "prompt_en": STR,
        "dialogue": _arr(_obj({"speaker": STR, "line": STR})),
    })),
    "caption_ko": STR,
    "hashtags": _arr(STR),
})


def _call(system: str, user: str, schema: dict) -> dict:
    load_env()
    client = anthropic.Anthropic()
    kw = dict(
        model=CONFIG["model"],
        max_tokens=32000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": CONFIG.get("effort", "medium"),
                       "format": {"type": "json_schema", "schema": schema}},
    )
    with client.beta.messages.stream(betas=[FALLBACK_BETA], fallbacks="default", **kw) as st:
        msg = st.get_final_message()
    if msg.stop_reason == "refusal":
        raise SystemExit("Claude 가 이 요청을 거절했습니다. 로그라인이나 설정을 순화해서 다시 시도하세요.")
    if msg.stop_reason == "max_tokens":
        raise SystemExit("응답이 길이 제한에 걸려 잘렸습니다. 다시 실행해 주세요.")
    text = next(b.text for b in msg.content if b.type == "text")
    return json.loads(text)


def _system() -> str:
    smax = CONFIG.get("shot_seconds_max", 10)
    model = CONFIG.get("video_tool", {}).get("model", "AI 영상 모델")
    return f"""너는 한국 세로형 숏드라마(유튜브 쇼츠·인스타 릴스·틱톡) 전문 작가이자 AI 영상 연출가다.
영상은 {model} 로 장면마다 최대 {smax}초씩 생성해 이어 붙인다. 인물 기준 사진을 참조로 함께 넣는다. 그래서 다음을 지킨다.
- 등장인물은 회차당 3~4명 이하, 장소는 1~2곳. 인물이 많고 장소가 자주 바뀌면 AI 영상의 얼굴·배경이 흔들린다.
- 한 장면 = 한 동작·한 감정. 큰 액션, 군중, 글자가 화면에 나오는 장면(간판·문자메시지 화면)은 피한다.
- 말하는 사람만 계속 비추지 말고, 듣는 사람·옆 사람의 반응 장면을 섞는다.
- 실존 인물·연예인·기존 작품 캐릭터·브랜드 로고는 절대 쓰지 않는다.
- 영상 모델의 안전 필터에 걸리지 않게 한다: 때리기·밀치기 같은 신체 폭력, 입술을 깨물기·핥기 같은 입술 클로즈업 묘사,
  몸매를 강조하는 표현, 키스 클로즈업은 쓰지 않는다. 응징은 말·증거·지위·제3자 등장으로 한다.
- 매화 한 편 안에 시청자가 받는 '보상'이 반드시 한 번 있어야 한다. 보상은 셋 중 하나다:
  사이다(무시·모함한 사람이 증거·실력·인맥 앞에서 무너짐), 설렘(두 주인공 사이의 확실한 심쿵 순간), 웃음(차가운 인물이 망가지는 반전 코미디).
  다음 화로 끊기만 하고 보상이 없는 회차는 실패다.
- 구조: 0~3초 상대를 대놓고 무시·도발하는 한마디로 시작 → 갈등은 전체의 40% 안에 끝 → 보상 → 마지막 5초는 두 주인공 관계에 대한 떡밥.
- 보상 종류와 반전 방식을 앞 회차와 돌려 쓴다. 매화 '숨은 실력으로 반전'만 반복하지 않는다.
- 회차마다 이야기가 반드시 앞으로 나아간다. 앞 회차와 같은 사건·같은 대사·같은 반전을 되풀이하지 않는다."""


def make_bible(logline: str) -> dict:
    n = CONFIG.get("season_episodes", 30)
    user = f"""다음 로그라인으로 시즌 1 ({n}화, 회당 약 {CONFIG['episode_seconds']}초) 시리즈 설정을 만들어라.

로그라인: {logline}

- title: 한국어 시리즈 제목 (짧고 자극적으로)
- visual_style_en: 모든 장면 프롬프트 앞에 붙일 영어 화풍 설명 (예: cinematic Korean drama, vertical 9:16, soft film lighting ...)
- characters: 주요 인물 3~5명. id 는 영문 소문자(예: seoyeon). look_en 은 얼굴·헤어·체형을 매번 똑같이 그릴 수 있게 구체적인 영어로.
  outfit_en 은 기본 의상. voice_en 은 목소리 특징 영어 한 줄.
- locations: 자주 쓸 장소 3~5곳. id 는 영문 소문자.
- season_beats: 정확히 {n}개. 각 회차에서 일어날 핵심 사건 한 줄씩. 5화마다 큰 반전, 마지막 화는 시즌2 떡밥.
- hashtags: 공용 해시태그 5~8개 (# 포함)."""
    return _call(_system(), user, BIBLE_SCHEMA)


def make_episode(bible: dict, n: int, previous: list[dict]) -> dict:
    beats = bible["season_beats"]
    beat = beats[n - 1] if n <= len(beats) else "시즌 이후 이야기: 앞 내용을 이어 새 갈등을 시작"
    so_far = "\n".join(f"{p['n']}화 「{p['title']}」" + (f" [보상: {p['payoff']}]" if p.get("payoff") else "")
                       + f": {p['summary']}" for p in previous) or "(첫 화)"
    sec = CONFIG["episode_seconds"]
    smax = CONFIG.get("shot_seconds_max", 10)
    model = CONFIG.get("video_tool", {}).get("model", "AI 영상 모델")
    smin = min(4, smax)
    lo = math.ceil(sec / smax)          # 가장 긴 장면으로 채워도 필요한 개수
    hi = max(lo + 2, sec // 6 + 1)      # 장면이 짧아도 이 정도면 충분
    user = f"""시리즈 설정:
{json.dumps({k: bible[k] for k in ('title', 'logline', 'genre', 'tone', 'visual_style_en', 'characters', 'locations')}, ensure_ascii=False, indent=1)}

지금까지 줄거리:
{so_far}

이번 {n}화의 핵심 사건: {beat}
(핵심 사건은 큰 줄기다. 이 사건을 지키되, 한 편 안에 보상이 들어가도록 장면을 짠다.)

{n}화 대본을 써라.
- title: 이번 화 부제만 (시리즈 제목·화수는 빼고, 15자 이내). 썸네일 문구처럼 궁금하게.
- 전체 {sec}초 안팎. 장면(shots) {lo}~{hi}개, 장면 하나는 {smin}~{smax}초(seconds 는 정수).
- location_id, character_ids 는 설정에 있는 id 만 쓴다.
- action_ko: 사람이 읽을 장면 설명 한 줄.
- prompt_en: {model} 에 그대로 넣을 영어 프롬프트. 순서: 화풍 → 장소 모습 → 인물 외모(look_en+outfit_en 그대로 반복) → 동작·표정 → 카메라(샷 크기·움직임) → 소리.
  대사가 있으면 인물의 voice_en 을 괄호로 붙여 'She (clear bright young female voice) says in Korean: "(한국어 대사)"' 처럼 영어 문장 안에 한국어 대사를 따옴표로 넣는다.
  화면에 글자·자막을 넣으라고 하지 않는다. 안전 필터 규칙(신체 폭력·입술 클로즈업·몸매 강조 금지)을 지킨다.
- dialogue: 그 장면의 한국어 대사 (자막용). 장면당 0~2줄, 한 줄 25자 이내. 대사가 장면 길이에 비해 너무 길면 안 된다.
- summary: 다음 화 작가가 읽을 이번 화 줄거리 2~3문장.
- payoff: 이번 화의 보상 종류(사이다/설렘/웃음)와 그 순간을 한 줄로. 예: "사이다: 서연이 메일 수정 기록을 띄워 유나의 모함을 뒤집음".
- cliffhanger: 마지막 5초 떡밥 한 줄.
- caption_ko: 업로드 설명 문구 2~3줄 (시청자에게 말 걸듯, 결말 스포일러 금지, 댓글 유도 한 줄 포함).
- hashtags: 이번 화 전용 3~5개 (# 포함)."""
    ep = _call(_system(), user, EPISODE_SCHEMA)
    # 업로드 제목에 시리즈명·화수를 따로 붙이므로 부제만 남긴다
    t = ep["title"].replace(bible["title"], "").strip()
    ep["title"] = re.sub(r"^\d+\s*화\s*[-·:|]?\s*", "", t).strip(" -·:|") or ep["title"]
    ids_c = {c["id"] for c in bible["characters"]}
    ids_l = {l["id"] for l in bible["locations"]}
    for s in ep["shots"]:
        s["seconds"] = max(smin, min(smax, int(s["seconds"])))
        s["character_ids"] = [c for c in s["character_ids"] if c in ids_c]
        if s["location_id"] not in ids_l:
            s["location_id"] = ""
    return ep
