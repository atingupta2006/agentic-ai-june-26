"""Send one sample email JSON file to the running API.

Usage (server must be running on 127.0.0.1:8080):
    python scripts/run_email.py sample_data/emails/email-db-issue.json
"""
import _bootstrap  # noqa: F401

import json
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8080"


def load_ticket(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    attachments = []
    for rel in data.get("attachments", []):
        file_path = (base / rel).resolve()
        attachments.append({
            "filename": file_path.name,
            "bytes": file_path.read_bytes(),
            "mime": "",
        })
    return {
        "subject": data["subject"],
        "body": data.get("body", ""),
        "attachments": attachments,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_email.py sample_data/emails/<file>.json")
        sys.exit(1)

    ticket_path = Path(sys.argv[1])
    ticket = load_ticket(ticket_path)

    if ticket["attachments"]:
        files = [
            ("files", (a["filename"], a["bytes"], "application/octet-stream"))
            for a in ticket["attachments"]
        ]
        data = {"subject": ticket["subject"], "body": ticket["body"]}
        resp = requests.post(f"{BASE}/support/upload", data=data, files=files, timeout=300)
    else:
        resp = requests.post(
            f"{BASE}/support",
            json={"subject": ticket["subject"], "body": ticket["body"]},
            timeout=300,
        )

    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    main()
