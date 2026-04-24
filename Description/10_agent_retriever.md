# Step 10 — Knowledge Retriever Agent (The Policy Librarian)

## What This Does

When a human support agent gets a ticket, they mentally search their training and policy documents for the right information. The Knowledge Retriever does this automatically — it searches the bank's entire policy library and pulls out the most relevant articles for the specific ticket at hand.

This is the foundation of "grounded responses." Instead of letting the AI make up answers from its general training, the Retriever forces it to work from specific, approved bank documents.

## How It Works in Plain English

The Retriever performs a two-pronged search:

**Search 1: Full corpus search.** It takes the ticket text and searches across all 20 knowledge base articles for the best matches based on meaning similarity. This catches relevant articles even if they are in a different category than expected.

**Search 2: Category-filtered search.** It takes the same ticket text but only searches within articles that match the Classifier's category. For example, if the ticket was classified as "Fraud," this search only looks at the 5 fraud articles. This produces more focused, relevant results.

**Merge and deduplicate.** The results from both searches are combined. Category-filtered results are given priority because they are usually more relevant. Duplicate articles are removed. The top 5 unique results are kept, each with a similarity score indicating how well it matched the ticket.

**Fallback for weak matches.** If the best similarity score is below 0.60 (meaning nothing in the library is a strong match), the Retriever returns an empty result and sets a flag. When the Drafter sees this flag, it will honestly tell the customer: "I don't have a specific answer for this — I'm routing you to a specialist."

## Why This Design

- **Two searches are better than one.** The full-corpus search catches cross-category relevance (e.g., a fraud ticket that also involves account access). The filtered search ensures the primary category's articles are well-represented.
- **Similarity scores enable quality control.** Downstream agents can see how confident the retrieval was. A response grounded in a 0.92 match is very different from one grounded in a 0.45 match.
- **Honest about gaps.** The system does not pretend to know things it does not. When the knowledge base does not have a strong answer, the system says so rather than hallucinating one.
- **No LLM used here.** The Retriever uses an embedding model (mathematical similarity), not a reasoning model. This is fast, cheap, and deterministic.
