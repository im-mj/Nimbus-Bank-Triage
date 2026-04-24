"""
Nimbus Bank Triage — Knowledge Retriever Agent

Performs dual semantic search over the ChromaDB knowledge base:
1. Full-corpus search on ticket text
2. Category-filtered search for focused results
Results are merged, deduplicated, and returned as top-5 chunks.

Uses local sentence-transformer embeddings (no API key needed).
"""

import os
from functools import lru_cache

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

# ── Config ───────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

CHROMA_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(ROOT_DIR, "data", "chroma"),
)
COLLECTION_NAME = "nimbus_kb"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = float(os.environ.get("RETRIEVAL_SIMILARITY_THRESHOLD", "0.60"))
TOP_K = 5

# ── Embedding function (shared instance) ─────────────────────
@lru_cache(maxsize=1)
def _get_embedding_fn():
    """Create the embedding function lazily so imports stay lightweight."""
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def _get_collection():
    """Get the ChromaDB collection with the local embedding function."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_fn(),
    )


def _embed_query(text: str) -> list[float]:
    """Embed a query string using the local sentence-transformer."""
    return _get_embedding_fn()([text])[0]


def _query_collection(
    collection,
    query_embedding: list[float],
    n_results: int = TOP_K,
    where_filter: dict | None = None,
) -> list[dict]:
    """
    Query ChromaDB and return results as a list of dicts.
    Each dict has: kb_id, title, content, similarity, category.
    """
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    try:
        results = collection.query(**kwargs)
    except Exception:
        return []

    chunks = []
    if not results or not results.get("ids") or not results["ids"][0]:
        return chunks

    for i, doc_id in enumerate(results["ids"][0]):
        # ChromaDB returns cosine distance; similarity = 1 - distance
        distance = results["distances"][0][i]
        similarity = 1.0 - distance

        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        content = results["documents"][0][i] if results.get("documents") else ""

        chunks.append({
            "kb_id": metadata.get("kb_id", doc_id),
            "title": metadata.get("title", ""),
            "content": content,
            "similarity": round(similarity, 4),
            "category": metadata.get("category", ""),
        })

    return chunks


def retrieve_kb(state: dict) -> dict:
    """
    Knowledge Retriever Agent node function.

    Performs dual search (full corpus + category filtered),
    merges results with category-filtered priority, deduplicates,
    and returns top-5 chunks.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with retrieved_chunks and retrieval_top_score.
    """
    sanitized_ticket = state.get("sanitized_ticket", "")
    category = state.get("category", "")
    errors = list(state.get("errors", []))

    try:
        collection = _get_collection()
        query_embedding = _embed_query(sanitized_ticket)

        # ── Search 1: Full corpus ────────────────────────────
        full_results = _query_collection(
            collection, query_embedding, n_results=TOP_K
        )

        # ── Search 2: Category-filtered ──────────────────────
        filtered_results = []
        if category:
            filtered_results = _query_collection(
                collection,
                query_embedding,
                n_results=TOP_K,
                where_filter={"category": category},
            )

        # ── Merge: category-filtered first, then fill from full ─
        seen_ids: set[str] = set()
        merged: list[dict] = []

        # Priority: filtered results first
        for chunk in filtered_results:
            if chunk["kb_id"] not in seen_ids:
                seen_ids.add(chunk["kb_id"])
                merged.append(chunk)

        # Fill remaining slots from full results
        for chunk in full_results:
            if chunk["kb_id"] not in seen_ids and len(merged) < TOP_K:
                seen_ids.add(chunk["kb_id"])
                merged.append(chunk)

        # Sort by similarity descending
        merged.sort(key=lambda x: x["similarity"], reverse=True)
        top_chunks = merged[:TOP_K]

        # Determine top score
        top_score = top_chunks[0]["similarity"] if top_chunks else 0.0

        # If best match is below threshold, return empty (forces drafter to acknowledge gap)
        if top_score < SIMILARITY_THRESHOLD:
            return {
                "retrieved_chunks": [],
                "retrieval_top_score": top_score,
                "errors": errors,
            }

        # Strip internal 'category' field before passing downstream
        clean_chunks = [
            {
                "kb_id": c["kb_id"],
                "title": c["title"],
                "content": c["content"],
                "similarity": c["similarity"],
            }
            for c in top_chunks
        ]

        return {
            "retrieved_chunks": clean_chunks,
            "retrieval_top_score": top_score,
            "errors": errors,
        }

    except Exception as e:
        # Retrieval failure → drafter gets empty chunks and acknowledges gap
        errors.append(f"retriever_error: {type(e).__name__}: {e}")
        return {
            "retrieved_chunks": [],
            "retrieval_top_score": 0.0,
            "errors": errors,
        }
