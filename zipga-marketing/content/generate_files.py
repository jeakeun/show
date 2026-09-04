# 기획.json 을 읽어 영상별 파일 세트를 만듭니다.
#   comfyui프롬프트/{슬러그}.txt  — ComfyUI 에 복붙할 생성 프롬프트
#   문구/{슬러그}.txt             — 업로드 캡션 (영상과 같은 이름으로 watch/ 에 넣는 용)
#   영상기획.md                   — 전체 기획표 (사람이 보는 용)
# 기획을 바꾸려면 기획.json 만 고치고 이 스크립트를 다시 실행하세요.
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    items = json.loads((HERE / "기획.json").read_text(encoding="utf-8"))

    prompt_dir = HERE / "comfyui프롬프트"
    caption_dir = HERE / "문구"
    prompt_dir.mkdir(exist_ok=True)
    caption_dir.mkdir(exist_ok=True)
    # 기획이 바뀌면 옛 파일이 남지 않도록 싹 지우고 다시 만듦
    for d in (prompt_dir, caption_dir):
        for f in d.glob("*.txt"):
            f.unlink()

    rows = []
    for it in items:
        (prompt_dir / f"{it['slug']}.txt").write_text(it["comfy_prompt"] + "\n", encoding="utf-8")
        (caption_dir / f"{it['slug']}.txt").write_text(it["caption"] + "\n", encoding="utf-8")
        rows.append(
            f"| {it['slug']} | {it['title']} | {it['purpose']} | {it['account']} | {it['narration']} |")

    md = [
        "# 집가 영상 콘텐츠 기획 — 출시 전 대기 기간용",
        "",
        "총 " + str(len(items)) + "개 · 훅 실험 6종(계정 a~f 배정) + 씬 소재 6종 + 테스터 모집 3종",
        "",
        "## 만드는 순서 (영상 1개당)",
        "",
        "1. `comfyui프롬프트\\{슬러그}.txt` 를 열어 내용 복사",
        "2. ComfyUI 의 프롬프트 칸에 붙여넣고 생성",
        "3. `가져오기.bat` 더블클릭 → watch 폴더로 들어옴",
        "4. 들어온 영상 파일 이름을 **슬러그와 똑같이** 바꾸기 (예: `01_훅A_연락두절.mp4`)",
        "5. `문구\\{슬러그}.txt` 를 watch 폴더로 복사",
        "6. `업로드.bat` 더블클릭",
        "",
        "> 나레이션은 편집 프로그램에서 자막이나 목소리로 얹으세요.",
        "> 훅 실험은 **계정별로 다른 훅**을 올려서 어떤 문구가 먹히는지 비교하는 용도입니다 (플랜 W3).",
        "> 앱 출시 전이므로 문구에 링크가 없습니다 — CTA 는 댓글 \"점수\"/\"테스터\" 입니다.",
        "",
        "## 기획표",
        "",
        "| 슬러그(파일명) | 제목 | 용도 | 계정 | 나레이션/자막 |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "## 지켜야 할 것 — 플랫폼 제재 예방 원칙",
        "",
        "- **술·음주 단어 금지**: 술자리·취함·음주 등은 문구와 영상 어디에도 안 씀 → \"모임\", \"늦은 밤\"으로 표현",
        "- **음주 장면 금지**: 술집·잔·병·비틀거림이 영상에 나오지 않게 (프롬프트에 no alcohol 명시)",
        "- \"안전 보장·사고 예방·혈중알코올\" 표현 금지 — \"무사히\", \"집에 가는\" 정도까지만",
        "- 게임의 재미를 전면에 내세우지 않기 (술게임 서비스로 오인 방지)",
        "- 같은 영상 파일을 여러 계정에 올리지 않기 · 미성년 연상 인물 금지",
        "- 출시 날짜를 못 박지 않기 — \"곧 열립니다\" 까지만 · 포지셔닝은 \"설치 없이 쓰는 사이트\"",
    ]
    (HERE / "영상기획.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"완료 — 프롬프트 {len(items)}개, 문구 {len(items)}개, 영상기획.md 생성")


if __name__ == "__main__":
    main()
