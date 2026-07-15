# Start.md — 서버 시작 가이드

> 우리캐피탈 오토운영팀 상담챗봇(그래프RAG + 벡터 하이브리드) 로컬/개발 실행 가이드.
> 정식 규칙은 `CLAUDE.md`, 상세 설계는 `docs/` 참조.

---

## 0. 사전 조건 (한 번만)

- **Python 3.11+** (현재 `.venv`는 3.14 기준으로 구성됨)
- **`.env` 파일**이 프로젝트 루트에 있어야 함 (게이트웨이 키·엔드포인트·Qdrant 주소).
  없으면 `.env.example`을 복사해서 채운다:
  ```bash
  cp .env.example .env   # 이후 HCX30_API_KEY / EMBEDDING_API_KEY / QDRANT_URL 입력
  ```
- **Qdrant는 리모트 서버에 이미 설치·운영 중**
  (`QDRANT_URL`, 기본값 `http://223.130.140.218:6333`, 컬렉션 `woori_auto`).
  → **로컬에서 Qdrant를 띄울 필요가 없다.** `docker compose`로 qdrant를 실행하지 않는다.

---

## 1. 빠른 시작 (권장)

```bash
# 1) 프로젝트 루트로 이동
cd /Users/mac_al03256431/Documents/DEV/2_JB_Wooricapital_Auto_Agent_Graphify

# 2) 웹 서버 실행 (포트 8010, --reload 포함)
bash scripts/serve.sh
```

접속:
- 채팅 UI: <http://localhost:8010/>
- 대시보드: <http://localhost:8010/dashboard>

포트 변경: `PORT=9000 bash scripts/serve.sh`

`serve.sh`는 `.venv/bin/python`을 우선 사용해
`python -m uvicorn app.main:app --reload --port 8010`을 실행한다.
(venv를 별도로 `activate`하지 않아도 된다.)

> **참고 — venv 셔뱅 주의**: 현재 `.venv`는 다른 경로에서 옮겨져 콘솔 스크립트
> (`.venv/bin/uvicorn` 등)의 셔뱅이 깨져 있다. 따라서 `uvicorn ...`을 직접 호출하면
> `bad interpreter` 오류가 난다. **항상 `python -m uvicorn` 형태**로 실행하거나
> `serve.sh`를 사용한다. 완전히 정리하려면 2장처럼 venv를 재생성한다.

---

## 2. 의존성 설치가 필요한 경우 (새 환경)

`.venv`가 없거나 모듈 오류(`ModuleNotFoundError`)가 나면:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

설치 확인:
```bash
.venv/bin/python -c "import fastapi, uvicorn, pydantic_settings, qdrant_client; print('deps OK')"
```

> 재생성한 venv는 셔뱅이 정상이라 `source .venv/bin/activate` 후 `uvicorn`을 직접 써도 된다.

---

## 3. 리모트 Qdrant 연결 확인

서버 시작 전, 리모트 Qdrant가 살아있고 컬렉션이 있는지 확인:

```bash
curl -s "$QDRANT_URL/collections" | python -m json.tool
# 기대 출력: collections 목록에 "woori_auto" 포함
```

- 연결되면 → 벡터 검색은 리모트 `woori_auto`(4096d, Cosine)를 사용.
- 연결 실패 시 → 로컬 `vector_store.json` 폴백으로 자동 전환(`ALLOW_OFFLINE_FALLBACK=true`).

---

## 4. (선택) Docker Compose 실행

전체 스택을 컨테이너로 띄우고 싶을 때만 사용.
**리모트 Qdrant를 쓰므로 로컬 qdrant 컨테이너는 띄우지 않는다** — `api`만 실행:

```bash
docker compose up -d --build api
```

> 참고: `docker-compose.yml`에는 로컬 개발 편의를 위한 `qdrant` 서비스가 정의되어 있으나,
> 운영은 리모트 Qdrant(`QDRANT_URL`)를 사용한다. 로컬 qdrant를 쓰려면
> `.env`의 `QDRANT_URL`을 로컬 주소로 바꿔야 한다.

---

## 5. 재인덱싱 (데이터 갱신 시)

원천 데이터(`souce/`)나 그래프 산출물이 바뀌면 사내망(게이트웨이 접근 가능)에서:

```bash
.venv/bin/python scripts/reindex.py
```

순서: `tables.db` 추출 → Octen 실제 임베딩 생성 → 리모트 Qdrant 적재 → 평가 회귀.
※ `EMBEDDING_API_KEY`가 유효해야 실제 4096d 임베딩이 생성된다(미설정/미연결 시 256d 폴백).

---

## 6. 문제 해결

| 증상 | 원인 / 조치 |
|------|-------------|
| `ModuleNotFoundError: pydantic_settings` | venv 미활성화 또는 의존성 미설치 → 2장 |
| Qdrant 연결 실패 로그 | `QDRANT_URL` 확인, 리모트 서버/방화벽 상태 확인. 폴백은 자동 |
| 답변에 수치가 비거나 이상 | `tables.db` 존재/재인덱싱 필요 → 5장 |
| 포트 충돌 | `PORT=9000 bash scripts/serve.sh` |

---

## 7. 개발/운영 하네스 명령어 (참고)

서버 실행과 별개로, 개발 단계 진행용:

```bash
.venv/bin/python scripts/execute.py status   # 단계 상태 확인 (현재 phase_0~5 모두 completed)
.venv/bin/python scripts/verify.py           # Outputs·pytest·커스텀 체크 검증
```

- `/harness` — 하네스 기반 작업 진행
- `/loop` — 실행·검증·보완 반복 루프
- `/review` — 규칙 기반 코드/구현 리뷰
