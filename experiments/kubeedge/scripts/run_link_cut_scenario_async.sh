#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DURATION="$2"
RUNS="${3:-10}"
BASELINE="${4:-180}"
AFTER="${5:-180}"
TIMEOUT="${6:-300}"
MAX_IN_FLIGHT="${7:-10}"
START_RUN="${8:-01}"

BASE=~/ba-self-healing/experiments/kubeedge/link-cut-tests/$SCENARIO
mkdir -p "$BASE"

LOG="$BASE/scenario-run.log"

STABLE_CHECKS="${STABLE_CHECKS:-5}"
STABLE_SLEEP_SECONDS="${STABLE_SLEEP_SECONDS:-30}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-60}"
URL="${URL:-http://10.10.20.131:30080/}"

all_nodes_ready() {
  if kubectl get nodes --no-headers | awk '{print $2}' | grep -qv '^Ready$'; then
    return 1
  fi
  return 0
}

wait_for_nodeport_stable() {
  local ok=0
  local attempt=0

  echo "[stability] Warte auf stabile NodePort-Erreichbarkeit und Ready-Nodes: $URL" | tee -a "$LOG"

  while [ "$ok" -lt "$STABLE_CHECKS" ]; do
    attempt=$((attempt + 1))
    code=$(curl -m 5 -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")

    if [ "$code" = "200" ] && all_nodes_ready; then
      ok=$((ok + 1))
      echo "[stability] Versuch $attempt: HTTP 200 und alle Nodes Ready ($ok/$STABLE_CHECKS)" | tee -a "$LOG"
    else
      ok=0
      echo "[stability] Versuch $attempt: HTTP $code oder Nodes nicht Ready, Zähler zurückgesetzt" | tee -a "$LOG"
      kubectl get nodes | tee -a "$LOG"
    fi

    if [ "$ok" -lt "$STABLE_CHECKS" ]; then
      sleep "$STABLE_SLEEP_SECONDS"
    fi
  done
}

echo "Scenario $SCENARIO started at $(date -Is)" | tee -a "$LOG"
echo "duration=$DURATION runs=$RUNS baseline=$BASELINE after=$AFTER timeout=$TIMEOUT max_in_flight=$MAX_IN_FLIGHT start_run=$START_RUN" | tee -a "$LOG"

END_RUN=$((10#$START_RUN + RUNS - 1))

for i in $(seq "$((10#$START_RUN))" "$END_RUN"); do
  RUN=$(printf "%02d" "$i")

  wait_for_nodeport_stable

  echo "=== Starting $SCENARIO run-$RUN at $(date -Is) ===" | tee -a "$LOG"

  set +e
  experiments/kubeedge/scripts/run_link_cut_test_async.sh \
    "$SCENARIO" \
    "$DURATION" \
    "$RUN" \
    "$BASELINE" \
    "$AFTER" \
    "$TIMEOUT" \
    "$MAX_IN_FLIGHT" 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  set -e

  echo "=== Finished $SCENARIO run-$RUN at $(date -Is), rc=$rc ===" | tee -a "$LOG"

  if [ "$rc" -ne 0 ]; then
    echo "Scenario $SCENARIO aborted at run-$RUN with rc=$rc" | tee -a "$LOG"
    exit "$rc"
  fi

  if [ "$i" -lt "$END_RUN" ]; then
    echo "[cooldown] Warte ${COOLDOWN_SECONDS}s vor nächstem Lauf" | tee -a "$LOG"
    sleep "$COOLDOWN_SECONDS"
  fi
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
