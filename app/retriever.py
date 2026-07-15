"""하이브리드 검색 — 벡터 유사도(시작점) + 그래프 탐색(맥락 확장).

- 벡터: data/vector_store.json (운영 시 Qdrant) 코사인 유사도.
- 그래프: graphify-out/graph.json (NetworkX) 1~2홉 확장.
- node_chunk_map.json 으로 그래프 노드를 근거 청크로 환원.
청크 본문은 parse+chunk 로 즉석 복원(운영에서는 docstore).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import networkx as nx

from app.gateway.client import GatewayClient
from pipeline.chunk import chunk_all
from pipeline.parse import parse_all

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GRAPH_JSON = ROOT / "graphify-out" / "graph.json"


@lru_cache(maxsize=1)
def _chunk_text() -> dict[str, dict]:
    return {c["id"]: c for c in chunk_all(parse_all())}


@lru_cache(maxsize=1)
def _vectors() -> list[dict]:
    p = DATA / "vector_store.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@lru_cache(maxsize=1)
def _graph() -> nx.Graph:
    g = nx.Graph()
    if GRAPH_JSON.exists():
        data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        for n in data.get("nodes", []):
            g.add_node(n["id"], **n)
        for e in data.get("links", []):
            g.add_edge(e["source"], e["target"], **e)
    return g


def _cosine(a: list[float], b: list[float]) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(y * y for y in b) ** 0.5 or 1.0
    return s / (na * nb)


def vector_search(query: str, gc: GatewayClient, k: int = 5) -> list[dict]:
    qv = gc.embed(query)
    # Qdrant 에 닿으면 Qdrant 검색, 아니면 로컬 벡터스토어 코사인
    from app import qdrant_io

    client = qdrant_io.get_client(gc.s)
    if client is not None:
        try:
            return qdrant_io.search(client, gc.s.qdrant_collection, qv, k)
        except Exception:
            pass
    scored = [{"id": r["id"], "meta": r["meta"], "score": _cosine(qv, r["vector"])}
              for r in _vectors()]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


def graph_expand(seed_source_files: set[str], query: str | None = None, hops: int = 1) -> list[str]:
    import re

    g = _graph()
    seeds = {n for n, d in g.nodes(data=True) if d.get("source_file") in seed_source_files}
    # 질의어와 라벨이 겹치는 개념 노드도 시드로(벡터 히트가 그래프 빈약 문서일 때 보강)
    if query:
        toks = [t for t in re.findall(r"[가-힣A-Za-z0-9]{2,}", query)]
        for n, d in g.nodes(data=True):
            label = d.get("label", "")
            if any(t in label for t in toks):
                seeds.add(n)
    seeds = list(dict.fromkeys(seeds))  # 순서 보존 dedupe
    reached = set(seeds)
    frontier = set(seeds)
    for _ in range(hops):
        nxt = set()
        for node in frontier:
            nxt.update(g.neighbors(node))
        reached.update(nxt)
        frontier = nxt
    # 시드(직접 매칭)를 앞에, 확장 노드를 뒤에 — 노드 id 반환
    return seeds + [n for n in reached if n not in seeds]


def retrieve(query: str, gc: GatewayClient, k: int = 5) -> dict:
    import time

    t0 = time.perf_counter()
    hits = vector_search(query, gc, k)
    vector_ms = round((time.perf_counter() - t0) * 1000, 1)

    texts = _chunk_text()
    seed_files = {h["meta"].get("source_file") for h in hits}
    t1 = time.perf_counter()
    node_ids = graph_expand(seed_files, query=query, hops=1)
    graph_ms = round((time.perf_counter() - t1) * 1000, 1)
    g = _graph()
    evidence_nodes = [g.nodes[n].get("label", n) for n in node_ids][:12]
    graph_sources = [{"label": g.nodes[n].get("label", n),
                      "source_file": g.nodes[n].get("source_file")} for n in node_ids][:8]

    contexts = []
    vector_hits = []
    for h in hits:
        c = texts.get(h["id"])
        sf = (c["meta"].get("source_file") if c else h["meta"].get("source_file"))
        vector_hits.append({"id": h["id"], "score": round(h["score"], 3), "source_file": sf})
        if c:
            contexts.append({"text": c["text"][:800], "score": round(h["score"], 3),
                             "source": {"source_file": c["meta"].get("source_file"),
                                        "doc_type": c["meta"].get("doc_type")}})
    return {"contexts": contexts, "evidence_nodes": evidence_nodes,
            "graph_sources": graph_sources,
            "vector_hits": vector_hits, "seed_files": sorted(f for f in seed_files if f),
            "timings": {"vector_ms": vector_ms, "graph_ms": graph_ms}}
