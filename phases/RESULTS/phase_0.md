# RESULTS — phase_0 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- FastAPI 스켈레톤(`/health`)과 사내 게이트웨이 클라이언트(재시도·타임아웃·임베딩 캐시)를 구축했다.
- `.env` 기반 설정 로딩(`app/config.py`)으로 키를 코드에서 분리했다.
- 게이트웨이 미연결 시 결정적 폴백 임베딩으로 로컬/CI 에서도 파이프라인이 돌도록 했다(chat 은 환각 방지 위해 폴백 불가).
- Qdrant + API 도커 컴포즈 구성.

## 산출물 (어디에)
- `app/config.py` — pydantic-settings 기반 .env 설정. `get_settings()`, `has_gateway_key`.
- `app/gateway/client.py` — `GatewayClient.embed()/chat()`. 재시도/타임아웃/캐시 + 오프라인 폴백.
- `app/main.py` — FastAPI 앱, `/health`. Phase 2 에서 질의 라우터 include 예정.
- `.env.example` — 게이트웨이/임베딩/Qdrant 키·옵션(플레이스홀더).
- `docker-compose.yml` — qdrant + api 서비스.
- `requirements.txt` — 백엔드 의존성.
- `tests/test_gateway_smoke.py` — health·폴백 임베딩 검증(+키 있으면 실호출).

## 다음 단계가 이것을 어떻게 쓰나
- Phase 1 인덱싱이 `GatewayClient.embed()` 로 청크 임베딩을 만든다(오프라인 폴백 가능).
- Phase 2 답변 생성이 `GatewayClient.chat()` 으로 HCX 호출.
- 모든 단계가 `get_settings()` 로 설정을 읽는다.

## 주의/제약 (이어받는 사람이 알아야 할 것)
- 샌드박스/CI 에는 게이트웨이 키·네트워크가 없어 실제 LLM/임베딩 호출은 미검증. `has_gateway_key=False` 시 폴백 임베딩이 쓰인다.
- 폴백 임베딩(해시 256d)은 개발용. 운영 정확도는 실제 Octen 임베딩 필요.
- `chat()` 은 폴백이 없으므로 답변 생성 테스트는 키가 있어야 한다.

## 검증 근거
- `pytest -q tests/` → 2 passed, 1 skipped(키 미설정).
- `verify.py phase_0` → outputs_exist ✓, env_keys ✓, compose_qdrant ✓, no_real_secret ✓.
