# RESULTS — phase_1 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- souce/ 8개 문서를 파싱→청킹(252 청크)하고, 폴백 임베딩으로 벡터 인덱스를 만들었다.
- graphify graph.json 의 57개 노드를 source_file 기준으로 청크와 매핑(그래프→근거 환원).
- 운영기준 PDF의 내국인 금리표를 구조화 추출해 `tables.db` 적재. 금리등급 2 → 21.0%, 거점장 11.0% 회귀 검증 통과.

## 산출물 (어디에)
- `pipeline/parse.py` — docx/pdf/md/xlsx/이미지 파서. `parse_all()`.
- `pipeline/chunk.py` — FAQ Q-A·규정 문단 청킹. `chunk_all()`.
- `pipeline/embed_index.py` — 임베딩+벡터스토어(`data/vector_store.json`)+`build_node_chunk_map()`.
- `pipeline/extract_tables.py` — 금리/네고/조건/NICE 테이블 → `data/tables.db`. `build()`.
- `data/tables.db` — rate_grade / nego_rule / condition_rule / nice_band.
- `data/node_chunk_map.json` — 그래프 노드 id → 청크 id 매핑(57노드).
- `tests/test_indexing.py` — 추출·청킹·매핑 + 21.0% 회귀 테스트.

## 다음 단계가 이것을 어떻게 쓰나
- Phase 2 수치 조회는 `data/tables.db`(rate_grade/nego_rule/condition_rule)를 SQL 조회.
- Phase 2 벡터 검색은 `data/vector_store.json`(운영 시 Qdrant), 그래프 탐색 후 `node_chunk_map.json` 으로 근거 청크 환원.

## 주의/제약 (이어받는 사람이 알아야 할 것)
- 임베딩은 게이트웨이 미연결로 폴백(해시 256d). 운영 정확도는 실제 Octen 임베딩 필요(재인덱싱).
- tables.db 는 현재 중고승용 내국인 표 + 조건 시드만. 외국인 구간표·타 상품 표는 후속 회차에서 확장(PLAN_CHANGELOG 참조).
- Qdrant 미기동 → 로컬 JSON 벡터스토어 사용 중.

## 검증 근거
- `python -m pipeline.extract_tables` → rate_grade_rows=9.
- `python -m pipeline.embed_index` → docs=8, chunks=252, nodes_mapped=57.
- `pytest -q tests/test_indexing.py` → 4 passed.
- `verify.py phase_1` → outputs_exist ✓, rate_grade_sample(21.0%) ✓, node_chunk_map ✓.
