---
name: yummy-planet
description: "냠냠플래닛(팀프로젝트) 내 계정 독립 복사본 — D:\\YummyPlanet, jeakeun/YummyPlanet 비공개, 내 PC에서만 실행(run-all.bat), 원본 저장소는 건드리지 않음, 남은 일은 docs/REMAINING_ISSUES.md"
metadata:
  node_type: memory
  type: project
  originSessionId: d3737be7-c13b-4229-8e7d-510ba0ca56ab
  modified: 2026-10-07T06:15:49.066Z
---

냠냠플래닛(YummyPlanet) = AI 식단 관리 웹 서비스 팀프로젝트. React(project_react, 3000) + Spring Boot/MyBatis(project_java, 8080) + FastAPI(project_python, 8000) + MySQL `yummy` DB.

- 원본 `YH-KIKI/YummyPlanet`(전팀장 소유)과 기존 포크 `jeakeun/project`는 **건드리지 말 것** (2026-10-05 사용자 지시: "거기 레포는 건들지 말고").
- 작업 저장소: `jeakeun/YummyPlanet`(비공개), 로컬 `D:\YummyPlanet`. main이 최신 기준(daejangnim+sjk_test 병합).
- 운영 방침(2026-10-05 사용자 결정): AWS 서버는 안 쓰고 **내 PC에서만** 실행. GitHub Actions(배포)는 꺼둠.
- 실행: `run-all.bat`(창 3개). 순서·준비물·로컬 테스트 계정은 저장소의 `LOCAL_RUN.md`. DB 스키마는 `db/schema.sql`.
- **남은 손볼 부분은 저장소의 `docs/REMAINING_ISSUES.md`**(2026-10-05 전체 점검). 이어서 작업할 때 먼저 읽을 것. 사용자 지시(2026-10-05): "순서대로 진행". 끝낸 것: 섭취량 단위 g 통일(규칙은 `db/README.md`), 경험치 날짜별 1회 지급, 식단 수정 시 사진 유지, 식단 날짜 기준 통일, 하루 목표를 목표 화면 저장값으로 통일(2026-10-06 사용자 결정). 다음 차례: 5번 AI 추천 로직, 8번 JWT 필터. 사진 인식 한계 개선은 2026-10-06에 4단계를 추천했고 ①②는 사용자 승인으로 완료(영양 DB 보완 `db/extra_foods.sql`, "음식아님" 포함 151종 재학습). ③ 음식 부분 잘라서 인식 ④ 후보(2~3순위) 보여 주고 고르기도 2026-10-07 완료(`ImageAnalyze/Analyze.jsx`, 서버는 결과에 kind=best/alt/region). 고해상도(288px) 추가 학습도 2026-10-07 완료·main 병합(2babdea) — 사진 인식 쪽에서 사용자가 시킨 일은 모두 끝.
- 이 PC 환경: JDK 21(Temurin), Python 3.12 venv(`project_python\.venv`, torch 2.14.1+cu126 GPU용 설치·RTX 4080 인식 확인), MySQL 8.0(root 기본 비번), 음식 데이터 19,495건·레시피 샘플 5건 적재.
- 깃 기록의 Gemini 키 3개는 2026-10-05에 API로 확인하니 이미 전부 무효(삭제할 것 없음).
- 사용자가 직접 해야 하는 것(2026-10-05 안내함, 완료 여부 미확인): ① 식품안전나라 인증키 → `project_python\.env` FOODSAFETY_API_KEY → `import-recipes.bat` ② Gemini 키는 같은 `.env`의 GOOGLE_AI_API_KEY.
- 음식 사진 인식 재학습 완료: 2026-10-05 150종(검증 top1 90.3%), 2026-10-06 "음식아님" 추가한 151종으로 교체(음식 사진 top1 90.8%, 예전 대비 35%→91%, 음식아님 99.6%). 2026-10-07 그 모델에서 이어서 288px로 4 epoch 추가 학습(`--init`)해 교체: 같은 검증 사진 15,016장에서 1순위 90.8%→91.6%, 후보 포함 정답 노출은 96.5%→96.6%로 거의 그대로(해상도만 더 올려서는 얻을 게 적음), 요청 1건 약 97→127ms. ConvNeXt-Tiny, `project_python/train_food_classifier.py` + `prepare_nonfood.py`, 모델 `model/kfood_classifier.pth`(56MB, 깃 포함). 남은 한계(여러 음식, 비슷한 음식)는 REMAINING_ISSUES에 있음.
- "음식아님" 원본: `D:\datasets\nonfood\`(COCO val2017.zip + annotations, 약 1GB). 만든 사진은 `D:\datasets\kfood\images\_음식아님\음식아님`(4,515장)에 있어 D:의 데이터셋만으로 151종 재학습 가능.
- 추가한 음식 3종(과메기·편육·떡꼬치)의 수치는 fatsecret 값이고 과메기·편육 나트륨은 추정치 — 식품안전나라 키가 생기면 공식 수치로 교체할 것.
- 학습 데이터 위치: 원본 `D:\datasets\kfood\한국 음식 이미지\kfood.zip`(16.9GB), 푼 것 `D:\datasets\kfood\images`(HDD). 학습 때 쓴 SSD 사본(`C:\datasets\kfood`)은 학습이 끝날 때마다 삭제함(2026-10-06 사용자 요청, 2026-10-07에도 삭제) — 다시 학습하려면 D:에서 SSD로 복사(robocopy 약 8분)부터.
- 테스트할 때: 사용자가 `run-all.bat`으로 앱을 켜 둔 상태일 수 있으니(8080 사용 중) 내 빌드는 `SERVER_PORT=8081`로 따로 띄워 확인하고 사용자의 창은 끄지 말 것.
- 학습 때 주의: 이 PC의 GPU는 yt-auto의 ComfyUI(16:40 YouTubePrepareEvening 작업이 띄움, 약 10GB 점유)와 같이 쓴다. ComfyUI는 건드리지 말고 `--mem-fraction 0.27 --batch 48`로 학습. D:는 HDD라 데이터는 SSD(C:)에 둬야 빠름. BatchNorm 계열(EfficientNet·ResNet)은 이 환경에서 4배 느렸고 ConvNeXt가 빨랐음. GPU를 쓰는 또 하나: `D:\look-transfer-gen` 생성 서버(포트 8189, 약 14GB 점유) — 다른 클로드 대화(`show\support-yr-makeup`, 당화응 작업)가 백그라운드로 띄운 것이라 닫을 창이 없고, 꺼도 그 대화가 1분 안에 다시 켠다(2026-10-07 확인). 끄지 말고 그 작업이 끝나길 기다리거나 사용자가 그 대화에서 멈추게 할 것.
- 학습을 GPU가 빌 때까지 기다렸다 돌릴 때: 서버를 끄지 말고 GPU 여유 5.5GB 이상을 1분 간격으로 확인하다 시작(2026-10-07 사용자 결정 "1진행" = 다른 작업이 끝날 때까지 기다림). 288px는 `--batch 28 --mem-fraction 0.27`이면 ComfyUI와 같이 돌아도 됨(4 epoch 약 23분). 백그라운드 대기는 2시간 제한이 있어 70분 단위로 끊어 다시 건다. 이 PC에서 `CUDA_VISIBLE_DEVICES=""`는 GPU를 못 숨김(-1을 써야 함). 새 모델은 같은 검증 사진으로 기존 모델과 비교해 더 좋을 때만 채택.
- 함정: cmd에서 `call gradlew.bat`이 안 먹어 전체 경로로 호출. React dev 서버는 `DANGEROUSLY_DISABLE_HOST_CHECK=true` 필요. 파이썬은 `PYTHONUTF8=1` 없으면 이모지 print에서 죽음. Git Bash에서 curl로 한글 JSON을 보내면 cp949로 깨지므로 파이썬으로 테스트. 백엔드 재시작하면 JWT 서명 키가 바뀌어 브라우저에서 다시 로그인해야 함.

**Why:** 사용자가 서버 에러와 전체 코드를 직접 손보고 싶어 함(포트폴리오용으로 추정 — 내 해석).
**How to apply:** 작업은 `D:\YummyPlanet`에서 work/ 브랜치 → 실행 확인 → main 병합([[branch-workflow]]의 취지, gitwork.sh 대신 저장소 안 브랜치 사용). 관련: [[git-repos]].
