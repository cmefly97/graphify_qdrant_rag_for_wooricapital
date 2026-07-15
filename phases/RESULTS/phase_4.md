# RESULTS — phase_4 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- 골든셋(10문항: 예시5 + 변형/오타/영문 + 무관질의1)과 평가 러너를 만들었다.
- 정확도·수치정확도·출처율·환각회피를 측정 → eval/report.md 생성.
- iter1 결과: 전체 100%, 수치 100%, 출처 100%.

## 산출물 (어디에)
- `eval/goldenset.jsonl` — 채점용 질의/기대값.
- `eval/run_eval.py` — `evaluate()` + report 생성.
- `eval/report.md` — 최신 평가 리포트.

## 다음 단계가 이것을 어떻게 쓴다
- 인덱스/프롬프트/추출 변경 시 회귀 테스트로 재실행(`python -m eval.run_eval`).
- 다음 회차 개선의 정량 기준선.

## 주의/제약
- 골든셋이 작다(10). 실제 상담 로그로 50~100문항 확장 필요.
- 설명형 LLM 답변 품질은 게이트웨이 연결 시 별도 평가 필요(현재 폴백).

## 검증 근거
- `python -m eval.run_eval` → accuracy=1.0, numeric=1.0, source_rate=1.0.
- `verify.py phase_4` → outputs_exist ✓, 전체 pytest ✓.
