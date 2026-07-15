"""재랭킹 — 테이블 결과 우선 + 벡터 점수 정렬 + 중복 제거.

수치형 정답(테이블)을 최상위 근거로 두고, 설명 보강용 벡터 컨텍스트를
점수순으로 덧붙인다. 운영에서는 유효일자 최신본 가중을 추가한다.
"""
from __future__ import annotations


def rerank(contexts: list[dict], table_result: dict | None = None) -> list[dict]:
    ordered: list[dict] = []
    seen: set[str] = set()
    if table_result:
        ordered.append({"text": table_result["answer"], "score": 1.0,
                        "source": (table_result["sources"][0] if table_result.get("sources") else {}),
                        "kind": "table"})
    for c in sorted(contexts, key=lambda x: x.get("score", 0), reverse=True):
        key = c.get("text", "")[:60]
        if key in seen:
            continue
        seen.add(key)
        ordered.append({**c, "kind": "vector"})
    return ordered
