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

LOG=~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO/scenario-run.log
mkdir -p "$(dirname "$LOG")"

echo "Scenario $SCENARIO started at $(date -Is)" | tee "$LOG"

for i in $(seq -w 1 "$RUNS"); do
  echo "=== Starting $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"

  ~/ba-self-healing/experiments/k3s/scripts/run_packet_loss_test_async.sh \
    "$SCENARIO" "$LOSS" "$DURATION" "$i" "$BASELINE" "$AFTER" "$TIMEOUT" "$MAX_IN_FLIGHT" \
    2>&1 | tee -a "$LOG"

  echo "=== Finished $SCENARIO run-$i at $(date -Is) ===" | tee -a "$LOG"
  sleep 60
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
