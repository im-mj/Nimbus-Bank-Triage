# Step 3 — Vector Store Ingestion (Teaching the System to Search by Meaning)

## What This Does

The knowledge base articles are stored as JSON text, but the AI cannot just do a keyword search like Google — it needs to understand the *meaning* behind a customer's words and find the articles that are most relevant, even if the customer uses completely different wording than what is in the article.

This step takes each knowledge base article, converts it into a mathematical representation called an "embedding," and stores it in a specialized database (ChromaDB) designed for fast similarity searches.

## How It Works in Plain English

1. **Load the articles.** The script reads all 20 articles from the JSON file.

2. **Break articles into chunks.** Long articles are split at paragraph boundaries so that the search can match on specific sections rather than entire documents. This makes results more precise — a paragraph about "Regulation E timelines" is more useful than a whole article about fraud when the customer is asking about deadlines.

3. **Create embeddings.** Each chunk is sent to OpenAI's embedding model, which converts the text into a list of numbers (a vector) that captures its meaning. Texts with similar meanings end up with similar numbers — so "someone used my card without permission" and "unauthorized debit card transaction" produce nearly identical vectors even though they share few words.

4. **Store in ChromaDB.** The vectors and their associated metadata (article ID, title, category, tags) are stored in ChromaDB, a lightweight vector database that runs locally inside the application. No external database server is needed.

5. **Persist to disk.** The database is saved to the `data/chroma/` directory so it does not need to be rebuilt every time the application starts.

## Why This Design

- **Semantic search, not keyword search.** Customers describe problems in their own words. Embedding-based search finds the right articles regardless of exact wording.
- **Category filtering.** Each chunk carries its category as metadata, so the Retriever agent can search within a specific category (e.g., only Fraud articles) for more precise results.
- **Runs in-process.** ChromaDB runs inside the Python application — no separate server to manage, perfect for a single-instance deployment.
- **One-time cost.** Embedding the 20 articles costs a fraction of a cent and only needs to happen once. After that, the persisted database loads instantly.
