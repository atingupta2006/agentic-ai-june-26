"""End-to-end REST + OpenAPI smoke tests. Run while `python main.py` is up."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "sample_data" / "logs" / "app-db.log"

results: list[tuple[str, bool, str]] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, bool(cond), detail))
    print("PASS" if cond else "FAIL", name, detail)


def request(method: str, path: str, data: dict | None = None, headers: dict | None = None) -> tuple[int, dict | str]:
    body = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def multipart_upload(path: str, fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[int, dict]:
    import uuid

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())
    for field_name, file_path in files:
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'.encode()
        )
        lines.append(b"Content-Type: application/octet-stream\r\n\r\n")
        lines.append(file_path.read_bytes())
        lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_docs() -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        req = urllib.request.Request(f"{BASE}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            ok(f"GET {path}", resp.status == 200, str(resp.status))


def test_openapi_schema() -> None:
    _, schema = request("GET", "/openapi.json")
    paths = schema.get("paths", {})
    ok("openapi paths", set(paths) >= {
        "/health",
        "/support",
        "/support/upload",
        "/support/batch",
        "/admin/rebuild-kb",
        "/admin/samples",
    }, str(sorted(paths)))
    ok("openapi servers", bool(schema.get("servers")), str(schema.get("servers")))
    support_post = paths["/support"]["post"]
    ok("openapi support summary", support_post.get("summary") == "Process ticket (JSON)")
    ok("openapi support requestBody", "requestBody" in support_post)


def test_health() -> None:
    code, data = request("GET", "/health")
    ok("health status code", code == 200, str(code))
    ok("health body", data.get("status") == "ok" and data.get("model"), str(data.get("model")))


def test_samples() -> None:
    code, data = request("GET", "/admin/samples")
    ok("samples status", code == 200, str(code))
    ok("samples emails", len(data.get("emails", [])) >= 3, str(len(data.get("emails", []))))
    ok("samples logs", len(data.get("logs", [])) >= 1, str(len(data.get("logs", []))))


def test_support_json() -> None:
    code, data = request(
        "POST",
        "/support",
        {
            "subject": "Printer on floor 3 is making a weird noise",
            "body": "It beeps twice then stops. Not related to our servers.",
        },
    )
    ok("support json code", code == 200, str(code))
    ok("support json escalated", data.get("status") == "escalated", data.get("status", ""))


def test_support_upload() -> None:
    assert LOG_FILE.is_file(), f"Missing {LOG_FILE}"
    code, data = multipart_upload(
        "/support/upload",
        {
            "subject": "Production app keeps returning 500 errors",
            "body": "Worse under load since 9am. Log attached.",
        },
        [("files", LOG_FILE)],
    )
    ok("upload code", code == 200, str(code))
    ok("upload answered", data.get("status") == "answered", data.get("status", ""))
    ok("upload references", len(data.get("references", [])) >= 1, str(data.get("references")))


def test_support_batch() -> None:
    code, data = request(
        "POST",
        "/support/batch",
        {
            "tickets": [
                {
                    "subject": "Production app keeps returning 500 errors",
                    "body": "Batch test with log",
                    "attachment_paths": ["sample_data/logs/app-db.log"],
                },
                {
                    "subject": "Printer on floor 3 beeps",
                    "body": "Should escalate",
                    "attachment_paths": [],
                },
            ]
        },
    )
    ok("batch code", code == 200, str(code))
    ok("batch total", data.get("total") == 2, str(data.get("total")))
    ok("batch answered+escalated", data.get("answered", 0) + data.get("escalated", 0) == 2, str(data))


def test_rebuild_kb() -> None:
    code, data = request("POST", "/admin/rebuild-kb")
    ok("rebuild code", code == 200, str(code))
    ok("rebuild chunks", int(data.get("indexed_chunks", 0)) > 0, str(data.get("indexed_chunks")))


def main() -> int:
    print(f"Testing API at {BASE}\n")
    if not LOG_FILE.is_file():
        print("ERROR: sample log missing:", LOG_FILE)
        return 1
    try:
        test_docs()
        test_openapi_schema()
        test_health()
        test_samples()
        test_support_json()
        test_support_upload()
        test_support_batch()
        test_rebuild_kb()
    except urllib.error.URLError as exc:
        print("ERROR: cannot reach server — start with `python main.py` first:", exc)
        return 1

    passed = sum(1 for _, p, _ in results if p)
    print(f"\nSUMMARY: {passed}/{len(results)} passed")
    if passed != len(results):
        for name, p, detail in results:
            if not p:
                print(" -", name, detail)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
