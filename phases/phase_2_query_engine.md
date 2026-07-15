# Phase 2 — 질의 엔진 (Query Engine)

## 목표
하이브리드 검색·답변 생성 백엔드를 완성한다.

## Tasks
- [ ] 질의 라우터(LLM 분류: 수치형/설명형/혼합형)
- [ ] 쿼리 확장(동의어·영문·유사표현)
- [ ] 벡터 검색(Qdrant, payload 필터) → 시작노드
- [ ] 그래프 탐색(NetworkX, 1~2홉 + 커뮤니티)
- [ ] 구조화 조회(tables.db): 자연어→파라미터 변환
- [ ] 재랭킹(벡터점수+그래프거리+최신 유효일자) + 출처 메타 부착
- [ ] 답변 생성(HCX): 근거 인용, 근거 없으면 "명시되어 있지 않음", 신뢰도 임계
- [ ] REST + SSE 스트리밍 API
- [ ] 운영확장 빈 인터페이스: auth/logging/scheduler no-op

## Outputs (산출물 — complete 시 존재 검증)
- `app/router.py`
- `app/expander.py`
- `app/retriever.py`
- `app/tables_lookup.py`
- `app/reranker.py`
- `app/generator.py`
- `app/api.py`
- `tests/test_query_engine.py`

## Exit Criteria
- PRD 대표 5개 질의가 정확 답변 + 출처 반환(수치 100% 일치).
- 근거 없는 질의에 "명시되어 있지 않음" 반환.
- 각 모듈 단위테스트 + 통합테스트 통과.
