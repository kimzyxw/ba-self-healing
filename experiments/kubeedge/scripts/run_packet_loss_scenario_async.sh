#!/bin/bash
set -euo pipefail

SCENARIO="$1"
LOSS="$2"
DURATION="$3"
RUNS="$4"
BASELINE="${5:-180}"
AFTER="${6:-180}"
TIMEOUT="${7:-300}"
MAX_IN_FLIGHT="${8:-10}"
START_RUN="${9:-01}"

BASE_DIR="experiments/kubeedge/packet-loss-tests/${SCENARIO}"
LOG="${BASE_DIR}/scenario-run.log"

URL="${URL:-http://10.10.20.131:30080/}"
STABLE_CHECKS="${STABLE_CHECKS:-5}"
STABLE_SLEEP_SECONDS="${STABLE_SLEEP_SECONDS:-30}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-60}"

mkdir -p "$BASE_DIR"

wait_for_nodeport_stable() {
  local ok=0
  local attempt=0

  echo "Waiting for NodePort stability at $(date -Is)" | tee -a "$LOG"

  while true; do
    attempt=$((attempt + 1))

    if curl -m 5 -s -o /dev/null -w "%{http_code}" "$URL" | grep -q "^200$"; then
      ok=$((ok + 1))
      echo "  attempt=$attempt ok=$ok/$STABLE_CHECKS" | tee -a "$LOG"
    else
      ok=0
      echo "  attempt=$attempt failed; reset ok counter" | tee -a "$LOG"
    fi

    if [ "$ok" -ge "$STABLE_CHECKS" ]; then
      echo "NodePort stable at $(date -Is)" | tee -a "$LOG"
      return 0
    fi

    sleep "$STABLE_SLEEP_SECONDS"
  done
}

echo "Scenario $SCENARIO started at $(date -Is)" | tee "$LOG"
echo "loss=$LOSS duration=$DURATION runs=$RUNS baseline=$BASELINE after=$AFTER timeout=$TIMEOUT max_in_flight=$MAX_IN_FLIGHT start_run=$START_RUN" | tee -a "$LOG"

for i in $(seq -w "$START_RUN" "$RUNS"); do
  echo "=== Preparing $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"

  wait_for_nodeport_stable

  echo "=== Starting $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"

  set +e
  ~/ba-self-healing/experiments/kubeedge/scripts/run_packet_loss_test_async.sh \
    "$SCENARIO" "$LOSS" "$DURATION" "$i" "$BASELINE" "$AFTER" "$TIMEOUT" "$MAX_IN_FLIGHT" \
    2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  set -e

  echo "=== Finished $SCENARIO run-$i at $(date -Is), rc=$rc ===" | tee -a "$LOG"

  if [ "$rc" -ne 0 ]; then
    echo "ERROR: run-$i failed with rc=$rc. Stop scenario." | tee -a "$LOG"
    exit "$rc"
  fi

  if [ "$i" != "$(printf "%02d" "$RUNS")" ]; then
    echo "Cooldown ${COOLDOWN_SECONDS}s before next run" | tee -a "$LOG"
    sleep "$COOLDOWN_SECONDS"
  fi
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
