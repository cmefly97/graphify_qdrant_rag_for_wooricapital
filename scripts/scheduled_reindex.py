#!/usr/bin/env python3
"""자동 재인덱싱 스케줄러 (운영 전환 항목 3).

월별 운영기준 갱신 시 실행: 표 재추출 → (옵션)재임베딩/적재 → 회귀 게이트(eval) →
게이트 통과 시에만 '반영(promote)'으로 기록. 실패 시 비정상 종료(알림용)하고 버전을 FAILED 로 남긴다.
재인덱싱 이력은 data/reindex_versions.jsonl 에 누적(시각·소스해시·산출물수·게이트결과).

사내 cron 예: 매월 1일 02:00 →  0 2 1 * *  cd <repo> && .venv/bin/python scripts/scheduled_reindex.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SOURCE_DIR = ROOT / "souce"
VERSIONS = ROOT / "data" / "reindex_versions.jsonl"


def source_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(SOURCE_DIR.iterdir()):
        if p.is_file():
            h.update(p.name.encode())
            h.update(str(p.stat().st_size).encode())
    return h.hexdigest()[:16]


def _record(entry: dict) -> None:
    VERSIONS.parent.mkdir(parents=True, exist_ok=True)
    with VERSIONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run(run_embed: bool = True) -> dict:
    from eval.gate import regression_gate
    from eval.run_eval import evaluate, write_report
    from pipeline import embed_index, extract_tables

    t0 = time.time()
    tbl = extract_tables.build()
    idx = embed_index.build() if run_embed else {"note": "embed skipped"}
    metrics = evaluate()
    write_report(metrics)
    passed, fails = regression_gate(metrics)

    entry = {
        "ts": time.time(),
        "source_hash": source_hash(),
        "tables": tbl,
        "index": {k: idx.get(k) for k in ("chunks", "dim", "qdrant")} if run_embed else idx,
        "metrics": {k: metrics.get(k) for k in ("accuracy", "numeric_accuracy", "source_rate")},
        "gate": "PROMOTED" if passed else "FAILED",
        "violations": fails,
        "elapsed_s": round(time.time() - t0, 1),
    }
    _record(entry)
    return {"promoted": passed, "violations": fails, "entry": entry}


def main() -> int:
    res = run(run_embed=True)
    if res["promoted"]:
        print(f"[scheduled_reindex] PROMOTED. {res['entry']['metrics']}")
        return 0
    print(f"[scheduled_reindex] FAILED gate — 반영 보류. 위반: {res['violations']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
