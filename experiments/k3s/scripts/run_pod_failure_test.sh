#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <url> <run_dir>"
  echo "Example: $0 http://10.10.10.129:30080/ experiments/k3s/pod-failure/run-01"
  exit 1
fi

URL="$1"
RUN_DIR="$2"

NAMESPACE="${NAMESPACE:-testapp}"
DEPLOYMENT="${DEPLOYMENT:-nginx-test}"
LABEL_SELECTOR="${LABEL_SELECTOR:-app=nginx-test}"
EXPECTED_REPLICAS="${EXPECTED_REPLICAS:-3}"

PRE_SECONDS="${PRE_SECONDS:-30}"
POST_SECONDS="${POST_SECONDS:-60}"
INTERVAL="${INTERVAL:-1}"
TIMEOUT="${TIMEOUT:-2}"
RECOVERY_TIMEOUT_SECONDS="${RECOVERY_TIMEOUT_SECONDS:-180}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR="${MONITOR:-$SCRIPT_DIR/request_monitor.py}"

ensure_experiment_routes() {
  echo "Ensuring experiment routes via router..."
  mkdir -p "$RUN_DIR/route-checks"

  ssh router 'sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null; sudo tc qdisc show dev ens161; sudo tc qdisc show dev ens256' \
    > "$RUN_DIR/route-checks/router.txt" 2>&1 || return 1

  for h in s1 s2 s3; do
    ssh "$h" 'sudo ip route replace 10.10.20.0/24 via 10.10.10.136 dev ens256; ip route get 10.10.20.129; ip route get 10.10.20.130' \
      > "$RUN_DIR/route-checks/${h}.txt" 2>&1 || return 1
  done

  for h in w1 w2; do
    ssh "$h" 'sudo ip route replace 10.10.10.0/24 via 10.10.20.133 dev ens256; ip route get 10.10.10.129; ip route get 10.10.10.130; ip route get 10.10.10.131' \
      > "$RUN_DIR/route-checks/${h}.txt" 2>&1 || return 1
  done

  for h in s1 s2 s3; do
    if ! grep -q "via 10.10.10.136 dev ens256" "$RUN_DIR/route-checks/${h}.txt"; then
      echo "ERROR: $h route to worker-net not via router" | tee "$RUN_DIR/route_error.txt"
      return 1
    fi
  done

  for h in w1 w2; do
    if ! grep -q "via 10.10.20.133 dev ens256" "$RUN_DIR/route-checks/${h}.txt"; then
      echo "ERROR: $h route to server-net not via router" | tee "$RUN_DIR/route_error.txt"
      return 1
    fi
  done

  ping -c 2 10.10.20.129 > "$RUN_DIR/route-checks/s1-to-w1-ping.txt" 2>&1 || return 1
  ping -c 2 10.10.20.130 > "$RUN_DIR/route-checks/s1-to-w2-ping.txt" 2>&1 || return 1
  ssh w1 'ping -c 2 10.10.10.129' > "$RUN_DIR/route-checks/w1-to-s1-ping.txt" 2>&1 || return 1
  ssh w2 'ping -c 2 10.10.10.129' > "$RUN_DIR/route-checks/w2-to-s1-ping.txt" 2>&1 || return 1

  echo "routes_ok=true" | tee "$RUN_DIR/routes_ok.txt"
}

mkdir -p "$RUN_DIR"

MONITOR_PID=""
NODE_MONITOR_PID=""

