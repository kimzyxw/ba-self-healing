#!/usr/bin/env bash
set -euo pipefail

# Single KubeEdge node/component failure test run.
#
# Usage:
#   ./experiments/kubeedge/scripts/run_node_failure_test_async.sh <scenario> <target-node> <target-ip> <service-name> <run-dir>
#
# Examples:
#   ./experiments/kubeedge/scripts/run_node_failure_test_async.sh edge e1 10.10.20.131 edgecore.service experiments/kubeedge/node-failure/edge/run-01-e1
#   ./experiments/kubeedge/scripts/run_node_failure_test_async.sh cloud c2 10.10.10.134 k3s.service experiments/kubeedge/node-failure/cloud/run-01-c2

SCENARIO="${1:?Usage: $0 <scenario> <target-node> <target-ip> <service-name> <run-dir>}"
TARGET_NODE="${2:?Usage: $0 <scenario> <target-node> <target-ip> <service-name> <run-dir>}"
TARGET_IP="${3:?Usage: $0 <scenario> <target-node> <target-ip> <service-name> <run-dir>}"
SERVICE_NAME="${4:?Usage: $0 <scenario> <target-node> <target-ip> <service-name> <run-dir>}"
RUN_DIR="${5:?Usage: $0 <scenario> <target-node> <target-ip> <service-name> <run-dir>}"

URL="${URL:-http://10.10.20.131:30080}"
NAMESPACE="${NAMESPACE:-testapp}"
APP_LABEL="${APP_LABEL:-nginx-testapp}"

PRE_SECONDS="${PRE_SECONDS:-180}"
FAULT_SECONDS="${FAULT_SECONDS:-300}"
POST_SECONDS="${POST_SECONDS:-180}"
INTERVAL="${INTERVAL:-1}"
TIMEOUT="${TIMEOUT:-2}"
MAX_IN_FLIGHT="${MAX_IN_FLIGHT:-10}"

TOTAL_DURATION=$((PRE_SECONDS + FAULT_SECONDS + POST_SECONDS))

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="${SCRIPT_DIR}/request_monitor_async.py"

if [[ -e "${RUN_DIR}" ]]; then
  echo "ERROR: ${RUN_DIR} already exists. Refusing to overwrite existing run data."
  exit 1
fi

mkdir -p "${RUN_DIR}"

log() {
  echo "[$(date -Is)] [$SCENARIO/$TARGET_NODE] $*"
}

log "KubeEdge node failure test"
log "Run directory: ${RUN_DIR}"
log "Target node: ${TARGET_NODE}"
log "Target IP: ${TARGET_IP}"
log "Service: ${SERVICE_NAME}"
log "URL: ${URL}"
log "Pre-fault seconds: ${PRE_SECONDS}"
log "Fault seconds: ${FAULT_SECONDS}"
log "Post-fault seconds: ${POST_SECONDS}"
log "Total monitor duration: ${TOTAL_DURATION}"
log "Timeout: ${TIMEOUT}"
log "Max in flight: ${MAX_IN_FLIGHT}"

date -Is > "${RUN_DIR}/test_start_time.txt"

echo "${SCENARIO}" > "${RUN_DIR}/scenario.txt"
echo "${TARGET_NODE}" > "${RUN_DIR}/target_node.txt"
echo "${TARGET_IP}" > "${RUN_DIR}/target_ip.txt"
echo "${SERVICE_NAME}" > "${RUN_DIR}/service_name.txt"
echo "${URL}" > "${RUN_DIR}/url.txt"
echo "${PRE_SECONDS}" > "${RUN_DIR}/pre_seconds.txt"
echo "${FAULT_SECONDS}" > "${RUN_DIR}/fault_seconds.txt"
echo "${POST_SECONDS}" > "${RUN_DIR}/post_seconds.txt"
echo "${INTERVAL}" > "${RUN_DIR}/interval_seconds.txt"
echo "${TIMEOUT}" > "${RUN_DIR}/timeout_seconds.txt"
echo "${MAX_IN_FLIGHT}" > "${RUN_DIR}/max_in_flight.txt"
echo "systemctl_stop_start" > "${RUN_DIR}/fault_method.txt"

log "Checking remote sudo/systemctl access"
ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl is-active ${SERVICE_NAME}" > "${RUN_DIR}/service_status_before.txt"

log "Capturing cluster state before fault"
kubectl get nodes -o wide > "${RUN_DIR}/nodes_before.txt"
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_before.txt"
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "${RUN_DIR}/events_before.txt" || true

log "Starting request monitor"
date -Is > "${RUN_DIR}/monitor_start_time.txt"

python3 "${MONITOR_SCRIPT}" \
  --url "${URL}" \
  --output "${RUN_DIR}/requests.csv" \
  --interval "${INTERVAL}" \
  --timeout "${TIMEOUT}" \
  --duration "${TOTAL_DURATION}" \
  --max-in-flight "${MAX_IN_FLIGHT}" &
MONITOR_PID=$!

cleanup() {
  if kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
    log "Stopping request monitor because script was interrupted"
    kill "${MONITOR_PID}" >/dev/null 2>&1 || true
    wait "${MONITOR_PID}" || true
  fi
}
trap cleanup INT TERM

log "Pre-fault phase running for ${PRE_SECONDS}s"
sleep "${PRE_SECONDS}"

log "Stopping ${SERVICE_NAME} on ${TARGET_NODE}"
date -Is > "${RUN_DIR}/fault_time.txt"

{
  echo "fault_start=$(date -Is)"
  ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl stop ${SERVICE_NAME}"
  echo "fault_stop_command_finished=$(date -Is)"
  ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl is-active ${SERVICE_NAME}" || true
} > "${RUN_DIR}/fault_command.log" 2>&1

