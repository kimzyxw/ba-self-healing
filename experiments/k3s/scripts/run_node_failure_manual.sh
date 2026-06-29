#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <role> <node> <monitor_url> <run_dir>"
  echo "Example worker: $0 worker k3s-w1 http://10.10.10.129:30080/ experiments/k3s/node-failure/worker-rerun-final/run-01-k3s-w1"
  echo "Example server: $0 server k3s-s2 http://10.10.10.129:30080/ experiments/k3s/node-failure/server-rerun-final/run-01-k3s-s2"
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
NODE_MONITOR_PID=""

cleanup() {
  for pid in "${MONITOR_PID:-}" "${NODE_MONITOR_PID:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping PID $pid ..."
      kill -TERM "$pid" 2>/dev/null || true
      sleep 1
      kill -KILL "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

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

ensure_experiment_routes() {
  local phase="$1"
  local dir="$RUN_DIR/route_preflight_${phase}"
  mkdir -p "$dir"

  echo "Ensuring experiment routes via router ($phase) ..."

  ssh router 'sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null; sudo tc qdisc show dev ens161; sudo tc qdisc show dev ens256' \
    > "$dir/router.txt" 2>&1 || {
      echo "Preflight FAILED: router check failed" | tee "$dir/preflight.log"
      return 1
    }

  for h in s1 s2 s3; do
    ssh "$h" 'sudo ip route replace 10.10.20.0/24 via 10.10.10.136 dev ens256; ip route get 10.10.20.129; ip route get 10.10.20.130' \
      > "$dir/${h}.txt" 2>&1 || {
        echo "Preflight FAILED: route setup failed on $h" | tee "$dir/preflight.log"
        return 1
      }
  done

  for h in w1 w2; do
    ssh "$h" 'sudo ip route replace 10.10.10.0/24 via 10.10.20.133 dev ens256; ip route get 10.10.10.129; ip route get 10.10.10.130; ip route get 10.10.10.131' \
      > "$dir/${h}.txt" 2>&1 || {
        echo "Preflight FAILED: route setup failed on $h" | tee "$dir/preflight.log"
        return 1
      }
  done

  for h in s1 s2 s3; do
    grep -q "via 10.10.10.136 dev ens256" "$dir/${h}.txt" || {
      echo "Preflight FAILED: $h not routed to worker-net via router" | tee "$dir/preflight.log"
      return 1
    }
  done

  for h in w1 w2; do
    grep -q "via 10.10.20.133 dev ens256" "$dir/${h}.txt" || {
      echo "Preflight FAILED: $h not routed to server-net via router" | tee "$dir/preflight.log"
      return 1
    }
  done

  ping -c 2 10.10.20.129 > "$dir/s1-to-w1-ping.txt" 2>&1 || return 1
  ping -c 2 10.10.20.130 > "$dir/s1-to-w2-ping.txt" 2>&1 || return 1
  ssh w1 'ping -c 2 10.10.10.129' > "$dir/w1-to-s1-ping.txt" 2>&1 || return 1
  ssh w2 'ping -c 2 10.10.10.129' > "$dir/w2-to-s1-ping.txt" 2>&1 || return 1

  echo "Preflight OK" | tee "$dir/preflight.log"
}

node_ready_status() {
  kubectl get node "$FAILED_NODE" -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}' 2>/dev/null || echo "Missing"
}

all_nodes_ready() {
  local not_ready
  not_ready="$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 != "Ready" {print $1 ":" $2}')"
  [ -z "$not_ready" ]
}

testapp_ready_pods() {
  kubectl -n testapp get pods -l app=nginx-test -o json 2>/dev/null | python3 -c '
import json, sys
d=json.load(sys.stdin)
count=0
for item in d.get("items", []):
    if item.get("status", {}).get("phase") != "Running":
        continue
    statuses=item.get("status", {}).get("containerStatuses", [])
    if statuses and all(s.get("ready") for s in statuses):
        count += 1
print(count)
' || echo 0
}

pods_on_failed_node() {
  kubectl -n testapp get pods -l app=nginx-test -o json 2>/dev/null | python3 - "$FAILED_NODE" <<'PY'
import json, sys
node = sys.argv[1]
d = json.load(sys.stdin)
count = 0
names = []
for item in d.get("items", []):
    if item.get("spec", {}).get("nodeName") == node:
        count += 1
        names.append(item["metadata"]["name"])
print(count)
print(",".join(names))
PY
}

snapshot() {
  local phase="$1"

  kubectl get nodes -o wide > "$RUN_DIR/nodes_${phase}.txt" 2>&1 || true
  kubectl -n testapp get deploy -o wide > "$RUN_DIR/deployment_${phase}.txt" 2>&1 || true
  kubectl -n testapp get pods -o wide > "$RUN_DIR/pods_${phase}.txt" 2>&1 || true
  kubectl get pods -A -o wide > "$RUN_DIR/pods_all_${phase}.txt" 2>&1 || true
  kubectl -n testapp get svc -o wide > "$RUN_DIR/service_${phase}.txt" 2>&1 || true
  kubectl -n testapp get endpoints -o wide > "$RUN_DIR/endpoints_${phase}.txt" 2>&1 || true
  kubectl get events -A --sort-by=.metadata.creationTimestamp > "$RUN_DIR/events_${phase}.txt" 2>&1 || true

  pods_on_failed_node > "$RUN_DIR/pods_on_failed_node_${phase}.txt" 2>&1 || true
}

