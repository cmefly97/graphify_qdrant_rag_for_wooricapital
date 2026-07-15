# RESULTS — phase_5 핸드오프 요약 (운영 전환 2·3·5)

> 4(인프라)·1(SSO)·6(보안)은 docs/PRODUCTION_TRANSITION.md 에 문서화·보류.

## 무엇을 만들었나
- (2) 질의·답변 로깅(data/query_log.db) + 피드백(/feedback) + 통계(/stats) + 대시보드(/dashboard).
- (3) 자동 재인덱싱 스케줄러: 재추출→(재임베딩)→회귀게이트 통과 시만 PROMOTED, 이력 data/reindex_versions.jsonl.
- (5) CI 회귀 게이트(scripts/ci_gate.py) + A/B 하네스(eval/ab_test.py, baseline.json). 임계는 eval/gate.py 공용.

## 산출물 (어디에)
- `app/logging_store.py` — 로깅/피드백/통계. `app/api.py` 에 /ask 로깅·/feedback·/stats·/dashboard.
- `scripts/scheduled_reindex.py` — 버전 게이트 재인덱싱(cron 등록용).
- `scripts/ci_gate.py` — pytest+eval 임계 게이트(배포 전/CI).
- `eval/gate.py` — 회귀 임계 단일 출처(numeric 100%, accuracy≥95%, source 100%).
- `eval/ab_test.py` + `eval/baseline.json` — 업그레이드 A/B 비교.
- `tests/test_logging.py`, `tests/test_ci_ab.py` — 회귀 테스트(파일 보존).

## 다음 단계가 이것을 어떻게 쓰나
- 업그레이드 시: 코드 수정 → `python eval/ab_test.py`(회귀 확인) → `python scripts/ci_gate.py`(게이트) → 통과 시 반영.
- 월별: 사내 cron 에 `scheduled_reindex.py` 등록(게이트 통과해야 반영).
- SSO(1) 도입 시 logging_store.log_query 의 user_id 를 실제 신원으로 교체.

## 주의/제약
- 스케줄러의 실제 임베딩/적재는 게이트웨이·Qdrant 접근 가능한 사내망에서 실행.
- query_log/reindex_versions 는 런타임 데이터(gitignore). baseline.json 은 버전관리 대상.

## 검증 근거
- 전체 pytest 24 passed, 1 skipped. ci_gate PASS(accuracy=1.0/numeric=1.0/source=1.0).
- A/B: baseline 51문항 저장, 현재 vs baseline 회귀 0.
