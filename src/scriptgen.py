"""트렌드 데이터를 바탕으로 Claude API로 오리지널 영상 대본을 생성한다."""
import json

import anthropic

from .config import ANTHROPIC_API_KEY, CONFIG, DATA_DIR, load_used_topics

SYSTEM = """당신은 구독자 1000만 명의 지식 채널 '1분호기심'의 크리에이터입니다.
사람들이 무심코 지나치는 궁금증을 잡아내 "아 그래서 그런 거구나!"라는
쾌감을 주는 것이 당신의 시그니처입니다.

[페르소나 말투]
- 친한 형/누나가 신기한 걸 알려주듯 자신감 있고 친근한 구어체 ("~거든요", "~인 거예요", "근데 여기서 반전이 있어요")
- 시청자를 "여러분"으로 부르고, 질문을 던져 대화하듯 진행
- 어려운 개념은 반드시 일상 비유로 변환 (전문용어를 쓰면 바로 쉬운 말로 풀기)

[대본 구조 - 시청 지속률이 생명]
1. 훅 (첫 1~2문장): 충격적 사실, 의외의 숫자, 또는 "여러분 혹시 ~한 적 있으세요?"형 공감 질문.
   절대 인사말이나 서론으로 시작하지 않는다. 첫 문장에서 바로 본론.
2. 전개: 한 문장을 짧게. 8~15초마다 "그런데", "근데 진짜 신기한 건", "여기서 반전" 같은
   패턴 전환으로 이탈을 막는다. 궁금증을 하나 풀면 바로 다음 궁금증을 던진다.
3. 마무리 (반드시 이 순서와 요소를 지킨다):
   ① 여운을 남기는 반전 한 줄 또는 시청자에게 던지는 질문
   ② [필수] 구독 유도 멘트 한 문장 - 반드시 내레이션 대본(음성)에 포함하며,
      "구독"이라는 단어가 대본 텍스트에 명시적으로 들어가야 한다.
      "구독과 좋아요 부탁드립니다" 같은 뻔한 표현은 금지. 그날 주제와 엮어
      자연스럽고 위트 있게, 매일 다르게 쓴다.
      (좋은 예: "내일도 1분 만에 똑똑해지고 싶다면 구독 눌러두세요" /
       "이런 궁금증, 구독하면 매일 아침 하나씩 배달됩니다" /
       "다음 궁금증도 놓치기 싫다면 구독이 답이에요")
   ③ 가능하면 구독 멘트나 마지막 문장이 첫 훅과 이어지게 해서 루프감을 만든다
      (반복 재생 = 알고리즘 최대 가산점. ②와 자연스럽게 결합해도 좋다)

[원칙]
- 특정 영상/크리에이터를 베끼지 않는다. 뉴스 단순 요약 금지.
- 트렌드에서 '사람들이 지금 궁금해하는 심리/원리'를 읽어내 오리지널 지식으로 푼다.
- 확인되지 않은 사실 단정 금지. 특정인 비방, 허위 낚시 금지. 연구/통계는 실제 있는 것만.
- [사실 검증] 주제를 정한 뒤, 대본에 넣을 핵심 사실/수치/연구를 web_search로 1~3회
  검색해 검증한다. 검색으로 확인된 정확한 정보만 대본에 담고, 확인 안 되는 수치는
  "약", "연구에 따르면" 수준으로 완화하거나 뺀다. (정확한 정보 = 채널의 신뢰 자산)
- TTS로 읽히므로 이모지/특수문자/괄호 지문을 대본에 넣지 않는다.

[제목 규칙 - 클릭률이 두 번째 생명]
- 궁금증 격차(curiosity gap)를 만든다: 답을 제목에서 말하지 않는다.
- 숫자, "진짜 이유", "~하면 생기는 일", "99%가 모르는" 같은 검증된 포맷 활용 (남용은 금지)
- 40자 이내, 핵심 키워드를 앞쪽에 배치."""

