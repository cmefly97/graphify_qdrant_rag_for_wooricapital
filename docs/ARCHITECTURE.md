# ARCHITECTURE — 어떻게 만드는가

## 1. 전체 구성도
```
Frontend (Next.js)
  예시질문칩 · 채팅 · 답변+출처 · 근거그래프패널
        │ REST / SSE
Backend (FastAPI)
  [0] 질의 라우터  → LLM 분류: 수치형 / 설명형 / 혼합형
  [1] 쿼리 확장    → 동의어·영문·유사표현
  [2] 벡터검색(Qdrant)  → 의미 유사 시작노드
  [3] 그래프탐색(NetworkX) → 인접·커뮤니티 1~2홉 확장
  [3'] 구조화 조회(tables.db) → 정밀 수치
  [4] 컨텍스트 조립 + 재랭킹 + 출처부착
  [5] 답변 생성(HCX-30B / hcx-agent-05) → 근거 인용 / 모르면 모른다
        │
  사내 게이트웨이(namc-aigw): HCX · Qwen · Octen-Embedding
  인덱스: Qdrant(벡터) · graph.json(NX) · tables.db(수치) · docstore(원문)
```

## 2. 온라인 질의 흐름 (하이브리드 라우팅)
1. **라우팅**: LLM이 질의를 수치형/설명형/혼합형으로 분류.
2. **쿼리 확장**: "로그인 튕김"→"인증 실패/세션 만료/Auth fail" 식 유사표현 생성.
3. **수치형**: 자연어→파라미터 변환 → `tables.db` 정확 조회(예: 금리등급2→GL 21.0%+nego). 그래프RAG로 설명 보강.
4. **설명형**: 벡터검색으로 시작노드 → 그래프 인접/커뮤니티 확장 → 근거 청크 수집.
5. **재랭킹**: 벡터점수 + 그래프거리 + 메타필터(최신 유효일자)로 정렬.
6. **생성**: 근거+출처로 답변. 임계값 미만이면 불확실 표기.

## 3. 오프라인 인덱싱 파이프라인
1. **파싱**: docx(python-docx/mammoth), pdf(pymupdf+pdfplumber 표), md(직접), xlsx(openpyxl), 이미지(HCX Vision OCR).
2. **청킹**: 규정/운영기준=조항·표 단위(헤더 반복 부착), FAQ=Q-A 1쌍=1청크.
3. **메타 부착**: source_file, doc_type, 상품, 유효일자, 조항/행위치.
4. **임베딩**: Octen-Embedding-8B → Qdrant(vector+payload). payload 필터(상품·유효일자) 선적용.
5. **그래프**: `graphify-out/graph.json` 로드. 노드 id ↔ 원문청크 매핑. 고립/약연결 노드 보강.
6. **테이블 추출**: 운영기준 금리/등급/조건표 → 구조화 → `tables.db`.

## 4. 저장소
- **Qdrant**: 컬렉션 1개, payload=메타. 도커 컨테이너.
- **NetworkX**: graph.json 메모리 로드(데이터 규모상 충분).
- **tables.db(SQLite)**: 금리표/등급표/조건표 스키마.
- **docstore**: 원문 청크(SQLite/파일).

## 5. 외부 연동(게이트웨이)
- 모든 호출에 타임아웃·재시도·백오프. 임베딩 결과 캐시.
- HCX 장애 시 Qwen 폴백. 호출 파라미터/모델명은 `.env`.

## 6. 모듈 경계 (독립 + 테스트)
`parsers/`, `chunker/`, `embedder/`, `graph/`, `tables/`, `router/`, `expander/`, `retriever/`(vector+graph), `reranker/`, `generator/`, `api/`, `web/`.
각 모듈 입출력 계약을 명시하고 단위테스트 보유.

## 7. 운영확장 훅 (지금은 빈 인터페이스)
- `auth/`(SSO 자리), `logging/`(질의로그 자리), `scheduler/`(재인덱싱 자리). MVP에선 no-op 구현.

## 8. 디렉터리(코드, 예정)
```
app/ (FastAPI)  ·  pipeline/ (인덱싱)  ·  web/ (Next.js)  ·  tests/  ·  data/(인덱스 산출)
```

---

## 9. 현행화 (2026-06-29 최신 상태)

### 질의 조회 핸들러 (app/tables_lookup.py, 순서대로)
`lookup()` = 잔가군 → 프로모션(+판정) → 조건(개월/듀얼/엔카/R판정) → 금리(rate) → 네고개요 → 법인 → 범용조건(상품 스코프) → 팩트(키워드).
- **판정형**: 프로모션 등은 질의의 NICE·KCB 점수를 파싱해 기준(tables.db 자동추출)과 대조 → 가능/불가 + 근거.
- **오매칭 방지**: 비범위 질의는 상품명 일치 필수, 흔한 단어 1개 매칭 차단, 팩트 라우터는 속성 우선.

### LLM/임베딩 (게이트웨이)
- 답변: **HCX-30B-Text(`hcx-agent-05`)** `HCX30_*` — 223.130.140.68:11000. 폴백 Qwen3.6 `QWEN_*` — 223.130.140.218:8000.
- 임베딩: **Octen-8B(4096d)** — 사내 vLLM(223.130.140.218:8002), 키 불필요(`EMBEDDING_API_KEY` 빈 값). 배치 임베딩+개별 폴백.
- `chat`에 `max_tokens`(ANSWER_MAX_TOKENS, 기본 2048)로 답변 잘림 방지.

### 저장소
- Qdrant `woori_auto`(4096d, Cosine) 우선, 미연결 시 로컬 `vector_store.json` 폴백.
- SQLite `tables.db`: rate_grade 45 / nego_rule 36 / condition_rule 51 / lease_residual_group 70 / nice_band 9.

### 프론트엔드
- FastAPI 직접 서빙: `/`(채팅), `/dashboard`(통계). 3분할 — 채팅 / 처리과정 트레이스(단계·ms·검색결과) / 답변근거(청크·graphify 노드).

### 운영/품질
- 로깅(query_log.db)·/stats·/feedback, 자동 재인덱싱 스케줄러(회귀 게이트), CI 게이트(ci_gate.py)+A/B(ab_test.py). 골든셋 65문항.
