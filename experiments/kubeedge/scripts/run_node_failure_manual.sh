#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <role> <node> <monitor_url> <run_dir>"
  echo "Example edge:  $0 edge e1 http://10.10.20.132:30080/ experiments/kubeedge/node-failure/edge/run-01-e1"
  echo "Example cloud: $0 cloud c2 http://10.10.20.131:30080/ experiments/kubeedge/node-failure/cloud/run-01-c2"
  exit 1
fi

ROLE="$1"
FAILED_NODE="$2"
URL="$3"
RUN_DIR="$4"

PRE_SECONDS="${PRE_SECONDS:-30}"
FAULT_SECONDS="${FAULT_SECONDS:-120}"
POST_SECONDS="${POST_SECONDS:-60}"
INTERVAL="${INTERVAL:-1}"
TIMEOUT="${TIMEOUT:-2}"
NODE_READY_TIMEOUT_SECONDS="${NODE_READY_TIMEOUT_SECONDS:-600}"
NODE_NOTREADY_TIMEOUT_SECONDS="${NODE_NOTREADY_TIMEOUT_SECONDS:-180}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR="${MONITOR:-$SCRIPT_DIR/request_monitor.py}"

mkdir -p "$RUN_DIR"

MONITOR_PID=""

cleanup() {
  if [ -n "${MONITOR_PID:-}" ] && kill -0 "$MONITOR_PID" 2>/dev/null; then
    echo "Stopping request monitor PID $MONITOR_PID ..."
    kill -TERM "$MONITOR_PID" 2>/dev/null || true

    for _ in {1..5}; do
      if ! kill -0 "$MONITOR_PID" 2>/dev/null; then
        break
      fi
      sleep 1
    done

    if kill -0 "$MONITOR_PID" 2>/dev/null; then
      echo "Request monitor did not stop after TERM, sending KILL ..."
      kill -KILL "$MONITOR_PID" 2>/dev/null || true
    fi

    wait "$MONITOR_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

node_ready_status() {
  kubectl get node "$FAILED_NODE" -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}' 2>/dev/null || echo "Missing"
}

snapshot() {
  local phase="$1"

  kubectl get nodes -o wide > "$RUN_DIR/nodes_${phase}.txt" 2>&1 || true
  kubectl get pods -n testapp -o wide > "$RUN_DIR/pods_${phase}.txt" 2>&1 || true
  kubectl get pods -A -o wide > "$RUN_DIR/pods_all_${phase}.txt" 2>&1 || true
  kubectl get deploy -n testapp -o wide > "$RUN_DIR/deployment_${phase}.txt" 2>&1 || true
  kubectl get svc -n testapp -o wide > "$RUN_DIR/service_${phase}.txt" 2>&1 || true
  kubectl get pods -n kubeedge -o wide > "$RUN_DIR/kubeedge_pods_${phase}.txt" 2>&1 || true
  kubectl get events -A --sort-by=.metadata.creationTimestamp > "$RUN_DIR/events_${phase}.txt" 2>&1 || true
}

wait_for_notready() {
  echo "Waiting until node $FAILED_NODE is no longer Ready ..."
  local start
  start="$(date +%s)"

  while true; do
    local status
    status="$(node_ready_status)"
    echo "$(date -Is) node_ready_status=$status" | tee -a "$RUN_DIR/node_notready_poll.log"

    if [ "$status" != "True" ]; then
      date -Is | tee "$RUN_DIR/node_notready_time.txt"
      return 0
    fi

    local now elapsed
    now="$(date +%s)"
    elapsed="$((now - start))"

    if [ "$elapsed" -ge "$NODE_NOTREADY_TIMEOUT_SECONDS" ]; then
      echo "WARNING: node did not become NotReady within ${NODE_NOTREADY_TIMEOUT_SECONDS}s" | tee "$RUN_DIR/node_notready_timeout.txt"
      return 1
    fi

    sleep 2
  done
}

