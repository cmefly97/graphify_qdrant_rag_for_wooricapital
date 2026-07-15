"""phase_1 커스텀 검증 — 인덱싱 산출물 점검.

핵심: tables.db 가 만들어졌다면 예시 질의(금리등급 2 → 21.0%)를 실제로
조회할 수 있는지 확인하여 '수치 정확성'을 회귀 검증한다.
산출물이 없으면 통과(skip).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def check(root: Path) -> list[dict]:
    results: list[dict] = []

    db = root / "data" / "tables.db"
    if db.exists():
        try:
            con = sqlite3.connect(str(db))
            cur = con.cursor()
            # rate_grade 테이블에서 내국인 금리등급 2 의 GL금리가 21.0% 인지(샘플 회귀)
            row = cur.execute(
                "SELECT gl_rate FROM rate_grade "
                "WHERE customer_type='내국인' AND grade=2 "
                "ORDER BY term_min_months LIMIT 1"
            ).fetchone()
            con.close()
            ok = row is not None and str(row[0]).startswith("21")
            results.append({
                "name": "rate_grade_sample",
                "ok": ok,
                "detail": f"내국인 등급2 GL금리={row[0] if row else '없음'} (기대 21.0%)",
                "blocking": True,
            })
        except Exception as e:  # noqa: BLE001
            results.append({
                "name": "rate_grade_sample",
                "ok": False,
                "detail": f"tables.db 조회 실패: {e}",
                "blocking": True,
            })

    mapping = root / "data" / "node_chunk_map.json"
    if mapping.exists():
        results.append({
            "name": "node_chunk_map",
            "ok": mapping.stat().st_size > 2,
            "detail": "노드↔청크 매핑 존재",
            "blocking": True,
        })

    return results
