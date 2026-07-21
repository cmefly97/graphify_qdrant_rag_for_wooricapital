# graphify_qdrant_rag_for_wooricapital

우리캐피탈 오토운영팀 상담사가 심사·운영 기준을 질문하면, 사내 규정·FAQ·월별 운영기준을 근거로
**정확하고 출처가 명확한 답변**을 주는 **그래프RAG + 벡터 임베딩 하이브리드** 상담챗봇.

> 최상위 규칙은 [`CLAUDE.md`](CLAUDE.md), 상세 설계는 [`docs/`](docs/) 참조.
> (PRD=뭘 / ARCHITECTURE=어떻게 / ADR=왜 / UI_GUIDE=어떻게 보여줄지)

---

## 핵심 원칙 (불변 규칙)

1. **수치 환각 금지** — 금리·등급·개월수·금액·한도 등 정밀 수치는 구조화 테이블(`tables.db`) 조회 결과에서만 생성. LLM 자유생성 금지.
2. **출처 의무** — 모든 답변은 근거(문서명·조항/행·유효일자)를 함께 반환.
3. **모르면 모른다** — 근거가 없으면 "규정에 명시되어 있지 않습니다"로 답한다.
4. **유효일자 우선** — 운영기준 충돌 시 최신 유효일자 본 우선.
5. **사내 게이트웨이만 사용** — HCX-30B / Qwen 폴백 / Octen-Embedding. 외부 모델 호출 금지.
6. **비밀정보는 `.env`로만** — 키를 코드/문서/로그/커밋에 노출 금지.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.11 + FastAPI |
| 벡터DB | Qdrant (리모트, 컬렉션 `woori_auto`, 4096d/Cosine) |
| 그래프 | NetworkX (`graphify-out/graph.json` 로드) |
| 구조화 | SQLite/parquet (`tables.db`) |
| LLM(답변) | HCX-30B-Text (`hcx-agent-06`) · 폴백 Qwen3.6-35B-A3B |
| 임베딩 | Octen-Embedding-8B |
| Frontend | Next.js + React · 그래프 시각화 Cytoscape.js |
| 배포 | Docker Compose (API + Qdrant) |

검색 파이프라인: **라우팅 → 쿼리확장 → 벡터 → 그래프 → 재랭킹 → 답변** (+ 수치 테이블 조회).

---

## 빠른 시작

### 1. 사전 조건
- Python 3.11+
- 프로젝트 루트에 `.env` (아래 참조). Qdrant는 리모트 사용 — 로컬 컨테이너 불필요.

```bash
cp .env.example .env   # 이후 HCX30_API_KEY 등 실제 값 입력
```

### 2. 의존성 설치 (최초 1회)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 서버 실행 (포트 8010)
```bash
bash scripts/serve.sh          # 또는 PORT=9000 bash scripts/serve.sh
```
- 채팅 UI: <http://localhost:8010/>
- 대시보드: <http://localhost:8010/dashboard>

> `.venv` 콘솔 스크립트 셔뱅이 깨질 수 있어, 항상 `python -m uvicorn` 형태(=`serve.sh`)로 실행한다.
> 자세한 내용은 [`Start.md`](Start.md).

### 4. 재인덱싱 (데이터 갱신 시, 사내망 필요)
```bash
.venv/bin/python scripts/reindex.py
```
`tables.db` 추출 → Octen 실제 임베딩 생성 → 리모트 Qdrant 적재 → 평가 회귀.

---

## 환경 변수 (`.env`)

| 변수 | 설명 |
|------|------|
| `HCX30_BASE_URL` / `HCX30_API_KEY` / `HCX30_MODEL` | 답변 LLM (HCX-30B) |
| `QWEN_BASE_URL` / `QWEN_MODEL` | 폴백 LLM (Qwen3.6) |
| `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` / `EMBEDDING_MODEL` | 임베딩 (Octen) |
| `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_COLLECTION` | 벡터DB |
| `ALLOW_OFFLINE_FALLBACK` / `GATEWAY_TIMEOUT` / `GATEWAY_MAX_RETRIES` / `ANSWER_MAX_TOKENS` | 동작 옵션 |

전체 예시는 [`.env.example`](.env.example) 참조.

---

## 디렉터리 맵

```
CLAUDE.md            ← 프로젝트 헌법(최상위 규칙)
docs/                ← PRD / ARCHITECTURE / ADR / UI_GUIDE 등
app/                 ← FastAPI 앱 (검색 파이프라인·게이트웨이·API)
scripts/             ← execute.py(단계 실행) + serve.sh + reindex.py + hooks/
phases/              ← phase_0~4 정의 + state.json(실행상태)
eval/                ← 평가 하네스 (골든셋 수치 데이터는 미포함)
pipeline/            ← 인덱싱 파이프라인
web/                 ← 프론트엔드
```

---

## 저장소에서 제외된 데이터 (기밀)

사내 규정·기밀 보호를 위해 다음은 커밋되지 않는다 ([`.gitignore`](.gitignore)):

- `.env` — 실제 API 키
- `souce/` — 사내 심사·운영 기준 원천 문서
- `graphify-out/` — 위 문서 파생 지식그래프
- `eval/goldenset.jsonl`, `eval/baseline.json`, `eval/report.md` — 규정 파생 실제 수치
- `data/*.db|json|jsonl` — 인덱스 산출물

이 저장소는 **코드·설정·문서만** 공개한다.
