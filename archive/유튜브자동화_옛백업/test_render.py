"""API 키 없이 TTS + 렌더링 경로만 검증하는 테스트 스크립트."""
from pathlib import Path

from src import config
from src.tts import make_narration
from src.video import make_background, render_video

config.ensure_dirs()
workdir = config.OUTPUT_DIR / "_test" / "shorts"
workdir.mkdir(parents=True, exist_ok=True)

script = (
    "여러분은 하루에 몇 번이나 스마트폰을 확인하시나요? "
    "연구에 따르면 사람들은 평균적으로 하루 96번, 약 10분에 한 번꼴로 화면을 켠다고 합니다. "
    "그런데 놀라운 사실은, 대부분의 확인이 알림 때문이 아니라 습관 때문이라는 거예요. "
    "우리 뇌는 새로운 정보를 확인할 때마다 도파민이라는 보상 물질을 분비하는데, "
    "이 작은 보상이 반복되면서 무의식적인 습관 회로가 만들어집니다. "
    "오늘 하루, 화면을 켜기 전에 딱 삼 초만 멈춰보세요. 뇌의 자동 회로가 조금씩 풀리기 시작합니다."
)

mp3, srt = make_narration(script, "shorts", workdir)
print("TTS OK:", mp3, srt)

bg = make_background("하루 96번, 당신이 폰을 집어드는 진짜 이유 #Shorts", "shorts", workdir)
video = render_video(bg, mp3, srt, "shorts", workdir)
print("RENDER OK:", video)
