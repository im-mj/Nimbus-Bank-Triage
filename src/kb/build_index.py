"""
Nimbus Bank Knowledge Base — ChromaDB Ingestion Script

Reads articles from articles.json, chunks them by paragraph,
embeds using a local sentence-transformer model (no API key needed),
and stores in ChromaDB.

Usage:
    python src/kb/build_index.py
"""

import json
import os

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ── Paths ────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

ARTICLES_PATH = os.environ.get(
    "KB_ARTICLES_PATH",
    os.path.join(os.path.dirname(__file__), "articles.json"),
)
CHROMA_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(ROOT_DIR, "data", "chroma"),
)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "nimbus_kb"


def load_articles(path: str) -> list[dict]:
    """Load KB articles from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_article(article: dict) -> list[dict]:
    """
    Split an article into paragraph-level chunks.
    Each chunk inherits the article's metadata.
    """
    paragraphs = [p.strip() for p in article["content"].split("\n\n") if p.strip()]

    chunks = []
    for i, para in enumerate(paragraphs):
        # Skip very short paragraphs (less than 30 chars) by merging with next
        if len(para) < 30 and chunks:
            chunks[-1]["content"] += "\n\n" + para
            continue

        chunks.append({
            "id": f"{article['id']}_chunk_{i:02d}",
            "kb_id": article["id"],
            "title": article["title"],
            "category": article["category"],
            "subcategory": article.get("subcategory", ""),
            "tags": ",".join(article.get("tags", [])),
            "escalation_required": str(article.get("escalation_required", False)),
            "content": para,
        })

    return chunks


def build_index():
    """Main ingestion pipeline."""
    # Load articles
    articles = load_articles(ARTICLES_PATH)
    print(f"Loaded {len(articles)} articles from {ARTICLES_PATH}")

    # Chunk articles
    all_chunks = []
    for article in articles:
        chunks = chunk_article(article)
        all_chunks.extend(chunks)
    print(f"Created {len(all_chunks)} chunks from {len(articles)} articles")

    # Initialize embedding function (local, no API key)
    print(f"Loading local embedding model: {EMBEDDING_MODEL}...")
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    # Initialize ChromaDB
    os.makedirs(CHROMA_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection if it exists, then recreate
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )

    # Add chunks — ChromaDB handles embedding via the collection's embedding_function
    texts = [chunk["content"] for chunk in all_chunks]
    print(f"Embedding and indexing {len(texts)} chunks...")

    collection.add(
        ids=[chunk["id"] for chunk in all_chunks],
        documents=texts,
        metadatas=[
            {
                "kb_id": chunk["kb_id"],
                "title": chunk["title"],
                "category": chunk["category"],
                "subcategory": chunk["subcategory"],
                "tags": chunk["tags"],
                "escalation_required": chunk["escalation_required"],
            }
            for chunk in all_chunks
        ],
    )

    print(f"Indexed {collection.count()} chunks into ChromaDB at {CHROMA_DIR}")
    print("Done.")


if __name__ == "__main__":
    build_index()
