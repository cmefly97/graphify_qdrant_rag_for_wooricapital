"""Phase 2 질의엔진 테스트 — PRD 대표 5개 질의의 정확 답변/출처.

수치·규칙형은 tables.db 기반으로 결정적 검증(환각 0). 근거 없는 질의는 '모름'.
"""
from __future__ import annotations

from app.api import answer_query


def test_q1_term_months():
    r = answer_query("론/할부 상품 취급 가능 개월수가 어떻게돼?")
    assert "12~72개월" in r["answer"]
    assert r["mode"] == "table" and r["sources"]


def test_q2_rate_grade2():
    r = answer_query("론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘")
    assert "21.0%" in r["answer"]
    assert "거점장 네고 11.0%" in r["answer"]
    assert "NICE 2등급" in r["answer"]  # NICE 885점 = 884~932 구간(원문 실제 등급표)
    assert r["mode"] == "table"


def test_q3_dual_grade():
    r = answer_query("듀얼상품 금리등급 몇등급까지 취급 가능해?")
    assert "7등급" in r["answer"]
    assert r["mode"] == "table"


def test_q4_encar_sliding():
    r = answer_query("엔카 슬라이딩 가능해?")
    assert "조건부 가능" in r["answer"]
    assert "19년식" in r["answer"]


def test_q5_r_pandan():
    r = answer_query("신용회복, 개인회생 고객인데 판정값이 R 판정이야")
    assert "필터링 취급 불가" in r["answer"]


def test_nego_overview_not_dual():
    # '내국인 네고 조건' 이 Dual 등급 행에 오매칭되지 않고 네고 요약을 반환해야 함
    r = answer_query("내국인 네고 조건이 어떻게 돼?")
    assert "Dual" not in r["answer"]
    assert "네고" in r["answer"]


def test_unknown_returns_no_evidence_or_context():
    r = answer_query("주말에 회식 어디서 할까?")
    # 근거 없으면 '모름' 또는 낮은 신뢰 컨텍스트
    assert r["mode"] in ("none", "context_only", "llm")
