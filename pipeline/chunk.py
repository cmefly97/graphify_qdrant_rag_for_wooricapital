"""청킹 — FAQ는 Q-A 1쌍=1청크, 규정/운영기준은 문단·헤딩 단위.

각 청크는 검색·출처에 쓰일 메타데이터를 보유한다.
"""
from __future__ import annotations

import re


def _cid(source: str, idx: int) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "_", source)[:40]
    return f"{base}__{idx}"


def chunk_document(doc: dict) -> list[dict]:
    meta = doc["meta"]
    chunks: list[dict] = []

    if doc["kind"] == "rows":  # FAQ
        for i, row in enumerate(doc["rows"]):
            q = row.get("질문", "")
            a = row.get("답변", "")
            if not (q or a):
                continue
            chunks.append({
                "id": _cid(meta["source_file"], i),
                "text": f"질문: {q}\n답변: {a}",
                "meta": {**meta, "question": q},
            })
        return chunks

    text = doc.get("text", "")
    # 빈 줄 또는 항목/조항 헤딩 기준 분할, 너무 짧은 조각은 병합
    raw = re.split(r"\n\s*\n|\n(?=\d+[.)]\s)|\n(?=제\s*\d+\s*조)", text)
    buf = ""
    idx = 0
    for seg in raw:
        seg = seg.strip()
        if not seg:
            continue
        buf = (buf + "\n" + seg).strip() if buf else seg
        if len(buf) >= 120:
            chunks.append({"id": _cid(meta["source_file"], idx), "text": buf, "meta": dict(meta)})
            idx += 1
            buf = ""
    if buf:
        chunks.append({"id": _cid(meta["source_file"], idx), "text": buf, "meta": dict(meta)})
    return chunks


def chunk_all(docs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for d in docs:
        out.extend(chunk_document(d))
    return out