cleanup() {
  if [ -n "${MONITOR_PID:-}" ] && kill -0 "$MONITOR_PID" 2>/dev/null; then
    echo "Stopping request monitor PID $MONITOR_PID ..."
    kill -TERM "$MONITOR_PID" 2>/dev/null || true
    for _ in {1..5}; do
      kill -0 "$MONITOR_PID" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$MONITOR_PID" 2>/dev/null && kill -KILL "$MONITOR_PID" 2>/dev/null || true
    wait "$MONITOR_PID" 2>/dev/null || true
  fi

  if [ -n "${NODE_MONITOR_PID:-}" ] && kill -0 "$NODE_MONITOR_PID" 2>/dev/null; then
    echo "Stopping node monitor PID $NODE_MONITOR_PID ..."
    kill -TERM "$NODE_MONITOR_PID" 2>/dev/null || true
    wait "$NODE_MONITOR_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

ready_pod_count() {
  kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" --no-headers 2>/dev/null \
    | awk '$2 ~ /^1\/1$/ && $3 == "Running" {count++} END {print count+0}'
}

sum_restarts() {
  kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath='{range .items[*]}{range .status.containerStatuses[*]}{.restartCount}{"\n"}{end}{end}' 2>/dev/null \
    | awk '{s+=$1} END{print s+0}'
}

all_nodes_ready() {
  local not_ready
  not_ready="$(kubectl get nodes --no-headers 2>/dev/null | awk '$2 != "Ready" {print $1 ":" $2}')"
  if [ -z "$not_ready" ]; then
    return 0
  fi
  echo "$not_ready" >&2
  return 1
}

node_monitor() {
  while true; do
    ts="$(date -Is)"
    kubectl get nodes --no-headers 2>/dev/null | while read -r name status rest; do
      echo "$ts,$name,$status"
    done
    sleep 1
  done
}

echo "===== K3s Pod Failure Test ====="
echo "URL: $URL"
echo "Run dir: $RUN_DIR"
echo "Namespace: $NAMESPACE"
echo "Deployment: $DEPLOYMENT"
echo "Label selector: $LABEL_SELECTOR"
echo "Expected replicas: $EXPECTED_REPLICAS"
echo "PRE_SECONDS: $PRE_SECONDS"
echo "POST_SECONDS: $POST_SECONDS"
echo "INTERVAL: $INTERVAL"
echo "TIMEOUT: $TIMEOUT"
echo

{
  echo "scenario=pod-failure"
  echo "system=k3s"
  echo "url=$URL"
  echo "namespace=$NAMESPACE"
  echo "deployment=$DEPLOYMENT"
  echo "label_selector=$LABEL_SELECTOR"
  echo "expected_replicas=$EXPECTED_REPLICAS"
  echo "pre_seconds=$PRE_SECONDS"
  echo "post_seconds=$POST_SECONDS"
  echo "interval_seconds=$INTERVAL"
  echo "timeout_seconds=$TIMEOUT"
} > "$RUN_DIR/config.txt"

echo "$URL" > "$RUN_DIR/url.txt"
echo "$PRE_SECONDS" > "$RUN_DIR/pre_seconds.txt"
echo "$POST_SECONDS" > "$RUN_DIR/post_seconds.txt"
echo "$INTERVAL" > "$RUN_DIR/interval_seconds.txt"
echo "$TIMEOUT" > "$RUN_DIR/timeout_seconds.txt"
echo "$NAMESPACE" > "$RUN_DIR/namespace.txt"
echo "$DEPLOYMENT" > "$RUN_DIR/deployment.txt"
echo "$LABEL_SELECTOR" > "$RUN_DIR/label_selector.txt"
echo "$EXPECTED_REPLICAS" > "$RUN_DIR/expected_replicas.txt"

date -Is | tee "$RUN_DIR/test_start_time.txt"

ensure_experiment_routes

kubectl get nodes -o wide > "$RUN_DIR/nodes_before.txt"
kubectl get nodes -o json > "$RUN_DIR/nodes_before.json"
kubectl get pods -n "$NAMESPACE" -o wide > "$RUN_DIR/pods_before.txt"
kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o json > "$RUN_DIR/pods_before.json"
kubectl get deploy -n "$NAMESPACE" -o wide > "$RUN_DIR/deployment_before.txt"
kubectl get svc -n "$NAMESPACE" -o wide > "$RUN_DIR/service_before.txt"
kubectl get endpoints -n "$NAMESPACE" -o wide > "$RUN_DIR/endpoints_before.txt" 2>/dev/null || true
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$RUN_DIR/events_before.txt"

sum_restarts > "$RUN_DIR/pod_restarts_before.txt"

echo "timestamp,node,status" > "$RUN_DIR/node_status_poll.csv"
node_monitor >> "$RUN_DIR/node_status_poll.csv" &
NODE_MONITOR_PID="$!"
echo "$NODE_MONITOR_PID" > "$RUN_DIR/node_monitor_pid.txt"

echo "Starting request monitor..."
python3 "$MONITOR" \
  --url "$URL" \
  --output "$RUN_DIR/requests.csv" \
  --interval "$INTERVAL" \
  --timeout "$TIMEOUT" &
MONITOR_PID="$!"

echo "Monitor PID: $MONITOR_PID" | tee "$RUN_DIR/monitor_pid.txt"

echo "Baseline phase: ${PRE_SECONDS}s"
sleep "$PRE_SECONDS"

POD_TO_DELETE="$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')"

if [ -z "$POD_TO_DELETE" ]; then
  echo "ERROR: No running pod found for selector $LABEL_SELECTOR in namespace $NAMESPACE" | tee "$RUN_DIR/error.txt"
  exit 1
fi

POD_NODE="$(kubectl get pod -n "$NAMESPACE" "$POD_TO_DELETE" -o jsonpath='{.spec.nodeName}')"

echo "$POD_TO_DELETE" | tee "$RUN_DIR/deleted_pod.txt"
echo "$POD_NODE" | tee "$RUN_DIR/deleted_pod_node.txt"

date -Is | tee "$RUN_DIR/fault_time.txt"

echo "Deleting pod $POD_TO_DELETE on node $POD_NODE ..."
kubectl delete pod -n "$NAMESPACE" "$POD_TO_DELETE" --wait=false | tee "$RUN_DIR/delete_command_output.txt"

echo "Waiting for recovery: $EXPECTED_REPLICAS ready Running pods..."
RECOVERY_START_EPOCH="$(date +%s)"
RECOVERED="false"

while true; do
  CURRENT_READY="$(ready_pod_count)"
  echo "$(date -Is) ready_pods=$CURRENT_READY/$EXPECTED_REPLICAS" | tee -a "$RUN_DIR/recovery_poll.log"

  if [ "$CURRENT_READY" -ge "$EXPECTED_REPLICAS" ]; then
    date -Is | tee "$RUN_DIR/recovery_time.txt"
    RECOVERED="true"
    break
  fi

  NOW_EPOCH="$(date +%s)"
  ELAPSED="$((NOW_EPOCH - RECOVERY_START_EPOCH))"

  if [ "$ELAPSED" -ge "$RECOVERY_TIMEOUT_SECONDS" ]; then
    echo "WARNING: Recovery timeout after ${RECOVERY_TIMEOUT_SECONDS}s" | tee "$RUN_DIR/recovery_timeout.txt"
    break
  fi

  sleep 1
done

kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o wide > "$RUN_DIR/pods_after_recovery.txt"
kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o json > "$RUN_DIR/pods_after_recovery.json"

NEW_POD_INFO="$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.nodeName}{"\n"}{end}' | grep -v "^${POD_TO_DELETE} " | sort | tail -n 1 || true)"
echo "$NEW_POD_INFO" > "$RUN_DIR/new_pod_info.txt"

STABLE_DETECTED="false"
STABLE_START_EPOCH="$(date +%s)"

while true; do
  PODS_READY="$(ready_pod_count)"

  if all_nodes_ready && [ "$PODS_READY" -ge "$EXPECTED_REPLICAS" ]; then
    date -Is | tee "$RUN_DIR/stable_time.txt"
    STABLE_DETECTED="true"
    break
  fi

  echo "$(date -Is) pods_ready=$PODS_READY/$EXPECTED_REPLICAS all_nodes_ready=pending" | tee -a "$RUN_DIR/stable_poll.log"

  NOW_EPOCH="$(date +%s)"
  ELAPSED="$((NOW_EPOCH - STABLE_START_EPOCH))"

  if [ "$ELAPSED" -ge "$RECOVERY_TIMEOUT_SECONDS" ]; then
    echo "WARNING: Stable state timeout after ${RECOVERY_TIMEOUT_SECONDS}s" | tee "$RUN_DIR/stable_timeout.txt"
    break
  fi

  sleep 1
done

echo "Post phase: ${POST_SECONDS}s"
sleep "$POST_SECONDS"

kubectl get nodes -o wide > "$RUN_DIR/nodes_after.txt"
kubectl get nodes -o json > "$RUN_DIR/nodes_after.json"
kubectl get pods -n "$NAMESPACE" -o wide > "$RUN_DIR/pods_after.txt"
kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o json > "$RUN_DIR/pods_after.json"
kubectl get deploy -n "$NAMESPACE" -o wide > "$RUN_DIR/deployment_after.txt"
kubectl get svc -n "$NAMESPACE" -o wide > "$RUN_DIR/service_after.txt"
kubectl get endpoints -n "$NAMESPACE" -o wide > "$RUN_DIR/endpoints_after.txt" 2>/dev/null || true
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$RUN_DIR/events_after.txt"

sum_restarts > "$RUN_DIR/pod_restarts_after.txt"

date -Is | tee "$RUN_DIR/test_end_time.txt"

cleanup
trap - EXIT

python3 - "$RUN_DIR" <<'PY' > "$RUN_DIR/summary.txt"
import csv
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

base = Path(sys.argv[1])

def read_text(name):
    p = base / name
    return p.read_text().strip() if p.exists() else ""

def parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def pct(a, b):
    return round((a / b) * 100, 2) if b else 0.0

rows = []
req = base / "requests.csv"
if req.exists():
    with req.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

total = len(rows)
ok = sum(1 for r in rows if r.get("status_code") == "200" and r.get("success") == "True")
fail = total - ok
errors = Counter(r.get("error", "") for r in rows if not (r.get("status_code") == "200" and r.get("success") == "True"))

fault = parse_dt(read_text("fault_time.txt"))
recovery = parse_dt(read_text("recovery_time.txt"))
stable = parse_dt(read_text("stable_time.txt"))

recovery_seconds = ""
if fault and recovery:
    recovery_seconds = round((recovery - fault).total_seconds(), 2)

stabilization_seconds = ""
if fault and stable:
    stabilization_seconds = round((stable - fault).total_seconds(), 2)

before_restart = int(read_text("pod_restarts_before.txt") or 0)
after_restart = int(read_text("pod_restarts_after.txt") or 0)

node_notready_detected = False
notready_seconds = 0
current_start = None

poll = base / "node_status_poll.csv"
if poll.exists():
    with poll.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ts = parse_dt(r.get("timestamp", ""))
            status = r.get("status", "")
            if not ts:
                continue
            if status != "Ready":
                node_notready_detected = True
                if current_start is None:
                    current_start = ts
            else:
                if current_start is not None:
                    notready_seconds += (ts - current_start).total_seconds()
                    current_start = None

if current_start is not None:
    end = parse_dt(read_text("test_end_time.txt")) or current_start
    notready_seconds += (end - current_start).total_seconds()

final_ready = "ja"
nodes_after = read_text("nodes_after.txt")
for line in nodes_after.splitlines()[1:]:
    parts = line.split()
    if len(parts) >= 2 and parts[1] != "Ready":
        final_ready = "nein"

new_pod_info = read_text("new_pod_info.txt")
new_pod = ""
new_pod_node = ""
if new_pod_info:
    parts = new_pod_info.split()
    if len(parts) >= 2:
        new_pod = parts[0]
        new_pod_node = parts[1]

recovered = "true" if read_text("recovery_time.txt") else "false"
stable_detected = "true" if read_text("stable_time.txt") else "false"
valid = "ja" if recovered == "true" and final_ready == "ja" and total > 0 else "nein"

print("scenario=pod-failure")
print("system=k3s")
print(f"url={read_text('url.txt')}")
print(f"namespace={read_text('namespace.txt')}")
print(f"deployment={read_text('deployment.txt')}")
print(f"label_selector={read_text('label_selector.txt')}")
print(f"expected_replicas={read_text('expected_replicas.txt')}")
print(f"deleted_pod={read_text('deleted_pod.txt')}")
print(f"deleted_pod_node={read_text('deleted_pod_node.txt')}")
print(f"new_pod={new_pod}")
print(f"new_pod_node={new_pod_node}")
print(f"recovered={recovered}")
print(f"stable_detected={stable_detected}")
print(f"recovery_seconds={recovery_seconds}")
print(f"stabilization_seconds={stabilization_seconds}")
print(f"total_requests={total}")
print(f"ok_requests={ok}")
print(f"failed_requests={fail}")
print(f"success_rate_percent={pct(ok, total)}")
print(f"error_rate_percent={pct(fail, total)}")
print(f"error_types={dict(errors)}")
print(f"pod_restart_delta={after_restart - before_restart}")
print(f"node_notready_detected={'true' if node_notready_detected else 'false'}")
print(f"node_notready_seconds={round(notready_seconds, 2)}")
print(f"final_ready={final_ready}")
print(f"valid={valid}")
PY

echo
echo "===== SUMMARY ====="
cat "$RUN_DIR/summary.txt"
echo
echo "Run completed: $RUN_DIR"
