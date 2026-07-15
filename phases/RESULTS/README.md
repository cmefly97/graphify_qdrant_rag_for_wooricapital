# phases/RESULTS — 단계 핸드오프 요약

각 단계 완료 시 `phase_<N>.md` 핸드오프 요약을 이 폴더에 남긴다.
이 요약 + 단계가 만든 실제 산출물(Outputs)만 보면 **다음 단계를 그대로 이어받을 수 있어야** 한다.

## 규칙
- 템플릿 생성: `python scripts/execute.py handoff phase_<N>`
- 단계 완료(`complete`)는 다음을 모두 통과해야 한다:
  1. `phase_<N>.md` 의 `## Outputs` 경로가 실제로 존재
  2. `phases/RESULTS/phase_<N>.md` 요약 작성 완료
- 산출물 기록은 `phases/state.json` 의 각 phase `artifacts` 에 자동 저장된다.

## 작성 항목
무엇을 만들었나 / 산출물 위치 / 다음 단계의 사용법 / 주의·제약 / 검증 근거.