log "Capturing cluster state during fault"
sleep 10
kubectl get nodes -o wide > "${RUN_DIR}/nodes_during.txt" || true
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_during.txt" || true
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_during.txt" || true
kubectl get events -A --sort-by=.metadata.creationTimestamp > "${RUN_DIR}/events_during.txt" || true

log "Fault phase running for ${FAULT_SECONDS}s"
sleep "${FAULT_SECONDS}"

log "Starting ${SERVICE_NAME} on ${TARGET_NODE}"
date -Is > "${RUN_DIR}/recovery_command_time.txt"

{
  echo "recovery_command_start=$(date -Is)"
  ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl start ${SERVICE_NAME}"
  echo "recovery_command_finished=$(date -Is)"
} > "${RUN_DIR}/recovery_command.log" 2>&1

log "Waiting for target service to become active"
SERVICE_RECOVERY_RECORDED="false"
for _ in $(seq 1 180); do
  if ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl is-active ${SERVICE_NAME}" >/dev/null 2>&1; then
    date -Is > "${RUN_DIR}/service_recovery_time.txt"
    SERVICE_RECOVERY_RECORDED="true"
    log "Service active again"
    break
  fi
  sleep 1
done

if [[ "${SERVICE_RECOVERY_RECORDED}" != "true" ]]; then
  echo "Service did not become active within 180s" > "${RUN_DIR}/service_recovery_time.txt"
  log "WARNING: service recovery not detected within 180s"
fi

log "Waiting for Kubernetes node ${TARGET_NODE} to be Ready"
NODE_RECOVERY_RECORDED="false"
for _ in $(seq 1 300); do
  READY_STATUS="$(
    kubectl get node "${TARGET_NODE}" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown"
  )"
  if [[ "${READY_STATUS}" == "True" ]]; then
    date -Is > "${RUN_DIR}/node_recovery_time.txt"
    NODE_RECOVERY_RECORDED="true"
    log "Node ${TARGET_NODE} is Ready"
    break
  fi
  sleep 1
done

if [[ "${NODE_RECOVERY_RECORDED}" != "true" ]]; then
  echo "Node did not become Ready within 300s" > "${RUN_DIR}/node_recovery_time.txt"
  log "WARNING: node recovery not detected within 300s"
fi

log "Post-fault phase running for ${POST_SECONDS}s"
sleep "${POST_SECONDS}"

log "Capturing cluster state after recovery"
kubectl get nodes -o wide > "${RUN_DIR}/nodes_after.txt" || true
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_after.txt" || true
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_after.txt" || true
kubectl get events -A --sort-by=.metadata.creationTimestamp > "${RUN_DIR}/events_after.txt" || true

ssh "kim@${TARGET_IP}" "sudo -n /usr/bin/systemctl status ${SERVICE_NAME} --no-pager" > "${RUN_DIR}/service_status_after.txt" 2>&1 || true

date -Is > "${RUN_DIR}/test_end_time.txt"

log "Waiting for request monitor to finish"
wait "${MONITOR_PID}" || true
trap - INT TERM

date -Is > "${RUN_DIR}/monitor_end_time.txt"

log "Computing run summary"
python3 - <<PY > "${RUN_DIR}/summary.txt"
import csv
from pathlib import Path
from datetime import datetime
from statistics import median, mean

base = Path("${RUN_DIR}")

def read_time(name):
    p = base / name
    if not p.exists():
        return None
    text = p.read_text().strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None

def pct(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    k = (len(vals)-1) * p / 100
    f = int(k)
    c = min(f + 1, len(vals)-1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c] - vals[f]) * (k - f)

rows = []
req = base / "requests.csv"
if req.exists():
    with req.open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "success": str(r.get("success", "")).lower() == "true",
                    "ms": float(r.get("duration_ms", "")),
                    "error": r.get("error", ""),
                })
            except ValueError:
                rows.append({
                    "success": str(r.get("success", "")).lower() == "true",
                    "ms": None,
                    "error": r.get("error", ""),
                })

total = len(rows)
success = sum(1 for r in rows if r["success"])
failed = total - success
vals = [r["ms"] for r in rows if r["ms"] is not None]

fault = read_time("fault_time.txt")
service_rec = read_time("service_recovery_time.txt")
node_rec = read_time("node_recovery_time.txt")

print("=== Run summary ===")
print(f"scenario=${SCENARIO}")
print(f"target_node=${TARGET_NODE}")
print(f"target_ip=${TARGET_IP}")
print(f"service=${SERVICE_NAME}")
print(f"requests_total={total}")
print(f"success={success}")
print(f"failed={failed}")
print(f"success_rate_pct={(success / total * 100) if total else 0:.2f}")
print(f"error_rate_pct={(failed / total * 100) if total else 0:.2f}")
if vals:
    print(f"avg_ms={mean(vals):.2f}")
    print(f"median_ms={median(vals):.2f}")
    print(f"p95_ms={pct(vals, 95):.2f}")
    print(f"min_ms={min(vals):.2f}")
    print(f"max_ms={max(vals):.2f}")
else:
    print("latency_values=NA")

if fault and service_rec:
    print(f"service_recovery_seconds={(service_rec - fault).total_seconds():.2f}")
else:
    print("service_recovery_seconds=NA")

if fault and node_rec:
    print(f"node_recovery_seconds={(node_rec - fault).total_seconds():.2f}")
else:
    print("node_recovery_seconds=NA")
PY

cat "${RUN_DIR}/summary.txt"

log "Run finished: ${RUN_DIR}"
