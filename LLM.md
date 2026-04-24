# Nimbus Bank Intelligent Support Triage System

## Project Overview

Multi-agent LangGraph system for banking customer support triage. Built for the Wipro Junior FDE Pre-screening Assignment.

**Use case:** Classify incoming support tickets (Fraud, Dispute, Access Issue, Inquiry), retrieve relevant KB articles, draft empathetic responses, enforce compliance guardrails, and route to auto-response or human escalation.

## Deadlines

- GitHub link: April 23, 2026 at 23:59 CST
- In-person presentation: April 24, 2026 at 10:00 CST (Wipro Plano office)

## Architecture

5 specialized agents in a sequential LangGraph `StateGraph` pipeline with one conditional branch:

1. **Security Agent (Input)** — PII redaction, prompt-injection detection, delimiter wrapping
2. **Classifier** — Category, urgency, sentiment, confidence (Claude Haiku, temp 0.0)
3. **Knowledge Retriever** — RAG via ChromaDB + OpenAI embeddings (text-embedding-3-small)
4. **Response Drafter** — Customer-facing response (Claude Sonnet, temp 0.5)
5. **Compliance Critic** — Policy gate, escalation decision (Claude Haiku, temp 0.0)
6. **Security Agent (Output)** — Final PII scrub, structured audit log

Agents communicate via shared `TriageState` TypedDict. Critic can send draft back to Drafter once (max 1 revision). All Fraud/Dispute tickets always escalate.

## Tech Stack

- **Orchestration:** LangGraph 0.2+
- **LLMs:** Claude Haiku (classifier, critic, injection check), Claude Sonnet (drafter)
- **Embeddings:** OpenAI text-embedding-3-small
- **Vector Store:** ChromaDB (in-process)
- **Frontend:** Streamlit
- **Backend:** FastAPI + Uvicorn
- **Deployment:** AWS App Runner (Docker)
- **Observability:** LangSmith
- **Testing:** pytest + 20-ticket eval set

## Directory Structure

```
nimbus-triage/  (project root is WIPER/)
├── src/
│   ├── state.py              # TriageState TypedDict
│   ├── graph.py              # StateGraph assembly + router
│   ├── agents/
│   │   ├── security_input.py # PII + injection detection
│   │   ├── classifier.py     # Ticket classification
│   │   ├── retriever.py      # RAG retrieval
│   │   ├── drafter.py        # Response generation
│   │   ├── critic.py         # Compliance check
│   │   └── security_output.py# Scrub + audit log
│   ├── prompts/
│   │   ├── classifier.md
│   │   ├── drafter.md
│   │   ├── critic.md
│   │   └── injection.md
│   ├── kb/
│   │   ├── articles.json     # 20 KB articles
│   │   └── build_index.py    # ChromaDB ingestion
│   ├── utils/
│   │   ├── pii.py            # Regex PII redaction
│   │   ├── logging.py        # Structured audit logger
│   │   └── models.py         # LLM client wrappers
│   └── app.py                # Streamlit entry point
├── tests/
│   ├── eval_set.json         # 20 labeled test tickets
│   ├── test_agents.py
│   ├── test_graph.py
│   └── test_security.py
├── Dockerfile
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run src/app.py

# Run tests
pytest tests/ -v

# Run eval suite
pytest tests/test_graph.py -v -k "eval"

# Build ChromaDB index
python src/kb/build_index.py

# Build Docker image
docker build -t nimbus-triage .

# Run Docker container
docker run -p 8501:8501 --env-file .env nimbus-triage
```

## Environment Variables

Required in `.env` (see `.env.example`):
- `ANTHROPIC_API_KEY` — For Claude Haiku/Sonnet
- `OPENAI_API_KEY` — For embeddings
- `LANGSMITH_API_KEY` — For tracing (optional)

## Key Design Decisions

- **Sequential pipeline, not parallel:** Retriever needs Classifier output for category-filtered search
- **Shared state, no direct agent calls:** Agents read/write to TriageState only; individually testable
- **Autonomy decreases toward output:** Retriever has high autonomy, Critic has veto power, Security is deterministic
- **Every failure → human escalation:** No silent wrong answers; worst case is over-escalation
- **Revision cap of 1:** Critic can ask Drafter to revise once; prevents runaway cost
- **PII never logged:** Audit logs contain only allow-listed metadata fields

## Conventions

- All agent functions follow signature: `(TriageState) -> dict` (partial state update)
- System prompts live in `src/prompts/*.md`, loaded at agent init
- All LLM calls use structured output (Pydantic models) for type safety
- PII regex patterns centralized in `src/utils/pii.py`
- Use `tenacity` for LLM retry logic (exponential backoff, max 2 retries)
- Temperature 0.0 for classification/critique, 0.5 for drafting
- All test tickets are synthetic — no real customer data anywhere
