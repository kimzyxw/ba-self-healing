#!/usr/bin/env python3
import argparse
import asyncio
import csv
from datetime import datetime, timezone
import aiohttp

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--interval", type=float, default=1.0)
parser.add_argument("--timeout", type=float, default=180.0)
parser.add_argument("--duration", type=float, required=True)
parser.add_argument("--max-in-flight", type=int, default=10)
args = parser.parse_args()


def now():
    return datetime.now(timezone.utc)


async def fetch(session, writer, f, request_id):
    start = now()
    status_code = ""
    success = False
    error = ""

    try:
        async with session.get(args.url) as response:
            status_code = response.status
            await response.read()
            success = 200 <= response.status < 400
    except Exception as e:
        error = type(e).__name__

    end = now()
    duration_ms = (end - start).total_seconds() * 1000

    writer.writerow([
        request_id,
        start.isoformat(),
        end.isoformat(),
        status_code,
        round(duration_ms, 2),
        success,
        error
    ])
    f.flush()

async def main():
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    active_tasks = set()

    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "request_id",
            "request_start_time",
            "request_end_time",
            "status_code",
            "duration_ms",
            "success",
            "error"
        ])
        f.flush()

        async with aiohttp.ClientSession(timeout=timeout) as session:
            start_time = now()
            request_id = 0

            while (now() - start_time).total_seconds() < args.duration:
                while len(active_tasks) >= args.max_in_flight:
                    done, active_tasks = await asyncio.wait(
                        active_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                request_id += 1
                task = asyncio.create_task(
                    fetch(session, writer, f, request_id)
                )
                active_tasks.add(task)

                await asyncio.sleep(args.interval)

            if active_tasks:
                await asyncio.gather(*active_tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
