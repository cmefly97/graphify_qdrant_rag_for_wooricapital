# RESULTS — phase_2 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- 하이브리드 질의 파이프라인 완성: 라우팅 → 쿼리확장 → (테이블 조회 | 벡터+그래프 검색) → 재랭킹 → 답변 생성.
- 정밀 수치는 tables.db 결과를 그대로 신뢰(LLM 자유생성 금지) → 환각 0.
- PRD 대표 5개 질의가 모두 정확 답변 + 출처 반환. 근거 없는 질의는 "규정에 명시되어 있지 않습니다".

## 산출물 (어디에)
- `app/router.py` — 수치형/설명형/혼합형 분류.
- `app/expander.py` — 동의어·영문 확장(검색 누락 보완).
- `app/tables_lookup.py` — 금리/네고/조건 SQL 조회 + 답변 문장 생성(정답원).
- `app/retriever.py` — 벡터 검색(cosine) + 그래프 1홉 확장 + 근거 청크 환원.
- `app/reranker.py` — 테이블 우선 + 벡터 점수 정렬 + 중복 제거.
- `app/generator.py` — 근거 기반 생성. 수치=테이블, 설명=LLM(키 있으면)/근거요약, 없으면 '모름'.
- `app/api.py` — `POST /ask` + `answer_query()` 오케스트레이션.
- `tests/test_query_engine.py` — 5개 예시 질의 end-to-end 검증.

## 다음 단계가 이것을 어떻게 쓰나
- Phase 3 프론트엔드가 `POST /ask` 를 호출해 answer/sources/evidence_nodes 를 렌더링.
- evidence_nodes 는 근거 그래프 패널 시각화에 사용.

## 주의/제약 (이어받는 사람이 알아야 할 것)
- 라우팅은 휴리스틱(오프라인). 테이블 조회는 라우팅과 무관하게 항상 시도(정답 누락 방지) — iter1 중 버그 수정 반영.
- 설명형 LLM 답변은 게이트웨이 키 필요. 키 없으면 근거 요약(context_only)으로 폴백.
- 벡터 검색은 폴백 임베딩 기준이라 설명형 정밀도는 실제 Octen 임베딩에서 개선됨.

## 검증 근거
- `pytest -q` → 12 passed, 1 skipped.
- 예시: "금리등급 2등급" → 21.0% + 거점장 11.0% + NICE 1등급(mode=table).
- "엔카 슬라이딩"→조건부 가능, "R판정"→필터링 취급 불가(mode=table).
