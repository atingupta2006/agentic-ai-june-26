"""Run every ticket listed in sample_data/manifest.json.

    python scripts/batch_test.py
    python scripts/batch_test.py --include-large-log
"""
import _bootstrap  # noqa: F401

import argparse
import json
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8080"
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "sample_data" / "manifest.json"


def load_email_file(name: str) -> dict:
    path = ROOT / "sample_data" / "emails" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    paths = []
    for rel in data.get("attachments", []):
        paths.append(str((path.parent / rel).resolve().relative_to(ROOT)).replace("\\", "/"))
    return {
        "subject": data["subject"],
        "body": data.get("body", ""),
        "attachment_paths": paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-large-log", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tickets = [load_email_file(item["file"]) for item in manifest["tickets"]]
    if args.include_large_log:
        tickets.append({
            "subject": manifest["large_log_ticket"]["subject"],
            "body": manifest["large_log_ticket"]["body"],
            "attachment_paths": ["sample_data/logs/huge-app.log"],
        })

    started = time.time()
    resp = requests.post(f"{BASE}/support/batch", json={"tickets": tickets}, timeout=600)
    resp.raise_for_status()
    result = resp.json()
    elapsed = time.time() - started

    print(f"Batch finished in {elapsed:.1f}s")
    print(f"  total={result['total']} answered={result['answered']} escalated={result['escalated']}")
    for row in result["results"]:
        flag = "OK" if row["status"] in ("answered", "escalated") else "??"
        print(f"  [{flag}] {row['subject'][:50]:50} -> {row['status']} ({row.get('category','')})")
        if row.get("error"):
            print(f"       error: {row['error']}")


if __name__ == "__main__":
    main()
