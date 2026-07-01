# Run guide — Email L1 Support Agent

Follow this document from top to bottom the first time you set up the project.
After that, use the quick reference in section 8.

All API calls are **REST over HTTP**. Examples use **curl from Git Bash** on Windows
(same commands work on macOS/Linux).

---

## 1. What you are running

A FastAPI service that accepts a support email (and optional attachments), runs a
LangGraph pipeline, and returns either a grounded reply or an escalation to a human.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EMAIL L1 SUPPORT — request flow                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  curl /support or /support/upload
              │
              ▼
  ┌───────────────────────┐
  │  FastAPI (server.py)  │  REST + Swagger UI at /docs
  └───────────┬───────────┘
              │ graph.invoke(state)
              ▼
  ┌───────────────────────┐
  │  ingest               │  attachments → log text / screenshot text
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  triage               │  category, severity, summary (+ MCP ticket lookup)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  log_analysis         │  format-aware chunking + log embeddings + LLM
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐     ┌─────────────────┐
  │  retrieve_kb          │────►│ Chroma (on disk) │  KB chunks, small embedder
  └───────────┬───────────┘     └─────────────────┘
              ▼
  ┌───────────────────────┐
  │  web_compare          │  SerpAPI (if SERPAPI_API_KEY set)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  draft_response       │  prompts from config/prompts.yaml
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  guardrails           │  guardrails-ai validators (policy, refs, grounding)
  └───────────┬───────────┘
         proceed │ escalate
              ▼       ▼
         finalize   escalate
              │       │
              └───┬───┘
                  ▼
            JSON response
```

**Config files (no code changes needed for most tuning):**

| File | Purpose |
|------|---------|
| `config/app.yaml` | models, chunk sizes, thresholds, log format rules |
| `config/prompts.yaml` | every LLM prompt (triage, log analysis, draft, grounding, vision) |
| `config/graph.yaml` | pipeline order and routing |
| `config/logging.yaml` | log format for the server process |

---

## 2. One-time setup

| Step | When | Command |
|------|------|---------|
| Install Python 3.11 | Once per machine | `python --version` |
| Create API keys file | Once | Create `~/dev.env` (see below) |
| Install dependencies + build KB | Once per clone (or after `git pull` that changes `requirements.txt`) | `bash scripts/setup.sh` or `.\scripts\setup.ps1` |

**`~/dev.env`** (Windows: `C:\Users\<you>\dev.env`):

```
OPENAI_API_KEY=sk-...
SERPAPI_API_KEY=...    # optional but needed for web_compare
```

---

## 3. Recurring / as-needed tasks

| Task | When to run | How |
|------|-------------|-----|
| **Start the API** | Every lab session | `python main.py` (see section 4) |
| **Rebuild KB index** | After adding/editing files in `knowledge_base/` | `curl -X POST http://127.0.0.1:8080/admin/rebuild-kb` or `python scripts/build_kb.py` |
| **Guardrails Hub (optional)** | Once per machine, if you enable Hub PII in `config/app.yaml` | `guardrails configure` then `guardrails hub install hub://guardrails/detect_pii` |
| **Regenerate large logs** | Before testing heavy-log scenarios (optional) | `python scripts/generate_large_log.py 30000` |
| **Restart server** | After editing any `config/*.yaml` file | Stop `main.py`, start again |

The vector store lives in `storage/chroma/` (gitignored). It is **not** updated
automatically when you change `knowledge_base/` — you must rebuild.

---

## 4. Start the server

```bash
cd email-l1-support
source .venv/bin/activate          # Git Bash on Windows: source .venv/Scripts/activate
python main.py
```

Confirm:

- Health: http://127.0.0.1:8080/health
- **Swagger UI**: http://127.0.0.1:8080/docs — try endpoints from the browser

Leave this terminal open.

---

## 5. curl examples (Git Bash)

Base URL: `http://127.0.0.1:8080`

### Health check

```bash
curl -s http://127.0.0.1:8080/health | python -m json.tool
```

### JSON ticket (no attachment)

```bash
curl -s -X POST http://127.0.0.1:8080/support \
  -H 'Content-Type: application/json' \
  -d '{"subject":"App returns 500 errors","body":"Started at 9am, worse under load."}' \
  | python -m json.tool
```

### Single log attachment

```bash
curl -s -X POST http://127.0.0.1:8080/support/upload \
  -F 'subject=Production 500 errors' \
  -F 'body=Application log attached.' \
  -F 'files=@sample_data/logs/app-db.log' \
  | python -m json.tool
```

### Multiple attachments (log + CSV + JSON)

```bash
curl -s -X POST http://127.0.0.1:8080/support/upload \
  -F 'subject=DB pool timeouts' \
  -F 'body=Several exports attached.' \
  -F 'files=@sample_data/logs/app-db.log' \
  -F 'files=@sample_data/logs/errors.csv' \
  -F 'files=@sample_data/logs/errors.json' \
  | python -m json.tool
```

### Apache + nginx logs

```bash
curl -s -X POST http://127.0.0.1:8080/support/upload \
  -F 'subject=502 from load balancer' \
  -F 'body=Front-end error logs attached.' \
  -F 'files=@sample_data/logs/apache-error.log' \
  -F 'files=@sample_data/logs/nginx-error.log' \
  | python -m json.tool
```

