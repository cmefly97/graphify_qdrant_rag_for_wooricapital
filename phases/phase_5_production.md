# Phase 5 — 운영 전환 (Production Transition, 부분)

## 목표
운영 전환 항목 중 2(로깅·대시보드)·3(자동 재인덱싱)·5(CI 게이트·A/B)를 구현한다.
4(인프라)·1(SSO)·6(보안)은 docs/PRODUCTION_TRANSITION.md 에 문서화하고 보류.

## Tasks
- [ ] 질의/답변 로깅 스토어 + 피드백 + 통계 API + 대시보드
- [ ] 자동 재인덱싱 스케줄러(회귀 게이트 통과 시만 반영) + 버전 이력
- [ ] CI 회귀 게이트(임계 검증) + A/B 테스트 하네스(베이스라인 비교)
- [ ] 테스트 코드 파일 보존(tests/, eval/)

## Outputs (산출물 — complete 시 존재 검증)
- `app/logging_store.py`
- `scripts/scheduled_reindex.py`
- `scripts/ci_gate.py`
- `eval/ab_test.py`
- `tests/test_logging.py`
- `tests/test_ci_ab.py`

## Exit Criteria
- 질의 로깅·통계 집계 동작, 회귀 테스트 통과.
- 스케줄러가 회귀 게이트 실패 시 반영을 막음(테스트로 검증).
- ci_gate 가 임계 미달 시 비정상 종료. A/B 가 베이스라인 대비 개선/회귀를 보고.
- 전체 pytest + eval(51/51) 통과.
