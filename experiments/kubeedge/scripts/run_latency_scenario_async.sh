#!/usr/bin/env bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"
RUNS="$4"
BASELINE="${5:-180}"
AFTER="${6:-180}"
TIMEOUT="${7:-300}"
MAX_IN_FLIGHT="${8:-10}"
START_RUN="${9:-01}"

BASE_DIR="experiments/kubeedge/latency-tests/${SCENARIO}"
LOG="${BASE_DIR}/scenario-run.log"
URL="${URL:-http://10.10.20.131:30080/}"
STABLE_CHECKS="${STABLE_CHECKS:-5}"
STABLE_SLEEP_SECONDS="${STABLE_SLEEP_SECONDS:-30}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-300}"

mkdir -p "$BASE_DIR"

wait_for_nodeport_stable() {
  local consecutive_ok=0
  local code
  local now

  echo "Waiting for stable NodePort before next run at $(date -Iseconds)"
  echo "url=${URL}"
  echo "stable_checks=${STABLE_CHECKS}"
  echo "stable_sleep_seconds=${STABLE_SLEEP_SECONDS}"

  while true; do
    code="$(curl -m 5 -s -o /dev/null -w "%{http_code}" "$URL" || true)"
    now="$(date -Iseconds)"

    echo "[$now] nodeport_code=${code} consecutive_ok=${consecutive_ok}"

    if [ "$code" = "200" ]; then
      consecutive_ok=$((consecutive_ok + 1))
    else
      consecutive_ok=0
    fi

    if [ "$consecutive_ok" -ge "$STABLE_CHECKS" ]; then
      echo "NodePort stable at $(date -Iseconds)"
      break
    fi

    sleep "$STABLE_SLEEP_SECONDS"
  done
}

{
  echo "Scenario ${SCENARIO} started at $(date -Iseconds)"
  echo "delay=${DELAY}"
  echo "duration=${DURATION}"
  echo "runs=${RUNS}"
  echo "baseline=${BASELINE}"
  echo "after=${AFTER}"
  echo "timeout=${TIMEOUT}"
  echo "max_in_flight=${MAX_IN_FLIGHT}"
  echo "start_run=${START_RUN}"
  echo "router_ifaces=${ROUTER_IFACES:-unset}"
  echo "url=${URL}"

  for i in $(seq -w "$START_RUN" "$RUNS"); do
    echo "=== Preparing ${SCENARIO} run-${i} at $(date -Iseconds) ==="

    wait_for_nodeport_stable

    echo "=== Starting ${SCENARIO} run-${i} at $(date -Iseconds) ==="

    ROUTER_IFACES="${ROUTER_IFACES:-ens161}" \
    URL="$URL" \
    ./experiments/kubeedge/scripts/run_latency_test_async.sh \
      "$SCENARIO" "$DELAY" "$DURATION" "$i" "$BASELINE" "$AFTER" "$TIMEOUT" "$MAX_IN_FLIGHT"

    rc=$?
    echo "=== Finished ${SCENARIO} run-${i} at $(date -Iseconds), rc=${rc} ==="

    if [ "$rc" -ne 0 ]; then
      echo "ERROR: ${SCENARIO} run-${i} failed with rc=${rc}. Stopping scenario."
      exit "$rc"
    fi

    if [ "$i" != "$(printf "%02d" "$RUNS")" ]; then
      echo "Cooling down for ${COOLDOWN_SECONDS}s after run-${i}"
      sleep "$COOLDOWN_SECONDS"
    fi
  done

  echo "Scenario ${SCENARIO} finished at $(date -Iseconds)"
} 2>&1 | tee -a "$LOG"
