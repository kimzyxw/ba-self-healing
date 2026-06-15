#!/usr/bin/env bash
set -euo pipefail

# Single KubeEdge pod failure test run.
#
# The script starts the async request monitor, waits for a short pre-fault phase,
# deletes one nginx-testapp pod, and continues monitoring during the post-fault phase.
#
# Default endpoint:
#   http://10.10.20.131:30080
#
# Usage example:
#   ./experiments/kubeedge/scripts/run_pod_failure_test_async.sh \
#     experiments/kubeedge/pod-failure/run-01

RUN_DIR="${1:?Usage: $0 <run-dir>}"

URL="${URL:-http://10.10.20.131:30080}"
NAMESPACE="${NAMESPACE:-testapp}"
APP_LABEL="${APP_LABEL:-nginx-testapp}"

PRE_SECONDS="${PRE_SECONDS:-60}"
POST_SECONDS="${POST_SECONDS:-120}"
INTERVAL="${INTERVAL:-1}"
TIMEOUT="${TIMEOUT:-2}"
MAX_IN_FLIGHT="${MAX_IN_FLIGHT:-10}"

TOTAL_DURATION=$((PRE_SECONDS + POST_SECONDS))

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
MONITOR_SCRIPT="${SCRIPT_DIR}/request_monitor_async.py"

mkdir -p "${RUN_DIR}"

echo "KubeEdge pod failure test"
echo "Run directory: ${RUN_DIR}"
echo "URL: ${URL}"
echo "Namespace: ${NAMESPACE}"
echo "App label: ${APP_LABEL}"
echo "Pre-fault seconds: ${PRE_SECONDS}"
echo "Post-fault seconds: ${POST_SECONDS}"
echo "Total monitor duration: ${TOTAL_DURATION}"
echo "Max in flight: ${MAX_IN_FLIGHT}"

date --iso-8601=seconds > "${RUN_DIR}/test_start_time.txt"

kubectl get nodes -o wide > "${RUN_DIR}/nodes_before.txt"
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_before.txt"
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_before.txt"
kubectl get events -n "${NAMESPACE}" --sort-by=.lastTimestamp > "${RUN_DIR}/events_before.txt" || true

echo "${URL}" > "${RUN_DIR}/url.txt"
echo "${PRE_SECONDS}" > "${RUN_DIR}/pre_seconds.txt"
echo "${POST_SECONDS}" > "${RUN_DIR}/post_seconds.txt"
echo "${MAX_IN_FLIGHT}" > "${RUN_DIR}/max_in_flight.txt"

echo "Starting request monitor..."
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
    echo "Stopping request monitor..."
    kill "${MONITOR_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup INT TERM

echo "Waiting ${PRE_SECONDS}s before deleting pod..."
sleep "${PRE_SECONDS}"

POD_TO_DELETE="$(
  kubectl get pods -n "${NAMESPACE}" \
    -l app="${APP_LABEL}" \
    --field-selector=status.phase=Running \
    -o jsonpath='{.items[0].metadata.name}'
)"

if [[ -z "${POD_TO_DELETE}" ]]; then
  echo "No running pod found for app=${APP_LABEL} in namespace=${NAMESPACE}" | tee "${RUN_DIR}/error.txt"
  exit 1
fi

echo "${POD_TO_DELETE}" > "${RUN_DIR}/deleted_pod.txt"
date --iso-8601=seconds > "${RUN_DIR}/fault_time.txt"

echo "Deleting pod: ${POD_TO_DELETE}"
kubectl delete pod "${POD_TO_DELETE}" -n "${NAMESPACE}" --wait=false

echo "Waiting for recovery to 3 ready non-terminating pods..."
RECOVERY_RECORDED="false"

for _ in $(seq 1 "${POST_SECONDS}"); do
  READY_COUNT="$(
    kubectl get pods -n "${NAMESPACE}" -l app="${APP_LABEL}" -o json \
      | python3 -c '
import json, sys
data = json.load(sys.stdin)
count = 0
for item in data.get("items", []):
    if item.get("metadata", {}).get("deletionTimestamp") is not None:
        continue
    statuses = item.get("status", {}).get("containerStatuses", [])
    if statuses and statuses[0].get("ready") is True:
        count += 1
print(count)
'
  )"

  NON_TERMINATING_COUNT="$(
    kubectl get pods -n "${NAMESPACE}" -l app="${APP_LABEL}" -o json \
      | python3 -c '
import json, sys
data = json.load(sys.stdin)
count = 0
for item in data.get("items", []):
    if item.get("metadata", {}).get("deletionTimestamp") is None:
        count += 1
print(count)
'
  )"

  if [[ "${READY_COUNT}" -ge 3 && "${NON_TERMINATING_COUNT}" -ge 3 ]]; then
    date --iso-8601=seconds > "${RUN_DIR}/recovery_time.txt"
    RECOVERY_RECORDED="true"
    echo "Recovery detected: ${READY_COUNT} ready non-terminating pods."
    break
  fi

  sleep 1
done

if [[ "${RECOVERY_RECORDED}" != "true" ]]; then
  echo "Recovery not detected during post-fault phase." > "${RUN_DIR}/recovery_time.txt"
fi

echo "Waiting for request monitor to finish..."
wait "${MONITOR_PID}"
trap - INT TERM

date --iso-8601=seconds > "${RUN_DIR}/test_end_time.txt"

kubectl get nodes -o wide > "${RUN_DIR}/nodes_after.txt"
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_after.txt"
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_after.txt"
kubectl get events -n "${NAMESPACE}" --sort-by=.lastTimestamp > "${RUN_DIR}/events_after.txt" || true

echo "Run finished."
echo "Results written to: ${RUN_DIR}"
