#!/usr/bin/env python3
import argparse
import csv
from datetime import datetime, timezone
import requests
import time

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--interval", type=float, default=1.0)
parser.add_argument("--timeout", type=float, default=180.0)
args = parser.parse_args()

with open(args.output, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "request_start_time",
        "request_end_time",
        "status_code",
        "duration_ms",
        "success",
        "error"
    ])
    f.flush()

    while True:
        start = datetime.now(timezone.utc)
        status_code = ""
        success = False
        error = ""

        try:
            response = requests.get(args.url, timeout=args.timeout)
            status_code = response.status_code
            success = response.ok
        except Exception as e:
            error = type(e).__name__

        end = datetime.now(timezone.utc)
        duration_ms = (end - start).total_seconds() * 1000

        writer.writerow([
            start.isoformat(),
            end.isoformat(),
            status_code,
            round(duration_ms, 2),
            success,
            error
        ])
        f.flush()

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        sleep_time = max(0, args.interval - elapsed)
        time.sleep(sleep_time)
