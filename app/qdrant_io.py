"""Qdrant 입출력 헬퍼 — 적재(인덱싱)와 검색(질의) 공용.

- QDRANT_URL 에 닿으면 Qdrant 사용, 아니면 호출측에서 로컬 폴백.
- 컬렉션은 적재 시 실제 벡터 길이로 (재)생성(distance=Cosine) → 폴백(256d)·
  실제(4096d) 차원 혼입을 원천 차단.
- qdrant-client 는 지연 임포트(미설치 환경에서도 모듈 임포트가 깨지지 않게).
"""
from __future__ import annotations

from app.config import Settings


def get_client(s: Settings):
    """연결 가능한 QdrantClient 반환, 불가하면 None."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=s.qdrant_url, api_key=(s.qdrant_api_key or None), timeout=5)
        client.get_collections()  # 연결 확인(핑)
        return client
    except Exception:
        return None


def ensure_collection(client, name: str, dim: int) -> None:
    from qdrant_client.models import Distance, VectorParams

    client.recreate_collection(
        collection_name=name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


def upsert(client, name: str, records: list[dict]) -> int:
    """records: [{id(str), vector, meta}]. point id 는 정수, chunk_id 는 payload 에 보관."""
    from qdrant_client.models import PointStruct

    points = [
        PointStruct(id=i, vector=r["vector"],
                    payload={"chunk_id": r["id"], **r.get("meta", {})})
        for i, r in enumerate(records)
    ]
    client.upsert(collection_name=name, points=points)
    return len(points)


def search(client, name: str, query_vector: list[float], k: int = 5) -> list[dict]:
    hits = client.search(collection_name=name, query_vector=query_vector, limit=k)
    return [{"id": h.payload.get("chunk_id"), "meta": h.payload, "score": float(h.score)} for h in hits]
