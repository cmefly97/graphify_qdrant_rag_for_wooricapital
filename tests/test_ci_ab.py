"""운영전환 항목 3·5 — 회귀 게이트, A/B 비교, 스케줄러 프로모션 테스트."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from eval.ab_test import compare
from eval.gate import regression_gate

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- 회귀 게이트 ---
def test_gate_pass():
    ok, fails = regression_gate({"numeric_accuracy": 1.0, "accuracy": 1.0, "source_rate": 1.0})
    assert ok and not fails


def test_gate_fail_on_numeric_regression():
    ok, fails = regression_gate({"numeric_accuracy": 0.9, "accuracy": 1.0, "source_rate": 1.0})
    assert not ok and any("numeric_accuracy" in f for f in fails)


# --- A/B 비교 ---
def test_ab_detects_regression():
    base = {"q1": {"ok": True, "answer": "21.0%"}, "q2": {"ok": True, "answer": "x"}}
    cur = [{"id": "q1", "ok": False, "mode": "none", "answer": "-"},
           {"id": "q2", "ok": True, "mode": "table", "answer": "x"}]
    d = compare(cur, base)
    assert d["regressed"] == ["q1"] and d["same"] >= 1


def test_ab_detects_improvement_and_change():
    base = {"q1": {"ok": False, "answer": "-"}, "q2": {"ok": True, "answer": "old"}}
    cur = [{"id": "q1", "ok": True, "mode": "table", "answer": "21.0%"},
           {"id": "q2", "ok": True, "mode": "table", "answer": "new"}]
    d = compare(cur, base)
    assert d["improved"] == ["q1"] and d["answer_changed"] == ["q2"]


# --- 스케줄러: 회귀 게이트 통과 시 PROMOTED + 버전 기록 ---
def test_scheduler_promotes_and_logs():
    sched = _load("scheduled_reindex", "scripts/scheduled_reindex.py")
    res = sched.run(run_embed=False)
    assert res["promoted"] is True
    assert (ROOT / "data" / "reindex_versions.jsonl").exists()
    assert res["entry"]["gate"] == "PROMOTED"
