"""Generate large sample log files for load testing.

Examples:
    python scripts/generate_large_log.py
    python scripts/generate_large_log.py 50000
    python scripts/generate_large_log.py 30000 --format spring
    python scripts/generate_large_log.py 15000 --format apache-access
    python scripts/generate_large_log.py 15000 --format nginx-error
"""
import _bootstrap  # noqa: F401

import argparse
import random
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "sample_data" / "logs"

SPRING_NOISE = [
    "INFO  [http-nio-8080-exec-{w}] checkout.OrderController - Received order id={n}",
    "INFO  [http-nio-8080-exec-{w}] db.HikariPool - Pool stats (total=10, active={a}, idle={i})",
    "DEBUG [http-nio-8080-exec-{w}] cache.RedisClient - GET session:{n} hit",
]
SPRING_ERRORS = [
    "ERROR [http-nio-8080-exec-{w}] db.HikariPool - Connection is not available, request timed out after 30000ms",
    "ERROR [http-nio-8080-exec-{w}] org.postgresql.util.PSQLException - FATAL: sorry, too many clients already",
    "ERROR [http-nio-8080-exec-{w}] checkout.OrderController - Failed to process order {n} (HTTP 500)",
]

APACHE_ACCESS = (
    '10.0.{o}.{h} - - [{ts}] "POST /api/checkout HTTP/1.1" {code} {size} "-" "Mozilla/5.0"'
)
APACHE_ERROR = (
    "[{ts}] [proxy_http:error] [pid {pid}:tid {tid}] AH01102: error reading status line from remote server"
)
NGINX_ERROR = (
    "{d}/{m}/{y} {hh}:{mm}:{ss} [error] {pid}#{pid}: *{n} upstream timed out while reading response header"
)


def write_spring(path: Path, total: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for line_no in range(total):
            w = random.randint(1, 12)
            n = random.randint(1000, 99999)
            ts = f"2026-06-30 09:{(line_no // 60) % 60:02d}:{line_no % 60:02d}"
            tmpl = random.choice(SPRING_ERRORS if random.random() < 0.0025 else SPRING_NOISE)
            fh.write(f"{ts} " + tmpl.format(w=w, n=n, a=random.randint(0, 10), i=random.randint(0, 10)) + "\n")


def write_apache_access(path: Path, total: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for line_no in range(total):
            code = random.choice([200, 200, 200, 500, 502, 504])
            ts = f"30/Jun/2026:09:{(line_no // 60) % 60:02d}:{line_no % 60:02d} +0000"
            fh.write(APACHE_ACCESS.format(
                o=random.randint(1, 4), h=random.randint(10, 250),
                ts=ts, code=code, size=random.randint(0, 256),
            ) + "\n")


def write_apache_error(path: Path, total: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for line_no in range(total):
            if random.random() < 0.003:
                ts = f"Mon Jun 30 09:{(line_no // 60) % 60:02d}:{line_no % 60:02d}.000000 2026"
                fh.write(APACHE_ERROR.format(ts=ts, pid=1800 + line_no % 50, tid=140234567890) + "\n")


def write_nginx_error(path: Path, total: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for line_no in range(total):
            if random.random() < 0.003:
                fh.write(NGINX_ERROR.format(
                    d="30/06", m="06", y="2026",
                    hh=9, mm=(line_no // 60) % 60, ss=line_no % 60,
                    pid=2900 + line_no % 20, n=8000 + line_no,
                ) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lines", nargs="?", type=int, default=20000)
    parser.add_argument(
        "--format",
        choices=["spring", "apache-access", "apache-error", "nginx-error"],
        default="spring",
    )
    args = parser.parse_args()

    writers = {
        "spring": ("huge-app.log", write_spring),
        "apache-access": ("huge-apache-access.log", write_apache_access),
        "apache-error": ("huge-apache-error.log", write_apache_error),
        "nginx-error": ("huge-nginx-error.log", write_nginx_error),
    }
    name, writer = writers[args.format]
    out = OUT_DIR / name
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    writer(out, args.lines)
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"Wrote {args.lines} lines ({size_mb:.2f} MB) to {out}")


if __name__ == "__main__":
    main()
