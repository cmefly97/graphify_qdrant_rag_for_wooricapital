"""Phase 1 인덱싱 테스트 — 추출·청킹·매핑 + 수치 회귀(21.0%)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pipeline import embed_index, extract_tables
from pipeline.chunk import chunk_all
from pipeline.parse import parse_all

ROOT = Path(__file__).resolve().parent.parent


def test_extract_tables_rate_grade_regression():
    info = extract_tables.build()
    assert info["rate_grade_rows"] >= 9
    con = sqlite3.connect(extract_tables.DB_PATH)
    row = con.execute(
        "SELECT gl_rate FROM rate_grade WHERE customer_type='내국인' AND grade=2 "
        "ORDER BY term_min_months LIMIT 1").fetchone()
    con.close()
    assert row is not None and str(row[0]).startswith("21")  # 금리등급 2 → 21.0%


def test_foreigner_term_tier_rate():
    """iter2 개선: 외국인 구간별 GL금리 추출 회귀(등급2·36개월 → 39.0%)."""
    extract_tables.build()
    con = sqlite3.connect(extract_tables.DB_PATH)
    row = con.execute(
        "SELECT gl_rate FROM rate_grade WHERE customer_type='외국인' AND grade=2 AND term_min_months=36").fetchone()
    con.close()
    assert row is not None and str(row[0]).startswith("39")


def test_nego_rule_grade2():
    con = sqlite3.connect(extract_tables.DB_PATH)
    rows = dict(con.execute(
        "SELECT authority, nego_rate FROM nego_rule "
        "WHERE customer_type='내국인' AND grade_from<=2 AND grade_to>=2").fetchall())
    con.close()
    assert rows.get("거점장", "").startswith("11")  # 거점장 11.0%


def test_multi_product_tables():
    """iter+ : 타 상품(중형트럭·재고금융·중고리스 잔가군) 추출 회귀."""
    extract_tables.build()
    con = sqlite3.connect(extract_tables.DB_PATH)
    truck = con.execute("SELECT COUNT(*) FROM condition_rule WHERE product='중형트럭'").fetchone()[0]
    jaego = con.execute("SELECT COUNT(*) FROM condition_rule WHERE product='재고금융'").fetchone()[0]
    groups = con.execute("SELECT grp FROM lease_residual_group WHERE models LIKE '%그랜져 2.4%'").fetchone()
    con.close()
    assert truck >= 10 and jaego >= 5
    assert groups is not None and groups[0] == "S군"


def test_nice_band_real_values():
    """NICE 점수→금리등급 실제값 회귀(원문: 1=933↑, 8=610↑, 9=350↑)."""
    extract_tables.build()
    con = sqlite3.connect(extract_tables.DB_PATH)

    def grade(score):
        r = con.execute("SELECT nice_grade FROM nice_band WHERE ? BETWEEN score_min AND score_max", (score,)).fetchone()
        return r[0] if r else None
    assert grade(940) == 1 and grade(884) == 2 and grade(650) == 8 and grade(400) == 9
    con.close()


def test_multi_product_lookup():
    from app.tables_lookup import lookup
    assert "2~10톤" in lookup("중형트럭 취급톤수 조건")["answer"]
    assert "2.5톤" in lookup("재고금융 화물차 톤수")["answer"]
    assert "S군" in lookup("그랜져 2.4 잔가군")["answer"]


def test_parse_and_chunk_nonempty():
    docs = parse_all()
    assert len(docs) >= 4
    chunks = chunk_all(docs)
    assert len(chunks) > 10
    assert all("source_file" in c["meta"] for c in chunks)


def test_node_chunk_map_built():
    docs = parse_all()
    chunks = chunk_all(docs)
    info = embed_index.build_node_chunk_map(chunks)
    assert info["nodes_mapped"] > 0
    assert embed_index.NODE_CHUNK_MAP.exists()
