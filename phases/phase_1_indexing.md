# Phase 1 — 인덱싱 파이프라인 (Indexing)

## 목표
souce/ 문서를 검색 가능한 인덱스(벡터·그래프·테이블)로 변환한다.

## Tasks
- [ ] 파서: docx(python-docx/mammoth), pdf(pymupdf + pdfplumber 표), md, xlsx(openpyxl), 이미지(HCX Vision OCR)
- [ ] FAQ xlsx 정규화: `<br>`/"(이미지 참조)" 처리, Q-A 1쌍=1청크
- [ ] 청킹: 규정/운영기준=조항·표 단위(헤더 반복 부착)
- [ ] 메타 부착: source_file, doc_type, 상품, 유효일자, 조항/행위치
- [ ] 임베딩(Octen) → Qdrant 적재(payload 포함)
- [ ] graph.json 로드 + 노드 id ↔ 청크 매핑 테이블
- [ ] 고립/약연결 노드 점검·보강(리포트 기준)
- [ ] **운영기준 금리/등급/조건표 구조화 추출 → tables.db** (스키마는 docs/TABLE_SCHEMA 참조)

## Outputs (산출물 — complete 시 존재 검증)
- `pipeline/parse.py`
- `pipeline/chunk.py`
- `pipeline/embed_index.py`
- `pipeline/extract_tables.py`
- `data/tables.db`
- `data/node_chunk_map.json`
- `tests/test_indexing.py`

## Exit Criteria
- souce/ 전 문서가 청크+메타로 인덱싱되어 Qdrant 검색됨.
- graph.json 노드가 원문 청크로 환원 가능.
- 금리표가 tables.db 에서 (상품·금리등급→GL금리·nego) 정확 조회됨.
- 인덱싱 재현 스크립트 + 검증 테스트 통과.
