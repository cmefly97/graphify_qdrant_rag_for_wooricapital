"""질의·답변 로깅 스토어 (운영 전환 항목 2).

모든 질의/답변/출처/모드/지연시간을 data/query_log.db 에 적재하고, 피드백(👍/👎)과
집계 통계를 제공한다. user_id 는 SSO(항목 1) 도입 전까지 'anonymous'.
로깅은 best-effort — 실패해도 질의 응답 자체를 막지 않는다.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "query_log.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    con = _conn()
    con.execute("""CREATE TABLE IF NOT EXISTS query_log(
        id TEXT PRIMARY KEY, ts REAL, user_id TEXT, query TEXT, route TEXT,
        mode TEXT, confidence TEXT, answer TEXT, sources TEXT,
        latency_ms INTEGER, feedback TEXT)""")
    con.commit()
    con.close()


def log_query(result: dict, latency_ms: int, user_id: str = "anonymous") -> str:
    qid = uuid.uuid4().hex
    try:
        con = _conn()
        con.execute("CREATE TABLE IF NOT EXISTS query_log("
                    "id TEXT PRIMARY KEY, ts REAL, user_id TEXT, query TEXT, route TEXT,"
                    "mode TEXT, confidence TEXT, answer TEXT, sources TEXT,"
                    "latency_ms INTEGER, feedback TEXT)")
        con.execute("INSERT INTO query_log VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (qid, time.time(), user_id, result.get("query", ""), result.get("route"),
                     result.get("mode"), result.get("confidence"), result.get("answer", "")[:2000],
                     json.dumps(result.get("sources", []), ensure_ascii=False),
                     latency_ms, None))
        con.commit()
        con.close()
    except Exception:
        pass  # best-effort
    return qid


def set_feedback(qid: str, vote: str) -> bool:
    if vote not in ("up", "down"):
        return False
    con = _conn()
    cur = con.execute("UPDATE query_log SET feedback=? WHERE id=?", (vote, qid))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


def stats() -> dict:
    con = _conn()
    con.execute("CREATE TABLE IF NOT EXISTS query_log("
                "id TEXT PRIMARY KEY, ts REAL, user_id TEXT, query TEXT, route TEXT,"
                "mode TEXT, confidence TEXT, answer TEXT, sources TEXT,"
                "latency_ms INTEGER, feedback TEXT)")
    total = con.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
    by_mode = {r["mode"]: r["c"] for r in con.execute(
        "SELECT mode, COUNT(*) c FROM query_log GROUP BY mode")}
    no_evidence = con.execute("SELECT COUNT(*) FROM query_log WHERE mode='none'").fetchone()[0]
    avg_latency = con.execute("SELECT AVG(latency_ms) FROM query_log").fetchone()[0] or 0
    fb = {r["feedback"]: r["c"] for r in con.execute(
        "SELECT feedback, COUNT(*) c FROM query_log WHERE feedback IS NOT NULL GROUP BY feedback")}
    top = [{"query": r["query"], "count": r["c"]} for r in con.execute(
        "SELECT query, COUNT(*) c FROM query_log GROUP BY query ORDER BY c DESC LIMIT 10")]
    con.close()
    return {
        "total_queries": total,
        "by_mode": by_mode,
        "no_evidence_rate": round(no_evidence / total, 3) if total else 0,
        "avg_latency_ms": round(avg_latency, 1),
        "feedback": fb,
        "top_queries": top,
    }
