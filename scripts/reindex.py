#!/usr/bin/env python3
"""재인덱싱 원스톱 — 사내망(게이트웨이+Qdrant 접근 가능)에서 실행.

순서: tables.db 추출 → 실제 Octen 임베딩으로 벡터 생성/Qdrant 적재 → 평가 회귀.
Qdrant 는 QDRANT_URL 에 닿으면 컬렉션을 실제 차원으로 재생성 후 적재, 아니면 로컬 폴백.

사용: python scripts/reindex.py
주의: .env 의 EMBEDDING_API_KEY 가 유효해야 실제 4096d 임베딩이 생성된다(미설정/미연결 시 256d 폴백).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from pipeline import embed_index, extract_tables  # noqa: E402


def main() -> int:
    s = get_settings()
    print(f"게이트웨이 키: {s.has_gateway_key} | Qdrant: {s.qdrant_url} | 컬렉션: {s.qdrant_collection}")
    print("1) tables.db 추출 …", extract_tables.build())
    print("2) 임베딩/적재 …", info := embed_index.build())
    if info["dim"] < 1024:
        print("⚠ 경고: 차원이 작습니다(폴백 임베딩 의심). 실제 Octen 임베딩은 4096d 입니다. "
              "게이트웨이 연결을 확인하고 재실행하세요.")
    if info["qdrant"].startswith("skipped"):
        print("⚠ 경고: Qdrant 미적재(연결 실패). QDRANT_URL 접근을 확인하세요. 현재 로컬 폴백 사용.")
    print("3) 평가 회귀 …")
    from eval.run_eval import evaluate, write_report
    m = evaluate(); write_report(m)
    print(f"   accuracy={m['accuracy']} numeric={m['numeric_accuracy']} source={m['source_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