SHORTS_PROMPT = """오늘의 한국 유튜브 인기 급상승 영상 메타데이터입니다:

{trends}

최근에 이미 다룬 주제 (중복 금지):
{used}

위 트렌드에서 사람들의 관심사를 분석한 뒤, 쇼츠(약 25~30초) 1편의 대본을 만드세요.
대본 길이는 공백 포함 약 {target_chars}자. 짧을수록 완주율이 오르니 절대 늘리지 마세요.

주제 선정 제약: 주제는 주로(10편 중 7~8편) [{topic_focus}] 범위에서 고르고,
가끔(10편 중 2~3편) [{topic_secondary}] 범위의 주제로 변화를 줍니다.
'최근에 이미 다룬 주제' 목록을 보고 보조 주제가 연달아 나오지 않게 조절하세요.
어느 쪽이든 트렌드가 보여주는 '지금 사람들의 관심사'와 연결되는 각도로 잡되,
이 두 범위를 벗어나는 주제는 다루지 않습니다. (주제 일관성 = 알고리즘 추천의 핵심)

아래 JSON만 출력하세요 (다른 텍스트 금지):
{{
  "topic": "주제 한 줄",
  "title": "영상 제목 (40자 이내 훅형 제목, 끝에 #Shorts 포함)",
  "description": "첫 줄: 핵심 키워드가 들어간 요약 1문장. 둘째 줄: 궁금증을 키우는 문장. 마지막 줄: #Shorts #1분호기심 + 주제 해시태그 3개",
  "tags": ["검색용 키워드 태그 10개 내외 (주제 키워드, 연관 검색어, 채널명 포함)"],
  "script": "전체 내레이션 대본",
  "comment": "업로드 직후 채널이 달 참여 유도 댓글 1개 - 시청자가 답하고 싶어지는 그날 주제 관련 질문 (이모지 1개 포함, 60자 이내)",
  "scenes": [
    {{"emoji": "대본 흐름 순서대로 각 구간을 상징하는 이모지 1개", "keyword": "그 구간의 핵심 키워드 (8자 이내)", "mood": "진행 캐릭터의 감정: surprised(놀람)/happy(웃음)/thinking(생각)/neutral 중 구간 내용에 맞는 것"}},
    {{"emoji": "...", "keyword": "... (총 4~5개, 대본을 시간순으로 균등 분할한 구간별)", "mood": "..."}},
    {{"emoji": "마지막 장면은 구독 유도용: 🔔 또는 ❤️", "keyword": "구독 멘트 키워드 (예: 구독 꾹)", "mood": "happy"}}
  ]
}}"""

LONGFORM_PROMPT = """오늘의 한국 유튜브 인기 급상승 영상 메타데이터입니다:

{trends}

최근에 이미 다룬 주제 (중복 금지):
{used}

위 트렌드에서 사람들의 관심사를 분석한 뒤, 8~10분 분량 롱폼 영상 1편의 대본을 만드세요.
대본 총 길이는 공백 포함 약 {target_chars}자이며, 절대 4,500자 미만으로 쓰지 마세요.
(8분 이상이어야 중간광고가 붙어 수익이 크게 늘어납니다 - 길이는 타협 불가)
구조: 도입 훅 → 본론 4~6개 섹션 (섹션마다 새로운 반전/사례로 이탈 방지) → 마무리.
3~4분 지점과 6~7분 지점에 "그런데 진짜 놀라운 건 지금부터예요" 같은
강한 궁금증 재점화 문장을 배치하세요 (중간광고 삽입 지점에서 이탈을 막는 장치).

주제 선정 제약: 주제는 주로 [{topic_focus}] 범위에서 고르고,
가끔 [{topic_secondary}] 범위의 주제로 변화를 줍니다. 트렌드가 보여주는
'지금 사람들의 관심사'와 연결되는 각도로 잡습니다.

아래 JSON만 출력하세요 (다른 텍스트 금지):
{{
  "topic": "주제 한 줄",
  "title": "영상 제목 (50자 이내 훅형 제목, 핵심 키워드 앞배치)",
  "description": "첫 줄: 핵심 키워드가 들어간 요약. 이후 2~3문장으로 내용 소개. 마지막 줄: #1분호기심 + 주제 해시태그 4개",
  "tags": ["태그", "15개", "내외"],
  "script": "전체 내레이션 대본 (섹션 구분 없이 이어지는 하나의 글)",
  "comment": "업로드 직후 채널이 달 참여 유도 댓글 1개 - 시청자가 답하고 싶어지는 질문 (이모지 1개 포함, 60자 이내)",
  "thumbnail_title": "썸네일용 초압축 제목 (12자 이내, 궁금증 극대화, 예: '뇌가 당신을 속이는 법')",
  "scenes": [
    {{"emoji": "대본 흐름 순서대로 각 구간을 상징하는 이모지 1개", "keyword": "그 구간의 핵심 키워드 (10자 이내)", "mood": "진행 캐릭터의 감정: surprised/happy/thinking/neutral 중 구간 내용에 맞는 것"}},
    {{"emoji": "...", "keyword": "... (총 6~8개, 대본을 시간순으로 균등 분할한 구간별)", "mood": "..."}},
    {{"emoji": "마지막 장면은 구독 유도용: 🔔 또는 ❤️", "keyword": "구독 멘트 키워드", "mood": "happy"}}
  ]
}}"""


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"JSON을 찾지 못했습니다: {text[:200]}")
    return json.loads(text[start : end + 1])