### Screenshot (vision model reads visible text)

```bash
curl -s -X POST http://127.0.0.1:8080/support/upload \
  -F 'subject=Error on login screen' \
  -F 'body=Screenshot attached.' \
  -F 'files=@path/to/screenshot.png' \
  | python -m json.tool
```

### Policy escalation (no auto-reply)

```bash
curl -s -X POST http://127.0.0.1:8080/support \
  -H 'Content-Type: application/json' \
  -d '{"subject":"Suspected data loss","body":"Customer records may be missing after migration."}' \
  | python -m json.tool
```

Expect `"status": "escalated"`.

### Rebuild knowledge base

```bash
curl -s -X POST http://127.0.0.1:8080/admin/rebuild-kb | python -m json.tool
```

### List bundled samples

```bash
curl -s http://127.0.0.1:8080/admin/samples | python -m json.tool
```

### Batch API (several tickets in one request)

```bash
curl -s -X POST http://127.0.0.1:8080/support/batch \
  -H 'Content-Type: application/json' \
  -d '{
    "tickets": [
      {
        "subject": "Production 500 errors",
        "body": "Log attached.",
        "attachment_paths": ["sample_data/logs/app-db.log"]
      },
      {
        "subject": "Printer noise",
        "body": "Out of scope test.",
        "attachment_paths": []
      }
    ]
  }' | python -m json.tool
```

---

## 6. Helper scripts (optional)

From a **second** terminal (server still running):

```bash
# One ticket from sample_data/emails/*.json
python scripts/run_email.py sample_data/emails/email-db-issue.json

# All tickets in sample_data/manifest.json via /support/batch
python scripts/batch_test.py

# Include huge-app.log (generate first if missing)
python scripts/generate_large_log.py 25000
python scripts/batch_test.py --include-large-log
```

---

## 7. Sample data

**Emails:** `sample_data/emails/` — JSON files with `subject`, `body`, `attachments`.

**Logs:**

| File | Format |
|------|--------|
| `app-db.log`, `app-auth.log` | Java/Spring style |
| `apache-access.log`, `apache-error.log` | Apache |
| `nginx-access.log`, `nginx-error.log` | Nginx |
| `errors.json` | JSON array |
| `errors.csv` | CSV export |
| `huge-app.log` | Generated Spring log (~20k+ lines) |

**Generate more heavy logs:**

```bash
python scripts/generate_large_log.py 40000 --format spring
python scripts/generate_large_log.py 20000 --format apache-access
python scripts/generate_large_log.py 20000 --format nginx-error
```

When the filtered log exceeds `logs.large_log_threshold_chars` in `config/app.yaml`,
the response includes `"log_was_large": true`.

---

## 8. Reading the response

| Field | Meaning |
|-------|---------|
| `status` | `answered` or `escalated` |
| `answer` | Reply text (or escalation message) |
| `category` / `severity` | From triage |
| `references` | KB ids used |
| `grounding_score` | 0–1, from guardrails |
| `log_was_large` | Whether chunked log RAG ran |
| `log_format` | Detected log type (e.g. `java_spring`, `nginx_error`) |
| `trace` | Short log of pipeline steps |

---

## 9. Attachment and log handling (under the hood)

- **Attachments:** `.log`, `.txt`, `.json`, `.csv`, `.pdf`, images — see `app/utils/attachments.py`
- **Log formats:** detected in `app/utils/log_formats.py` (Apache, Nginx, JSON, CSV, Spring, generic)
- **Chunking:** per-format rules in `config/app.yaml` → `logs.formats`
- **Embeddings:** KB uses `text-embedding-3-small`; log chunks use `text-embedding-3-large`
- **Prompts:** loaded from `config/prompts.yaml` via `settings.prompt(...)`
- **Guardrails:** [`guardrails-ai`](https://github.com/guardrails-ai/guardrails) in `app/guardrails_engine.py` — custom validators for policy keywords, minimum references, and grounding (grounding prompt still in `prompts.yaml`). Optional Hub PII: set `guardrails.hub_pii_enabled: true` after `guardrails configure`.

---

## 10. Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection refused on curl | Start `python main.py` first |
| `OPENAI_API_KEY` missing | Add to `~/dev.env`, restart server |
| No web references | Add `SERPAPI_API_KEY` to `~/dev.env` |
| Empty KB matches | Run rebuild-kb (section 3) |
| Upload 413 | File larger than `server.max_upload_mb` in `config/app.yaml` |
| curl path errors on Windows | Run curl from Git Bash inside the project folder; use forward slashes in JSON paths for `/support/batch` |

---

## 11. Project layout

```
email-l1-support/
├── RUN.md                 ← this file
├── main.py                ← starts uvicorn
├── config/                ← app.yaml, prompts.yaml, graph.yaml
├── app/
│   ├── server.py          ← REST API + Swagger
│   ├── nodes/             ← pipeline steps
│   ├── rag/               ← Chroma KB + ephemeral log index
│   └── utils/             ← attachments, log formats, log parser
├── knowledge_base/        ← source articles (rebuild index after edits)
├── sample_data/           ← test emails, logs, manifest.json
├── scripts/               ← setup, build_kb, run_email, batch_test, generate_large_log
└── storage/chroma/        ← built index (gitignored)
```

Swagger UI at **/docs** remains the easiest way to explore request/response schemas.
