"""운영전환 항목 2 — 질의 로깅·피드백·통계 테스트."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import logging_store
from app.main import app

client = TestClient(app)


def test_ask_logs_and_returns_query_id():
    r = client.post("/ask", json={"query": "금리등급 2등급 금리"})
    assert r.status_code == 200
    body = r.json()
    assert body["query_id"]
    assert "21.0%" in body["answer"]


def test_feedback_updates():
    r = client.post("/ask", json={"query": "엔카 슬라이딩 가능해?"})
    qid = r.json()["query_id"]
    fb = client.post("/feedback", json={"query_id": qid, "vote": "up"})
    assert fb.json()["ok"] is True
    bad = client.post("/feedback", json={"query_id": "nonexistent", "vote": "up"})
    assert bad.json()["ok"] is False


def test_stats_aggregates():
    client.post("/ask", json={"query": "듀얼상품 금리등급 몇등급까지?"})
    s = client.get("/stats").json()
    assert s["total_queries"] >= 1
    assert "by_mode" in s and isinstance(s["top_queries"], list)


def test_invalid_vote_rejected():
    assert logging_store.set_feedback("x", "maybe") is False


def test_web_pages_served():
    # 채팅 화면과 대시보드가 HTML 로 서빙되는지
    root = client.get("/")
    assert root.status_code == 200 and "상담챗봇" in root.text and "/ask" in root.text
    dash = client.get("/dashboard")
    assert dash.status_code == 200 and "대시보드" in dash.text
