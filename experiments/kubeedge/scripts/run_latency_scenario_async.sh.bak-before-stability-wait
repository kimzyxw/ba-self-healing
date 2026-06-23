#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"
RUNS="$4"
BASELINE="${5:-180}"
AFTER="${6:-180}"
TIMEOUT="${7:-300}"
MAX_IN_FLIGHT="${8:-10}"

LOG=~/ba-self-healing/experiments/kubeedge/latency-tests/$SCENARIO/scenario-run.log
mkdir -p "$(dirname "$LOG")"

echo "Scenario $SCENARIO started at $(date -Is)" | tee "$LOG"
echo "delay=$DELAY duration=$DURATION runs=$RUNS baseline=$BASELINE after=$AFTER timeout=$TIMEOUT max_in_flight=$MAX_IN_FLIGHT" | tee -a "$LOG"

for i in $(seq -w 1 "$RUNS"); do
  echo "=== Starting $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"

  ~/ba-self-healing/experiments/kubeedge/scripts/run_latency_test_async.sh \
    "$SCENARIO" "$DELAY" "$DURATION" "$i" "$BASELINE" "$AFTER" "$TIMEOUT" "$MAX_IN_FLIGHT" \
    2>&1 | tee -a "$LOG"

  echo "=== Finished $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"
  sleep 60
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
