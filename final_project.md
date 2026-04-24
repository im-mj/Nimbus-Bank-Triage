# Final Project

## Project Title

Nimbus Bank Intelligent Support Triage System

## Final Status

This project is complete and working in both environments:

- Local Windows runtime
- Public Hugging Face Docker Space

Live deployment:

- Hugging Face Space: `https://huggingface.co/spaces/MrNoOne07/Nimbus-Bank-Triage`

## Project Goal

Build a multi-agent AI support workflow for a banking use case that can:

- accept a customer support ticket
- classify the ticket
- retrieve relevant knowledge base content
- draft a response
- review the response for policy and safety
- either auto-respond or escalate to a human
- redact PII and write audit metadata

## Core Stack

- Python
- Streamlit
- LangGraph
- Anthropic via `langchain-anthropic`
- ChromaDB
- Sentence Transformers
- Pytest
- Hugging Face Spaces with Docker

## Final Architecture

The runtime flow is:

1. `security_in`
2. `classifier`
3. `retriever`
4. `drafter`
5. `critic`
6. `security_out`

Main orchestration files:

- [src/graph.py](./src/graph.py)
- [src/pipeline.py](./src/pipeline.py)
- [src/state.py](./src/state.py)

Main UI entrypoint:

- [src/app.py](./src/app.py)

## Agents Used

- [src/agents/security_input.py](./src/agents/security_input.py)
  - input PII redaction
  - prompt injection check
  - safe payload wrapping

- [src/agents/classifier.py](./src/agents/classifier.py)
  - category classification
  - urgency detection
  - sentiment detection
  - confidence scoring

- [src/agents/retriever.py](./src/agents/retriever.py)
  - knowledge base retrieval from Chroma

- [src/agents/drafter.py](./src/agents/drafter.py)
  - customer-facing draft generation

- [src/agents/critic.py](./src/agents/critic.py)
  - compliance check
  - escalation decision
  - revision loop control

- [src/agents/security_output.py](./src/agents/security_output.py)
  - final output scrub
  - audit log creation

## Important Supporting Files

- [src/utils/models.py](./src/utils/models.py) - model client setup and retry logic
- [src/utils/pii.py](./src/utils/pii.py) - regex-based PII detection/redaction
- [src/utils/logging.py](./src/utils/logging.py) - audit logging
- [src/kb/articles.json](./src/kb/articles.json) - source knowledge base
- [src/kb/build_index.py](./src/kb/build_index.py) - Chroma index builder
- [src/prompts](./src/prompts) - system prompts for agents
- [tests](./tests) - test suite

## Final Workflow

When a user submits a ticket:

1. The UI collects ticket text in [src/app.py](./src/app.py)
2. The pipeline starts in [src/pipeline.py](./src/pipeline.py)
3. LangGraph routes state through the agents in [src/graph.py](./src/graph.py)
4. Input is redacted and checked for injection
5. Ticket is classified
6. Matching KB articles are retrieved
7. A reply draft is generated
8. The draft is reviewed for policy violations
9. The system either auto-sends a safe response or escalates the case to a human
10. Final output is scrubbed and audit data is recorded

## Changes Completed During Finalization

### Windows Compatibility

The original code ran on macOS. These changes were made so it works on Windows:

- added [main.ps1](./main.ps1) as the Windows startup script
- forced UTF-8 handling for prompts, JSON files, and logs
- created `.venv`-based setup flow for Windows
- added safe temporary directory handling with `.tmp`
- made KB index rebuild optional through the launcher
- avoided eager embedding-model initialization at import time

### Hugging Face Deployment

A separate deployment bundle was created in:

- [huggingface_space_repo](./huggingface_space_repo)

This folder contains:

- `Dockerfile`
- `README.md`
- `HOW_TO_DEPLOY.md`
- copied `src/`
- copied `data/`
- copied `.streamlit/`
- copied `requirements.txt`

### Anthropic Runtime Fix

The main production issue found during deployment was model client initialization without a configured API key.

Fixes made:

- [src/utils/models.py](./src/utils/models.py)
  - validate `ANTHROPIC_API_KEY` before building the client
  - pass the API key explicitly into `ChatAnthropic`
  - prevent silent caching of an invalid client state

- [src/app.py](./src/app.py)
  - show a clear startup error if `ANTHROPIC_API_KEY` is missing

This same fix was copied into:

- [huggingface_space_repo/src/utils/models.py](./huggingface_space_repo/src/utils/models.py)
- [huggingface_space_repo/src/app.py](./huggingface_space_repo/src/app.py)

## How To Run Locally On Windows

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\main.ps1
```

If the KB index must be rebuilt:

```powershell
powershell -ExecutionPolicy Bypass -File .\main.ps1 -RebuildIndex
```

## Required Environment Variables

Defined in [.env.example](./.env.example):

- `ANTHROPIC_API_KEY` - required
- `OPENAI_API_KEY` - listed but not used in the main runtime path
- `LANGSMITH_API_KEY` - optional
- `LANGSMITH_PROJECT`
- `DRAFTER_MODEL`
- `FAST_MODEL`
- `EMBEDDING_MODEL`
- `CHROMA_PERSIST_DIR`
- `KB_ARTICLES_PATH`
- `CLASSIFIER_CONFIDENCE_THRESHOLD`
- `RETRIEVAL_SIMILARITY_THRESHOLD`
- `INJECTION_SCORE_THRESHOLD`
- `MAX_DRAFT_ITERATIONS`

## Testing Status

Current local verification:

```text
89 passed, 1 warning in 9.04s
```

Command used:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Key Deliverables In This Repo

- working Streamlit app
- LangGraph multi-agent workflow
- knowledge base and vector index
- audit logging
- Windows launcher
- Hugging Face Docker deployment bundle
- public live deployment
- automated tests

## Known Limitations

- this is a demo system, not connected to real bank systems
- logs are local/ephemeral depending on deployment target
- Hugging Face free hardware can cold-start after inactivity
- the project uses synthetic data and a curated local knowledge base

## Recommended Files To Review First

If someone needs to understand the project quickly, start with:

1. [final_project.md](./final_project.md)
2. [src/app.py](./src/app.py)
3. [src/graph.py](./src/graph.py)
4. [src/pipeline.py](./src/pipeline.py)
5. [src/state.py](./src/state.py)
6. [src/agents](./src/agents)
7. [src/utils/models.py](./src/utils/models.py)
8. [main.ps1](./main.ps1)
9. [huggingface_space_repo](./huggingface_space_repo)

## Final Conclusion

The project now has:

- a complete multi-agent banking triage workflow
- working Windows compatibility
- a live public deployment on Hugging Face Spaces
- a stable Anthropic configuration flow
- passing automated tests

This file is the final high-level handoff for the finished project.