wait_for_ready() {
  echo "Waiting until node $FAILED_NODE is Ready again ..."
  local start
  start="$(date +%s)"

  while true; do
    local status
    status="$(node_ready_status)"
    echo "$(date -Is) node_ready_status=$status" | tee -a "$RUN_DIR/node_ready_poll.log"

    if [ "$status" = "True" ]; then
      date -Is | tee "$RUN_DIR/node_ready_time.txt"
      return 0
    fi

    local now elapsed
    now="$(date +%s)"
    elapsed="$((now - start))"

    if [ "$elapsed" -ge "$NODE_READY_TIMEOUT_SECONDS" ]; then
      echo "WARNING: node did not become Ready within ${NODE_READY_TIMEOUT_SECONDS}s" | tee "$RUN_DIR/node_ready_timeout.txt"
      return 1
    fi

    sleep 2
  done
}

csv_stats() {
  local file="$1"

  if [ ! -f "$file" ]; then
    echo "total_requests=0"
    echo "ok_requests=0"
    echo "failed_requests=0"
    echo "success_rate_percent=0.00"
    return
  fi

  local total ok fail rate
  total="$(awk -F',' 'NR>1 {total++} END {print total+0}' "$file")"
  ok="$(awk -F',' 'NR>1 && $3=="200" && $5=="True" {ok++} END {print ok+0}' "$file")"
  fail="$(awk -F',' 'NR>1 && !($3=="200" && $5=="True") {fail++} END {print fail+0}' "$file")"

  if [ "$total" -gt 0 ]; then
    rate="$(awk -v ok="$ok" -v total="$total" 'BEGIN {printf "%.2f", (ok/total)*100}')"
  else
    rate="0.00"
  fi

  echo "total_requests=$total"
  echo "ok_requests=$ok"
  echo "failed_requests=$fail"
  echo "success_rate_percent=$rate"
}

seconds_between() {
  local start_file="$1"
  local end_file="$2"

  if [ ! -f "$start_file" ] || [ ! -f "$end_file" ]; then
    echo ""
    return
  fi

  python3 - "$start_file" "$end_file" <<'PY'
import sys
from datetime import datetime

with open(sys.argv[1]) as f:
    start = datetime.fromisoformat(f.read().strip())
with open(sys.argv[2]) as f:
    end = datetime.fromisoformat(f.read().strip())

print(round((end - start).total_seconds(), 2))
PY
}

echo "===== KubeEdge Node Failure Manual Test ====="
echo "Role: $ROLE"
echo "Failed node: $FAILED_NODE"
echo "Monitor URL: $URL"
echo "Run dir: $RUN_DIR"
echo "PRE_SECONDS: $PRE_SECONDS"
echo "FAULT_SECONDS: $FAULT_SECONDS"
echo "POST_SECONDS: $POST_SECONDS"
echo "INTERVAL: $INTERVAL"
echo "TIMEOUT: $TIMEOUT"
echo

echo "$ROLE" > "$RUN_DIR/node_role.txt"
echo "$FAILED_NODE" > "$RUN_DIR/failed_node.txt"
echo "$URL" > "$RUN_DIR/url.txt"
echo "VM manually powered off in VMware Fusion and manually restarted" > "$RUN_DIR/fault_method.txt"
echo "$PRE_SECONDS" > "$RUN_DIR/pre_seconds.txt"
echo "$FAULT_SECONDS" > "$RUN_DIR/fault_seconds.txt"
echo "$POST_SECONDS" > "$RUN_DIR/post_seconds.txt"
echo "$INTERVAL" > "$RUN_DIR/interval_seconds.txt"
echo "$TIMEOUT" > "$RUN_DIR/timeout_seconds.txt"

date -Is | tee "$RUN_DIR/test_start_time.txt"

snapshot "before"

echo "Starting request monitor..."
python3 "$MONITOR" \
  --url "$URL" \
  --output "$RUN_DIR/requests.csv" \
  --interval "$INTERVAL" \
  --timeout "$TIMEOUT" &
MONITOR_PID="$!"

echo "$MONITOR_PID" | tee "$RUN_DIR/monitor_pid.txt"

echo
echo "Baseline phase: ${PRE_SECONDS}s"
sleep "$PRE_SECONDS"

echo
echo "============================================================"
echo "BEREIT FÜR FEHLER: VM $FAILED_NODE wird gleich ausgeschaltet."
echo "Öffne VMware Fusion und bereite die VM $FAILED_NODE vor."
echo "Drücke ENTER, wenn du bereit bist. Danach wird fault_time gespeichert."
echo "============================================================"
read -r

