# Phase 0 — 셋업 (Setup)

## 목표
개발 토대를 만들고 사내 게이트웨이(LLM·임베딩) 연결을 검증한다.

## Tasks
- [ ] 레포 구조 생성: `app/`, `pipeline/`, `web/`, `tests/`, `data/`
- [ ] `.env.example` 작성(제공된 변수: HCX_*, QWEN_MODEL, EMBEDDING_*, QDRANT_URL). `.env`는 `.gitignore`
- [ ] `requirements.txt`/`pyproject.toml` + ruff/black 설정
- [ ] Docker Compose: FastAPI + Qdrant
- [ ] 게이트웨이 클라이언트(타임아웃·재시도·캐시) + 스모크 테스트:
  - [ ] HCX-30B(hcx-agent-06) chat 호출 1건 성공
  - [ ] Octen-Embedding-8B 임베딩 1건 성공(벡터 차원 확인)
- [ ] 헬스체크 엔드포인트 `/health`

## Outputs (산출물 — complete 시 존재 검증)
- `app/main.py`
- `app/gateway/client.py`
- `.env.example`
- `docker-compose.yml`
- `requirements.txt`
- `tests/test_gateway_smoke.py`

## Exit Criteria
- `docker compose up` 으로 API + Qdrant 기동.
- 게이트웨이 chat/embeddings 스모크 테스트 통과(테스트 코드 존재).
- 시크릿이 코드에 없고 .env 로만 관리됨.
