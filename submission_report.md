# Wipro Submission Report

## Project

**Nimbus Bank Intelligent Support Triage System**

## Submission Links

- Public deployment: `https://huggingface.co/spaces/MrNoOne07/Nimbus-Bank-Triage`
- Public repository: `[add your GitHub repository link here]`
- Recorded walkthrough: `[optional - add video link here if used]`

## 1. System Overview

This project implements a live multi-agent system for banking customer support triage. The use case is realistic and non-trivial: a bank receives support tickets covering fraud, disputes, account access problems, and general inquiries. The system accepts a ticket, classifies it, retrieves supporting knowledge-base content, drafts a response, applies compliance review, and then either auto-responds or escalates the case to a human.

The goal of the system is not only to generate text, but to demonstrate sound multi-agent architecture, safe use of LLMs, clear separation of responsibilities, and defensible guardrails. The application is deployed publicly on Hugging Face Spaces and is also runnable locally on Windows through a dedicated PowerShell launcher.

## 2. Multi-Agent Architecture

The system uses six specialized agents connected through LangGraph and a shared state object:

- **Security Input Agent**: first entry point. It redacts PII, checks prompt injection risk, and wraps user content as untrusted input.
- **Classifier Agent**: assigns ticket category, urgency, sentiment, and confidence.
- **Retriever Agent**: searches the Chroma vector store for the most relevant knowledge-base articles.
- **Drafter Agent**: generates a customer-facing draft grounded in retrieved articles and ticket context.
- **Critic Agent**: reviews the draft against policy and determines whether it is safe to send or must be escalated.
- **Security Output Agent**: performs final output scrubbing and writes audit metadata.

Each agent has a narrow responsibility and does not directly call other agents. Coordination is handled by LangGraph in [src/graph.py](./src/graph.py) using a shared typed state from [src/state.py](./src/state.py). This makes each stage inspectable, testable, and auditable.

The workflow is primarily **sequential**, with two controlled decision points:

- after `security_in`, high injection risk short-circuits the normal flow and exits safely
- after `critic`, the workflow either exits or performs one bounded revision loop back to `drafter`

This design favors control and auditability over open-ended agent autonomy, which is appropriate for a regulated banking scenario.

## 3. Security, Safety, and Guardrails

Security is implemented as a first-class system concern rather than an afterthought.

### Input validation and prompt injection protection

- Raw ticket text is processed by the Security Input Agent before any downstream LLM call.
- Regex-based PII detection/redaction is performed in [src/utils/pii.py](./src/utils/pii.py).
- The input is checked for prompt injection using an LLM-based classifier.
- Sanitized text is wrapped in `<untrusted_user_content>` tags so downstream prompts treat it strictly as data.

### LLM guardrails and policy enforcement

- Agent behavior is constrained through dedicated system prompts in [src/prompts](./src/prompts).
- The Critic Agent blocks unsafe drafts based on policy rules such as fraud escalation, critical urgency, or unsafe response behavior.
- The Security Output Agent performs a final scrub before output leaves the system.

### Data handling

- PII is redacted before model processing and checked again before output.
- Secrets are environment-based; deployment uses Hugging Face Space secrets, especially `ANTHROPIC_API_KEY`.
- Logs are structured and written as metadata-oriented JSON in the `logs/` folder.

### Preventing unintended actions

- No agent can take external side-effect actions such as transferring funds or changing account data.
- Unsafe or uncertain cases default to escalation rather than autonomous resolution.
- The final architecture intentionally limits the highest autonomy to retrieval, while customer-facing and policy-sensitive stages are strongly gated.

## 4. Implementation Approach

### Tools and frameworks

The system is built using:

- Python
- Streamlit for the user interface
- LangGraph for orchestration
- Anthropic models through `langchain-anthropic`
- ChromaDB for vector retrieval
- Sentence Transformers for local embeddings
- Pytest for verification

The main entry points are:

- [src/app.py](./src/app.py) for the Streamlit UI
- [src/pipeline.py](./src/pipeline.py) for pipeline execution
- [src/graph.py](./src/graph.py) for agent coordination

### Agent instantiation and coordination

Agents are implemented as Python functions under [src/agents](./src/agents). LangGraph compiles them into a `StateGraph`, and the shared state is threaded through the workflow. Agents are instantiated lazily where appropriate. For example, the local embedding model is loaded lazily in the Retriever so the app can start cleanly across environments.

### Error handling, retries, and failure behavior

- Anthropic calls are wrapped with retry logic in [src/utils/models.py](./src/utils/models.py).
- Agent-level exceptions are captured and added to the shared `errors` list.
- Retrieval failure degrades safely to “no KB results” rather than crashing the workflow.
- Missing `ANTHROPIC_API_KEY` is now detected explicitly, and the UI fails with a clear configuration error instead of a low-level runtime failure.

### Environment and deployment

The original borrowed project ran on macOS. To make it work reliably on Windows, the project was updated with:

- a Windows launcher: [run_windows.ps1](./run_windows.ps1)
- explicit UTF-8 file handling
- `.venv` setup and dependency installation
- optional KB rebuild support

For public deployment, a Hugging Face Docker Space bundle was created in [huggingface_space_repo](./huggingface_space_repo). The project is now live through a public URL without requiring local `localhost` execution.

## 5. Use of AI / LLMs and Agent Collaboration

LLMs are used where reasoning or language understanding is required:

- Security Input Agent: injection classification
- Classifier Agent: ticket categorization and sentiment/urgency understanding
- Drafter Agent: grounded response generation
- Critic Agent: policy reasoning and escalation decision

The Retriever does not rely on an LLM for retrieval. It uses local sentence-transformer embeddings with ChromaDB, which reduces cost and improves determinism.

Agent collaboration is state-driven rather than conversational. Each agent contributes structured outputs into the shared state, and subsequent agents consume those outputs. This gives clear decomposition:

- classification informs retrieval and drafting
- retrieval informs drafting
- drafting informs critique
- critique determines send vs. escalate

The design trade-off is deliberate: the system is not built for maximum autonomy. It is built for safe, inspectable workflow control. In a banking support use case, bounded autonomy is preferable to agent freedom.

## 6. Evaluation and Verification

The project includes automated verification in the `tests/` directory, covering:

- security behavior
- individual agents
- graph orchestration

At the current final state, the test suite passes:

```text
89 passed, 1 warning
```

This provides basic correctness coverage for the implemented workflow and helps ensure that environment changes and deployment changes do not break core functionality.

## 7. Final Deliverable Summary

This submission includes:

- a live deployed multi-agent system
- a public codebase with project material
- a working Streamlit interface
- documented agent architecture
- implemented security and guardrails
- Windows compatibility updates
- a Hugging Face deployment path and live public endpoint

Optional supporting artifacts also exist in the repository, including:

- architecture diagram
- prompts
- deployment bundle
- PRD and internal notes

## 8. Conclusion

This project demonstrates a practical and defensible multi-agent system rather than a single chatbot. The architecture decomposes work across specialized agents, uses LangGraph for explicit coordination, and applies layered guardrails for prompt injection defense, PII handling, policy enforcement, and escalation control. The final result is a live, test-backed banking support triage system that is technically coherent, safe by design, and aligned with the assignment objectives.