date -Is | tee "$RUN_DIR/fault_time.txt"

echo
echo "============================================================"
echo "JETZT VM $FAILED_NODE IN VMWARE FUSION AUSSCHALTEN."
echo "Warte, bis die VM wirklich ausgeschaltet ist."
echo "Danach hier ENTER drücken."
echo "============================================================"
read -r

date -Is | tee "$RUN_DIR/vm_poweroff_confirmed_time.txt"
FAULT_EPOCH="$(date +%s)"

wait_for_notready || true
snapshot "during"

echo
echo "Node-during snapshot saved."
echo "Die VM bleibt ab bestätigtem Ausschalten ungefähr ${FAULT_SECONDS}s ausgeschaltet."

while true; do
  NOW="$(date +%s)"
  ELAPSED="$((NOW - FAULT_EPOCH))"
  REMAINING="$((FAULT_SECONDS - ELAPSED))"

  if [ "$REMAINING" -le 0 ]; then
    break
  fi

  echo "Remaining planned VM-off time: ${REMAINING}s"
  sleep 10
done

echo
echo "============================================================"
echo "JETZT VM $FAILED_NODE IN VMWARE FUSION WIEDER STARTEN."
echo "Danach hier ENTER drücken."
echo "============================================================"
read -r

date -Is | tee "$RUN_DIR/vm_restart_time.txt"

wait_for_ready || true

if [ -f "$RUN_DIR/node_ready_time.txt" ]; then
  echo "Node is Ready again."
else
  echo
  echo "============================================================"
  echo "Node wurde nicht automatisch Ready."
  echo "Falls du manuell eingreifen musst, tue das jetzt."
  echo "Beispiel bei Edge: sudo systemctl restart edgecore"
  echo "Beispiel bei Cloud: sudo systemctl restart k3s"
  echo "Danach hier ENTER drücken."
  echo "Wenn kein manueller Eingriff erfolgt ist, einfach ENTER drücken."
  echo "============================================================"
  read -r

  echo "manual intervention prompt reached" | tee "$RUN_DIR/manual_intervention_prompt.txt"
  date -Is | tee "$RUN_DIR/manual_intervention_prompt_time.txt"

  wait_for_ready || true
fi

snapshot "after"

echo
echo "Post phase: ${POST_SECONDS}s"
sleep "$POST_SECONDS"

snapshot "final"

date -Is | tee "$RUN_DIR/test_end_time.txt"

cleanup
trap - EXIT

{
  echo "scenario=node-failure"
  echo "system=kubeedge"
  echo "role=$ROLE"
  echo "failed_node=$FAILED_NODE"
  echo "url=$URL"
  echo "pre_seconds=$PRE_SECONDS"
  echo "fault_seconds=$FAULT_SECONDS"
  echo "post_seconds=$POST_SECONDS"
  echo "interval_seconds=$INTERVAL"
  echo "timeout_seconds=$TIMEOUT"
  echo "node_notready_detected=$([ -f "$RUN_DIR/node_notready_time.txt" ] && echo true || echo false)"
  echo "node_ready_detected=$([ -f "$RUN_DIR/node_ready_time.txt" ] && echo true || echo false)"
  echo "node_notready_seconds=$(seconds_between "$RUN_DIR/fault_time.txt" "$RUN_DIR/node_notready_time.txt")"
  echo "node_recovery_seconds=$(seconds_between "$RUN_DIR/fault_time.txt" "$RUN_DIR/node_ready_time.txt")"
  echo "vm_poweroff_to_ready_seconds=$(seconds_between "$RUN_DIR/vm_poweroff_confirmed_time.txt" "$RUN_DIR/node_ready_time.txt")"
  echo "vm_restart_to_ready_seconds=$(seconds_between "$RUN_DIR/vm_restart_time.txt" "$RUN_DIR/node_ready_time.txt")"
  csv_stats "$RUN_DIR/requests.csv"
} > "$RUN_DIR/summary.txt"

echo
echo "===== SUMMARY ====="
cat "$RUN_DIR/summary.txt"

echo
echo "Run completed: $RUN_DIR"
