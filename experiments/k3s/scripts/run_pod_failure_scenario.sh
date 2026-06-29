#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://10.10.10.129:30080/}"
SCENARIO_DIR="${2:-experiments/k3s/pod-failure}"
RUNS="${RUNS:-10}"
RUN_PAUSE_SECONDS="${RUN_PAUSE_SECONDS:-10}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/run_pod_failure_test.sh"

mkdir -p "$SCENARIO_DIR"

LOG_FILE="$SCENARIO_DIR/scenario-run.log"

{
  echo "===== K3s Pod Failure Scenario ====="
  echo "Start: $(date -Is)"
  echo "URL: $URL"
  echo "Scenario dir: $SCENARIO_DIR"
  echo "Runs: $RUNS"
  echo "PRE_SECONDS: ${PRE_SECONDS:-30}"
  echo "POST_SECONDS: ${POST_SECONDS:-60}"
  echo "INTERVAL: ${INTERVAL:-1}"
  echo "TIMEOUT: ${TIMEOUT:-2}"
  echo
} | tee "$LOG_FILE"

for i in $(seq -w 1 "$RUNS"); do
  RUN_DIR="$SCENARIO_DIR/run-$i"

  if [ -d "$RUN_DIR" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "ERROR: $RUN_DIR already exists. Set FORCE=1 to overwrite/reuse intentionally." | tee -a "$LOG_FILE"
    exit 1
  fi

  mkdir -p "$RUN_DIR"

  {
    echo
    echo "===== RUN $i/$RUNS ====="
    echo "Run start: $(date -Is)"
    echo "Run dir: $RUN_DIR"
  } | tee -a "$LOG_FILE"

  "$TEST_SCRIPT" "$URL" "$RUN_DIR" 2>&1 | tee "$RUN_DIR/run.log"

  {
    echo "Run end: $(date -Is)"
    echo "Run $i completed."
  } | tee -a "$LOG_FILE"

  if [ "$i" != "$(seq -w 1 "$RUNS" | tail -n 1)" ]; then
    echo "Pause between runs: ${RUN_PAUSE_SECONDS}s" | tee -a "$LOG_FILE"
    sleep "$RUN_PAUSE_SECONDS"
  fi
done

{
  echo
  echo "Scenario end: $(date -Is)"
  echo "All runs completed."
} | tee -a "$LOG_FILE"
