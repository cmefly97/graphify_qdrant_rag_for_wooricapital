# CLAUDE.md — 프로젝트 헌법 (우리캐피탈 오토운영팀 상담챗봇)

> 이 파일은 **최상위 규칙**이다. 어떤 작업이든 시작 전 이 문서를 읽고, 충돌 시 이 문서가 우선한다.
> 세부 사항은 `docs/`를 참조한다. (PRD=뭘 / ARCHITECTURE=어떻게 / ADR=왜 / UI_GUIDE=어떻게 보여줄지)

---

## 0. 프로젝트 한 줄 정의
우리캐피탈 오토운영팀 상담사가 심사·운영 기준을 질문하면, 사내 규정·FAQ·월별 운영기준을 근거로 **정확하고 출처가 명확한 답변**을 주는 **그래프RAG + 벡터 임베딩 하이브리드** 챗봇.

---

## 1. 불변 규칙 (NEVER / ALWAYS) — 위반 금지
1. **수치 환각 금지**: 금리·등급·개월수·금액·한도·판정값 등 정밀 수치는 **반드시 구조화 테이블(tables.db) 조회 결과**에서만 생성한다. LLM 자유생성으로 수치를 만들지 않는다.
2. **출처 의무**: 모든 답변은 근거(문서명·조항/행·유효일자)를 함께 반환한다. 근거 없는 주장 금지.
3. **모르면 모른다**: 근거가 없으면 "규정에 명시되어 있지 않습니다"로 답한다. 추측 금지.
4. **유효일자 우선**: 운영기준이 충돌하면 최신 유효일자 본을 우선하고, 과거본 존재를 알린다.
5. **LLM/임베딩은 사내 게이트웨이만**: HCX-30B(`223.130.140.68:8000`) / Qwen 폴백(`223.130.140.218:8000`) / Octen-Embedding(`223.130.140.218:8002`)만 사용. 외부 모델 호출 금지.
6. **비밀정보**: API 키 등은 `.env`로만 관리. 코드/문서/로그/커밋에 키를 하드코딩하거나 노출하지 않는다. `.env`는 `.gitignore`.
7. **스코프 고정**: MVP 범위(아래 4장)를 벗어나는 기능을 임의 추가하지 않는다. 필요 시 ADR에 기록 후 진행.

---

## 2. 기술 스택 (고정)
- Backend: Python 3.11 + FastAPI
- 벡터DB: Qdrant · 그래프: NetworkX(`graphify-out/graph.json` 로드) · 구조화: SQLite/parquet(`tables.db`)
- LLM(답변): HCX-30B-Text (`hcx-agent-06`, OpenAI 호환·thinking) / 폴백 Qwen3.6-35B
- 임베딩: Octen-Embedding-8B · 이미지: VLM 비전(OCR, 후속)
- Frontend: Next.js + React · 그래프 시각화: Cytoscape.js
- 배포: Docker Compose (API + Qdrant)
- 설정: `.env` (키·엔드포인트·모델명)

자세한 근거는 `docs/ADR.md`.

---

## 3. 하네스 사용법 (작업 절차)
이 프로젝트는 **하네스 기반 단계 실행**으로 진행한다.
1. 작업 시작 전: `CLAUDE.md` + `docs/` + 해당 `phases/phase_N.md` 를 읽는다.
2. 단계 실행: `python scripts/execute.py status` 로 현재 단계 확인 → `python scripts/execute.py start <id>` / `complete <id>`.
3. 코드 변경 시 hook이 자동 검증(문법·비밀정보·테스트). hook 실패 시 **반드시 고치고 진행**.
4. 단계 완료 기준(phase 파일의 Exit Criteria)을 충족해야 다음 단계로 넘어간다.
5. 구현 리뷰는 `/review` (규칙 기반), 단계 묶음 실행은 `/harness`.
6. **반복 개선 루프**: `/loop` (또는 `scripts/orchestrate.py`)로 Phase 0→4 실행+검증→플랜 보완을 **3회 반복**한다. 검증은 `scripts/verify.py`(Outputs·pytest·커스텀 체크), 보완 이력은 `docs/PLAN_CHANGELOG.md` 에 누적된다. 검증 실패 시 반드시 보완(improve) 후 재검증한다.

### 핸드오프 컨벤션 (단계 간 인수인계)
- **산출물 위치**: 각 단계의 실제 결과물은 레포의 코드/데이터 파일로 누적된다. 각 `phases/phase_<N>.md` 의 `## Outputs` 에 그 경로를 못 박는다.
- **요약 문서**: 완료 시 `phases/RESULTS/phase_<N>.md` 에 "무엇을·어디에·다음 단계 사용법·주의·검증근거"를 남긴다(`execute.py handoff <id>` 로 템플릿 생성).
- **상태/추적**: `phases/state.json` 이 단계 상태 + 산출물 목록(`artifacts`) + RESULTS 경로를 기록한다.
- **완료 게이트**: `execute.py complete <id>` 는 (1) Outputs 경로 존재, (2) RESULTS 요약 존재를 모두 통과해야 성공한다(미충족 시 차단, `--force` 로만 우회).
- **다음 단계 참조 대상**: 정본 문서(`CLAUDE.md`+`docs/`) + 직전까지의 RESULTS 요약 + 실제 Outputs. 직전 단계만이 아니라 누적 산출물을 본다.

상태는 `phases/state.json`에 저장된다. 절대 임의로 단계를 건너뛰지 않는다.

---

## 4. MVP 범위 (확정)
- 포함: 인덱싱 파이프라인(doc/pdf/md/xlsx/이미지), 하이브리드 검색(라우팅→쿼리확장→벡터→그래프→재랭킹→답변), 수치 테이블 조회, 채팅 UI + 근거/출처 + 근거 그래프 패널, 평가 골든셋.
- 제외(후속): 사내 SSO/접근제어, 질의로그 대시보드, 월별 자동 재인덱싱 스케줄러. (코드는 인터페이스만 비워둠 = "운영확장 구조")

---

## 5. 코딩 규칙
- 함수·모듈은 단일 책임. 검색 경로(라우터/확장/벡터/그래프/조회/생성)는 각각 독립 모듈 + 단위테스트.
- 모든 외부 호출(게이트웨이)은 재시도·타임아웃·캐시를 둔다.
- 타입힌트 필수, `ruff`/`black` 통과. 테스트 없는 핵심 로직 머지 금지.
- 한국어 도메인 용어(금리등급, nego, R판정 등)는 코드 주석/문서에 정의를 남긴다.

---

## 6. 디렉터리 맵
```
CLAUDE.md            ← 본 문서(헌법)
docs/                ← PRD / ARCHITECTURE / ADR / UI_GUIDE
.claude/             ← commands(harness, review) + settings.json(hooks)
scripts/             ← execute.py(단계 실행+상태) + hooks/(자동 검증)
phases/              ← phase_0~4 정의 + state.json(실행상태)
souce/               ← 원천 데이터(FAQ/규정/운영기준)  [읽기 전용 취급]
graphify-out/        ← graphify 그래프 산출물(graph.json 등)
PROJECT_PLAN.md      ← 최초 계획 원본(참고). 정본은 docs/.
```
