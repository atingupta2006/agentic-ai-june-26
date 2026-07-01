# Email L1 Support Agent — project overview

This lab closes Day 4 by showing what a **production-style** L1 support agent looks like.
You will **not** build the full project in this notebook folder — read this overview first.
When you confirm this is the kind of system you need, your trainer will share the complete
`email-l1-support` project separately.

---

## What the project does

A customer sends a support email (optionally with log files, screenshots, or other attachments).
A backend service:

1. Parses and classifies the ticket.
2. Analyses attached logs (including very large files).
3. Retrieves relevant knowledge-base articles.
4. Optionally compares findings with public web results.
5. Drafts a reply grounded in evidence.
6. Runs **output guardrails** before sending.
7. Returns either an **auto-reply** or an **escalation** to a human specialist.

The same pipeline is exposed as a **REST API** (with Swagger UI) so other systems — or curl —
can submit tickets without a notebook.

---

## Concepts you will practice in earlier Day 4 labs

| Concept | Where you saw it | How it appears here |
|---------|------------------|---------------------|
| **RAG** | Chroma notebook | KB articles indexed in Chroma; top matches retrieved per ticket |
| **Embeddings** | Chroma notebook | Two embedders: small model for docs, large model for noisy log text |
| **Chunking** | Chroma + Smart Email (Day 3) | KB chunks + log chunks so large files never hit the LLM in full |
| **LangGraph** | Day 3 notebooks | Stateful graph of nodes with conditional routing (proceed vs escalate) |
| **MCP** | MCP basics notebook | Triage calls an MCP tool to look up open incident status |
| **Guardrails** | Day 5 guardrails lab | `guardrails-ai` validators on the draft (policy, references, grounding) |

---

## Architecture at a glance

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EMAIL L1 SUPPORT — request flow                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Client (curl, Swagger UI, or another app)
              │
              ▼
  ┌───────────────────────┐
  │  FastAPI (REST API)   │  /support, /support/upload, /support/batch
  └───────────┬───────────┘
              │ graph.invoke(state)
              ▼
  ┌───────────────────────┐
  │  ingest               │  subject/body + attachments → log text, screenshot text
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  triage               │  category, severity, summary + MCP ticket lookup
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  log_analysis         │  format-aware parsing, chunking, log embeddings, LLM
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐     ┌─────────────────┐
  │  retrieve_kb          │────►│ Chroma (on disk) │  KB RAG, small embedder
  └───────────┬───────────┘     └─────────────────┘
              ▼
  ┌───────────────────────┐
  │  web_compare          │  SerpAPI (optional, needs SERPAPI_API_KEY)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  draft_response       │  prompts from config/prompts.yaml
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  guardrails           │  guardrails-ai: policy, min references, grounding score
  └───────────┬───────────┘
         proceed │ escalate
              ▼       ▼
         finalize   escalate
              │       │
              └───┬───┘
                  ▼
            JSON response (answer or escalation message)
```

**Routing rule:** if guardrails pass (grounded enough, KB references present, no policy
violations), the graph goes to **finalize**; otherwise **escalate**.

---

## Frameworks and libraries

| Layer | Technology | Role |
|-------|------------|------|
| **Orchestration** | LangGraph | `StateGraph` with YAML-driven node wiring (`config/graph.yaml`) |
| **LLM** | LangChain + OpenAI | Chat completions, JSON-mode prompts, vision for screenshots |
| **API** | FastAPI + Uvicorn | REST endpoints, multipart uploads, OpenAPI/Swagger at `/docs` |
| **Vector DB** | Chroma + langchain-chroma | Persistent KB index under `storage/chroma/` |
| **Embeddings** | OpenAI | `text-embedding-3-small` (KB), `text-embedding-3-large` (logs) |
| **Web search** | google-search-results (SerpAPI) | Compare KB findings with public snippets |
| **Tools** | MCP (Model Context Protocol) | Stdio MCP server for ticket/incident lookup during triage |
| **Guardrails** | guardrails-ai | Custom validators + optional Hub PII detector |
| **Config** | PyYAML, pydantic-settings | `app.yaml`, `prompts.yaml`, `graph.yaml` — tune without code changes |
| **Logs / files** | pypdf, custom parsers | Apache, Nginx, JSON, CSV, Spring-style log formats |

---

## What you configure (not hard-code)

| File | Purpose |
|------|---------|
| `config/app.yaml` | Models, chunk sizes, log thresholds, guardrail thresholds, MCP settings |
| `config/prompts.yaml` | Every LLM prompt (triage, log analysis, draft, grounding audit) |
| `config/graph.yaml` | Pipeline order and conditional edges |
| `~/dev.env` | `OPENAI_API_KEY`, optional `SERPAPI_API_KEY`, optional `GUARDRAILS_API_KEY` |

---

## API surface (when you receive the project)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI — try requests in the browser |
| POST | `/support` | JSON ticket |
| POST | `/support/upload` | Multipart email + attachments |
| POST | `/support/batch` | Several tickets in one call |
| GET | `/admin/samples` | List bundled sample emails and logs |
| POST | `/admin/rebuild-kb` | Re-index `knowledge_base/` into Chroma |

---

## Sample scenarios the project includes

- **Database / pool exhaustion** — large `.log` attachment, KB match, grounded auto-reply.
- **Auth / token issues** — MCP incident lookup, runbook steps.
- **Non-IT request** (e.g. printer) — escalated without inventing a fix.
- **Multi-attachment tickets** — several log formats in one email.
- **Batch testing** — run many sample tickets and compare outcomes.

---

## How this fits your learning path

```
Day 3  LangChain agents → LangGraph workflows → AI judge → Smart email agent
Day 4  Chroma RAG → MCP tools → (this overview) → full project when assigned
Day 5  guardrails-ai in depth → extended Smart Email lab
```

Earlier labs teach each building block in isolation. The **Email L1 Support Agent** combines
them into one deployable service: ingest → classify → analyse → retrieve → draft → validate →
reply or escalate.

---

## Next step

If this matches what you need for your team or capstone:

1. Tell your trainer you want the **Email L1 Support Agent** project.
2. You will receive the `email-l1-support` folder with `RUN.md` (setup, curl, Swagger).
3. Use Day 4 labs as reference when you read the code — you have already used the same
   libraries and patterns.
