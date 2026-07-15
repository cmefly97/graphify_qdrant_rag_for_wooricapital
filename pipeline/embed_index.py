"""임베딩 인덱싱 + 그래프 노드↔청크 매핑.

- 청크를 GatewayClient.embed() 로 임베딩(게이트웨이 미연결 시 폴백).
- 벡터 저장: Qdrant 가 떠 있으면 적재, 아니면 data/vector_store.json 로컬 폴백.
- graphify-out/graph.json 노드를 source_file 기준으로 청크와 매핑 → data/node_chunk_map.json.
  이로써 그래프 탐색 결과를 실제 근거 청크로 환원할 수 있다.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.gateway.client import GatewayClient
from pipeline.chunk import chunk_all
from pipeline.parse import parse_all

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GRAPH_JSON = ROOT / "graphify-out" / "graph.json"
VECTOR_STORE = DATA / "vector_store.json"
NODE_CHUNK_MAP = DATA / "node_chunk_map.json"


def build_vector_store(chunks: list[dict], gc: GatewayClient) -> dict:
    from app import qdrant_io

    DATA.mkdir(parents=True, exist_ok=True)

    def _progress(done: int, total: int) -> None:
        print(f"\r  임베딩 {done}/{total}", end="", flush=True)

    vectors = gc.embed_many([c["text"] for c in chunks], batch_size=32, progress=_progress)
    print()  # 진행률 줄 마무리
    records = [{"id": c["id"], "text": c["text"], "meta": c["meta"], "vector": v}
               for c, v in zip(chunks, vectors)]
    dim = len(records[0]["vector"]) if records else gc.s.embedding_dim

    # 로컬 폴백 저장(오프라인 개발/검색용) — 항상 유지
    VECTOR_STORE.write_text(json.dumps(
        [{"id": r["id"], "meta": r["meta"], "vector": r["vector"]} for r in records],
        ensure_ascii=False), encoding="utf-8")

    # Qdrant 적재(URL 에 닿을 때만). 컬렉션은 실제 차원으로 재생성 → 차원 혼입 방지.
    qstatus = "skipped(no-connection)"
    client = qdrant_io.get_client(gc.s)
    if client is not None:
        qdrant_io.ensure_collection(client, gc.s.qdrant_collection, dim)
        n = qdrant_io.upsert(client, gc.s.qdrant_collection, records)
        qstatus = f"upserted {n} → {gc.s.qdrant_collection}(dim={dim})"
    return {"vectors": len(records), "dim": dim, "qdrant": qstatus}


def build_node_chunk_map(chunks: list[dict]) -> dict:
    by_source: dict[str, list[str]] = {}
    for c in chunks:
        by_source.setdefault(c["meta"]["source_file"], []).append(c["id"])
    mapping: dict[str, dict] = {}
    if GRAPH_JSON.exists():
        graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        for node in graph.get("nodes", []):
            src = node.get("source_file")
            mapping[node["id"]] = {
                "label": node.get("label"),
                "source_file": src,
                "chunk_ids": by_source.get(src, []),
            }
    NODE_CHUNK_MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"nodes_mapped": len(mapping)}


def build() -> dict:
    docs = parse_all()
    chunks = chunk_all(docs)
    gc = GatewayClient()
    vs = build_vector_store(chunks, gc)
    nm = build_node_chunk_map(chunks)
    return {"docs": len(docs), "chunks": len(chunks), **vs, **nm}


if __name__ == "__main__":
    print(build())