def generate_script(trend_items: list[dict], video_type: str,
                    companion: dict | None = None) -> dict:
    """video_type: 'shorts' | 'longform'. 반환: topic/title/description/tags/script dict.

    companion: 같은 날 올라가는 롱폼 정보 {'topic', 'title'}.
    지정되면 쇼츠를 그 롱폼의 예고편으로 작성한다.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY가 없습니다. secrets/.env 에 추가하세요.")

    trends_text = "\n".join(
        f"- [{t['views']:,}회] {t['title']} (채널: {t['channel']}, 태그: {', '.join(t['tags'])})"
        for t in trend_items[:30]
    )
    used = load_used_topics()
    used_text = "\n".join(f"- {t}" for t in used[-30:]) or "(없음)"

    tpl = SHORTS_PROMPT if video_type == "shorts" else LONGFORM_PROMPT
    prompt = tpl.format(
        trends=trends_text,
        used=used_text,
        target_chars=CONFIG[video_type]["target_chars"],
        topic_focus=CONFIG.get("topic_focus", "심리학, 뇌과학, 행동경제학"),
        topic_secondary=CONFIG.get(
            "topic_secondary", "우주, 물리학, 과학적 미스터리, 가상현실, 개인 금융"
        ),
    )

    playbook_file = DATA_DIR / "playbook.md"
    if playbook_file.exists():
        prompt += (
            "\n\n[채널 성과 플레이북 - 우리 채널의 실제 데이터에서 학습한 것. 반영할 것]\n"
            + playbook_file.read_text(encoding="utf-8")
        )

    if companion and video_type == "shorts":
        prompt += f"""

[특별 지시 - 오늘은 롱폼 예고편 쇼츠]
오늘 같은 채널에 롱폼 영상이 함께 올라갑니다.
- 롱폼 제목: {companion['title']}
- 롱폼 주제: {companion['topic']}
이 쇼츠는 위 롱폼과 같은 주제로 만들되, 예고편 역할을 해야 합니다:
가장 강렬한 훅과 핵심 반전 딱 하나만 보여주고, 나머지는 궁금증으로 남기세요.
[필수] 마무리 구독 멘트 대신, 롱폼 유도 멘트 한 문장을 반드시 내레이션 대본(음성)에
포함하세요. "채널"과 "풀버전"(또는 "자세한 이야기")이라는 표현이 대본 텍스트에
명시적으로 들어가야 합니다. 그날 내용과 엮어 자연스럽게:
(예: "이게 왜 그런지 진짜 이유는 채널의 풀버전에서 끝까지 파헤쳤어요" /
 "나머지 반전 세 개는 채널에 올라온 자세한 이야기에서 확인하세요")
마지막 장면(scenes)도 구독 대신 🎬 이모지 + "풀버전은 채널에" 키워드로 구성하세요.
(절대 전체 내용을 요약하지 말 것 - 답을 다 주면 롱폼을 보러 갈 이유가 사라집니다)"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
    last_err = None
    for _ in range(3):
        messages = [{"role": "user", "content": prompt}]
        msg = client.messages.create(
            model=CONFIG["model"],
            max_tokens=16000,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        # 서버측 웹검색이 길어지면 pause_turn으로 멈출 수 있음 → 이어서 재개
        for _resume in range(3):
            if msg.stop_reason != "pause_turn":
                break
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": msg.content},
            ]
            msg = client.messages.create(
                model=CONFIG["model"],
                max_tokens=16000,
                system=SYSTEM,
                tools=tools,
                messages=messages,
            )
        text = "".join(b.text for b in msg.content if b.type == "text")
        try:
            data = _extract_json(text)
            for key in ("topic", "title", "description", "tags", "script"):
                if key not in data:
                    raise ValueError(f"필수 키 누락: {key}")
            return data
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    raise RuntimeError(f"대본 생성 3회 실패: {last_err}")