node_monitor() {
  echo "timestamp,node,status" > "$RUN_DIR/node_status_poll.csv"
  while true; do
    local ts
    ts="$(date -Is)"
    kubectl get nodes --no-headers 2>/dev/null | awk -v ts="$ts" '{print ts "," $1 "," $2}' >> "$RUN_DIR/node_status_poll.csv" || true
    sleep 1
  done
}

sum_testapp_restarts() {
  kubectl -n testapp get pods -l app=nginx-test -o json 2>/dev/null | python3 -c '
import json, sys
d=json.load(sys.stdin)
total=0
for item in d.get("items", []):
    for s in item.get("status", {}).get("containerStatuses", []) or []:
        total += int(s.get("restartCount", 0))
print(total)
' || echo 0
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

wait_for_stable() {
  echo "Waiting for stable cluster state ..."
  local start
  start="$(date +%s)"

  while true; do
    local ready_pods
    ready_pods="$(testapp_ready_pods)"

    echo "$(date -Is) ready_pods=${ready_pods}/3 all_nodes_ready=$(all_nodes_ready && echo true || echo false)" | tee -a "$RUN_DIR/stability_poll.log"

    if [ "$ready_pods" -ge 3 ] && all_nodes_ready; then
      date -Is | tee "$RUN_DIR/stable_time.txt"
      return 0
    fi

    local now elapsed
    now="$(date +%s)"
    elapsed="$((now - start))"

    if [ "$elapsed" -ge "$NODE_READY_TIMEOUT_SECONDS" ]; then
      echo "WARNING: cluster did not become stable within ${NODE_READY_TIMEOUT_SECONDS}s" | tee "$RUN_DIR/stability_timeout.txt"
      return 1
    fi

    sleep 2
  done
}

csv_stats() {
  local file="$1"

  python3 - "$file" <<'PY'
import csv, sys
from collections import Counter
from pathlib import Path

path = Path(sys.argv[1])
total = ok = fail = 0
errors = Counter()

if path.exists():
    with path.open(newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            status = row.get("status_code", "")
            success = row.get("success", "")
            err = row.get("error", "")
            is_ok = status == "200" and success == "True"
            if is_ok:
                ok += 1
            else:
                fail += 1
                errors[err or "unknown"] += 1

success_rate = (ok / total * 100) if total else 0.0
error_rate = (fail / total * 100) if total else 0.0

print(f"total_requests={total}")
print(f"ok_requests={ok}")
print(f"failed_requests={fail}")
print(f"success_rate_percent={success_rate:.2f}")
print(f"error_rate_percent={error_rate:.2f}")
print("error_types=" + (";".join(f"{k}:{v}" for k, v in sorted(errors.items())) if errors else "{}"))
PY
}

echo "===== K3s Node Failure Manual Test ====="
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

{
  echo "role=$ROLE"
  echo "failed_node=$FAILED_NODE"
  echo "url=$URL"
  echo "pre_seconds=$PRE_SECONDS"
  echo "fault_seconds=$FAULT_SECONDS"
  echo "post_seconds=$POST_SECONDS"
  echo "interval_seconds=$INTERVAL"
  echo "timeout_seconds=$TIMEOUT"
} > "$RUN_DIR/config.txt"

date -Is | tee "$RUN_DIR/test_start_time.txt"

ensure_experiment_routes "before"

snapshot "before"
sum_testapp_restarts > "$RUN_DIR/pod_restarts_before.txt"

node_monitor &
NODE_MONITOR_PID="$!"
echo "$NODE_MONITOR_PID" > "$RUN_DIR/node_monitor_pid.txt"

echo "Starting request monitor..."
python3 "$MONITOR" \
  --url "$URL" \
  --output "$RUN_DIR/requests.csv" \
  --interval "$INTERVAL" \
  --timeout "$TIMEOUT" &
MONITOR_PID="$!"
echo "$MONITOR_PID" > "$RUN_DIR/monitor_pid.txt"

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

if [ ! -f "$RUN_DIR/node_ready_time.txt" ]; then
  echo
  echo "============================================================"
  echo "Node wurde nicht automatisch Ready."
  echo "Falls nötig, jetzt manuell eingreifen."
  echo "Server-Beispiel: ssh <node-alias> 'sudo systemctl restart k3s'"
  echo "Worker-Beispiel: ssh <node-alias> 'sudo systemctl restart k3s-agent'"
  echo "Danach hier ENTER drücken."
  echo "============================================================"
  read -r

  echo "manual_intervention_prompt_reached=true" > "$RUN_DIR/manual_intervention.txt"
  date -Is | tee "$RUN_DIR/manual_intervention_time.txt"

  wait_for_ready || true
fi

wait_for_stable || true

snapshot "after"

echo
echo "Post phase: ${POST_SECONDS}s"
sleep "$POST_SECONDS"

ensure_experiment_routes "after" || true
snapshot "final"
sum_testapp_restarts > "$RUN_DIR/pod_restarts_final.txt"

date -Is | tee "$RUN_DIR/test_end_time.txt"

cleanup
trap - EXIT

NODE_NOTREADY_DETECTED="$([ -f "$RUN_DIR/node_notready_time.txt" ] && echo true || echo false)"
NODE_READY_DETECTED="$([ -f "$RUN_DIR/node_ready_time.txt" ] && echo true || echo false)"
FINAL_READY="$(all_nodes_ready && echo ja || echo nein)"
PRE_OK="$([ -f "$RUN_DIR/route_preflight_before/preflight.log" ] && grep -q "Preflight OK" "$RUN_DIR/route_preflight_before/preflight.log" && echo true || echo false)"
POST_OK="$([ -f "$RUN_DIR/route_preflight_after/preflight.log" ] && grep -q "Preflight OK" "$RUN_DIR/route_preflight_after/preflight.log" && echo true || echo false)"

RESTARTS_BEFORE="$(cat "$RUN_DIR/pod_restarts_before.txt" 2>/dev/null || echo 0)"
RESTARTS_FINAL="$(cat "$RUN_DIR/pod_restarts_final.txt" 2>/dev/null || echo 0)"
POD_RESTART_DELTA="$((RESTARTS_FINAL - RESTARTS_BEFORE))"

NODE_NOTREADY_DETECTION_SECONDS="$(seconds_between "$RUN_DIR/fault_time.txt" "$RUN_DIR/node_notready_time.txt")"
NODE_NOTREADY_DURATION_SECONDS="$(seconds_between "$RUN_DIR/node_notready_time.txt" "$RUN_DIR/node_ready_time.txt")"
NODE_RECOVERY_SECONDS="$(seconds_between "$RUN_DIR/fault_time.txt" "$RUN_DIR/node_ready_time.txt")"
VM_POWEROFF_TO_READY_SECONDS="$(seconds_between "$RUN_DIR/vm_poweroff_confirmed_time.txt" "$RUN_DIR/node_ready_time.txt")"
VM_RESTART_TO_READY_SECONDS="$(seconds_between "$RUN_DIR/vm_restart_time.txt" "$RUN_DIR/node_ready_time.txt")"
STABILIZATION_SECONDS="$(seconds_between "$RUN_DIR/fault_time.txt" "$RUN_DIR/stable_time.txt")"

VALID="nein"
if [ "$NODE_NOTREADY_DETECTED" = "true" ] && [ "$NODE_READY_DETECTED" = "true" ] && [ "$FINAL_READY" = "ja" ] && [ "$PRE_OK" = "true" ] && [ "$POST_OK" = "true" ]; then
  VALID="ja"
fi

{
  echo "scenario=node-failure"
  echo "system=k3s"
  echo "role=$ROLE"
  echo "failed_node=$FAILED_NODE"
  echo "url=$URL"
  echo "pre_seconds=$PRE_SECONDS"
  echo "fault_seconds=$FAULT_SECONDS"
  echo "post_seconds=$POST_SECONDS"
  echo "interval_seconds=$INTERVAL"
  echo "timeout_seconds=$TIMEOUT"
  echo "node_notready_detected=$NODE_NOTREADY_DETECTED"
  echo "node_ready_detected=$NODE_READY_DETECTED"
  echo "node_notready_detection_seconds=$NODE_NOTREADY_DETECTION_SECONDS"
  echo "node_notready_seconds=$NODE_NOTREADY_DURATION_SECONDS"
  echo "node_recovery_seconds=$NODE_RECOVERY_SECONDS"
  echo "vm_poweroff_to_ready_seconds=$VM_POWEROFF_TO_READY_SECONDS"
  echo "vm_restart_to_ready_seconds=$VM_RESTART_TO_READY_SECONDS"
  echo "recovery_seconds=$NODE_RECOVERY_SECONDS"
  echo "stabilization_seconds=$STABILIZATION_SECONDS"
  csv_stats "$RUN_DIR/requests.csv"
  echo "pod_restart_delta=$POD_RESTART_DELTA"
  echo "preflight_before_ok=$PRE_OK"
  echo "preflight_after_ok=$POST_OK"
  echo "manual_intervention=$([ -f "$RUN_DIR/manual_intervention.txt" ] && echo true || echo false)"
  echo "final_ready=$FINAL_READY"
  echo "valid=$VALID"
} > "$RUN_DIR/summary.txt"

echo
echo "===== SUMMARY ====="
cat "$RUN_DIR/summary.txt"

echo
echo "Run completed: $RUN_DIR"
