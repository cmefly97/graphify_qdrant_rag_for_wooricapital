"""Phase 0 스모크 테스트.

- 게이트웨이 키가 없으면 실제 호출 테스트는 skip(오프라인/CI 안전).
- 키와 무관하게 임베딩 폴백·설정 로딩·health 응답은 항상 검증한다.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.gateway.client import GatewayClient
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_embedding_fallback_deterministic():
    s = get_settings()
    s.allow_offline_fallback = True
    s.embedding_api_key = ""  # 폴백 경로 강제
    gc = GatewayClient(s)
    v1 = gc.embed("금리등급 2등급 최저금리")
    v2 = gc.embed("금리등급 2등급 최저금리")
    assert v1 == v2  # 결정적
    assert abs(sum(x * x for x in v1) ** 0.5 - 1.0) < 1e-6  # 정규화


def test_chat_sends_max_tokens():
    # chat 페이로드에 max_tokens 가 실려 답변 잘림을 방지하는지 검증(_post 모킹)
    s = get_settings()
    s.hcx30_api_key = "sk-test-key-1234567890"  # has_gateway_key True 로
    s.answer_max_tokens = 2048
    gc = GatewayClient(s)
    captured = {}

    def fake_post(url, payload, api_key):
        captured.update(payload)
        captured["_api_key"] = api_key
        return {"choices": [{"message": {"content": "ok"}}]}

    gc._post = fake_post  # type: ignore
    out = gc.chat([{"role": "user", "content": "hi"}])
    assert out == "ok"
    assert captured.get("max_tokens") == 2048
    assert captured["_api_key"] == "sk-test-key-1234567890"
    s.hcx30_api_key = ""  # 원복


def test_real_gateway_if_configured():
    import pytest

    s = get_settings()
    if not s.has_gateway_key:
        pytest.skip("게이트웨이 키 미설정 — 실제 호출 테스트 skip")
    gc = GatewayClient(s)
    v = gc.embed("테스트")
    assert isinstance(v, list) and len(v) > 0
