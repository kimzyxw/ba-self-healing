#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DURATION="$2"
RUNS="${3:-10}"
BASELINE="${4:-180}"
AFTER="${5:-180}"
TIMEOUT="${6:-300}"
MAX_IN_FLIGHT="${7:-10}"

BASE=~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO
mkdir -p "$BASE"

LOG="$BASE/scenario-run.log"

echo "Scenario $SCENARIO started at $(date -Is)" | tee -a "$LOG"

for i in $(seq 1 "$RUNS"); do
  RUN=$(printf "%02d" "$i")

  echo "=== Starting $SCENARIO run-$RUN at $(date -Is) ===" | tee -a "$LOG"

  experiments/k3s/scripts/run_link_cut_test_async.sh \
    "$SCENARIO" \
    "$DURATION" \
    "$RUN" \
    "$BASELINE" \
    "$AFTER" \
    "$TIMEOUT" \
    "$MAX_IN_FLIGHT" 2>&1 | tee -a "$LOG"

  echo "=== Finished $SCENARIO run-$RUN at $(date -Is) ===" | tee -a "$LOG"
  sleep 60
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
