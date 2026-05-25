#!/usr/bin/env python3

import csv
import time
import argparse
import requests
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--interval", type=float, default=1.0)
parser.add_argument("--timeout", type=float, default=2.0)
parser.add_argument("--duration", type=int, default=0)
args = parser.parse_args()

start = time.time()

with open(args.output, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "status_code", "response_time_ms", "success", "error"])

    while True:
        if args.duration > 0 and time.time() - start >= args.duration:
            break

        timestamp = now_iso()
        status_code = ""
        response_time_ms = ""
        success = False
        error = ""

        request_start = time.time()
        try:
            response = requests.get(args.url, timeout=args.timeout)
            response_time_ms = round((time.time() - request_start) * 1000, 2)
            status_code = response.status_code
            success = 200 <= response.status_code < 400
        except Exception as e:
            response_time_ms = round((time.time() - request_start) * 1000, 2)
            error = type(e).__name__

        writer.writerow([timestamp, status_code, response_time_ms, success, error])
        f.flush()

        time.sleep(args.interval)
