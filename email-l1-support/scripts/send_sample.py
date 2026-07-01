"""Send a sample support request to the running REST API.

Start the server first (python main.py), then in another terminal:
    python scripts/send_sample.py                      # JSON, no attachment
    python scripts/send_sample.py sample_data/logs/app-db.log   # with attachment
"""
import _bootstrap  # noqa: F401

import json
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8080"


def main() -> None:
    subject = "Production app keeps returning 500 errors since this morning"
    body = "Since 9am our checkout service throws 500 errors, worse under load. Log attached."

    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
        files = {"files": (log_path.name, log_path.read_bytes(), "text/plain")}
        data = {"subject": subject, "body": body}
        resp = requests.post(f"{BASE}/support/upload", data=data, files=files, timeout=120)
    else:
        resp = requests.post(
            f"{BASE}/support",
            json={"subject": subject, "body": body},
            timeout=120,
        )

    resp.raise_for_status()
    result = resp.json()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
