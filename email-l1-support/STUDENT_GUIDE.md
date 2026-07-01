# Student checklist

Full instructions, curl examples, and the pipeline diagram are in **[RUN.md](RUN.md)**.

## Checklist

1. Python 3.11 + `~/dev.env` with `OPENAI_API_KEY` (and `SERPAPI_API_KEY` if you want web search)
2. `bash scripts/setup.sh` or `.\scripts\setup.ps1`
3. `python main.py` → http://127.0.0.1:8080/docs
4. Send a ticket with curl (Git Bash) — copy from RUN.md section 5
5. Try `python scripts/run_email.py sample_data/emails/email-db-issue.json`
6. Try `python scripts/batch_test.py` for multiple tickets

## When to rebuild the KB

After you add or change files in `knowledge_base/`:

```bash
curl -X POST http://127.0.0.1:8080/admin/rebuild-kb
```

## Large log test

```bash
python scripts/generate_large_log.py 25000
python scripts/run_email.py sample_data/emails/email-db-issue.json
# or swap attachment in curl to sample_data/logs/huge-app.log
```

Check `"log_was_large": true` in the JSON response.
