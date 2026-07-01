# Email L1 Support Agent

LangGraph pipeline behind a FastAPI REST API. Ingests emails and attachments,
analyses logs (including large and multi-format files), retrieves KB articles
from Chroma, optionally searches the web, validates drafts with **guardrails-ai**,
and returns a grounded answer or escalates.

**Start here:** [RUN.md](RUN.md) — setup, curl commands (Git Bash), Swagger,
batch testing, and when to rebuild the vector index.

## Quick start

```bash
bash scripts/setup.sh          # or .\scripts\setup.ps1
source .venv/Scripts/activate  # Git Bash on Windows
python main.py
```

Open http://127.0.0.1:8080/docs for Swagger.

```bash
curl -s http://127.0.0.1:8080/health
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + config summary |
| GET | `/docs` | Swagger UI |
| POST | `/support` | JSON ticket |
| POST | `/support/upload` | Multipart + files |
| POST | `/support/batch` | Several tickets (server reads attachment paths) |
| GET | `/admin/samples` | List sample emails/logs |
| POST | `/admin/rebuild-kb` | Re-index `knowledge_base/` |

## Configuration

| File | Controls |
|------|----------|
| `config/app.yaml` | models, chunking, log formats, thresholds |
| `config/prompts.yaml` | all LLM prompts |
| `config/graph.yaml` | pipeline flow |
| `~/dev.env` | `OPENAI_API_KEY`, `SERPAPI_API_KEY`, optional `GUARDRAILS_API_KEY` (Hub) |

## Layout

```
email-l1-support/
├── RUN.md
├── main.py
├── config/
├── app/              # server, nodes, rag, utils
├── knowledge_base/
├── sample_data/
└── scripts/
```

See [STUDENT_GUIDE.md](STUDENT_GUIDE.md) for a shorter checklist version.
