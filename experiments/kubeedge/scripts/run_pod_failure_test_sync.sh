#!/usr/bin/env bash
set -Eeuo pipefail

# Finaler synchroner KubeEdge-Pod-Ausfalltest.
#
# Methodik:
# - gleicher synchroner Request-Monitor wie bei K3s
# - 60 s Baseline
# - Löschen eines laufenden nginx-testapp-Pods
# - Recovery: drei Ready, nicht terminierende Ersatz-Replikate
# - 60 s Nachlauf ab dokumentierter Recovery
#
# Aufruf:
# ./experiments/kubeedge/scripts/run_pod_failure_test_sync.sh \
#   experiments/kubeedge/pod-failure/run-01

RUN_DIR="${1:?Usage: $0 <run-directory>}"

URL="${URL:-http://10.10.20.131:30080}"
NAMESPACE="${NAMESPACE:-testapp}"
APP_LABEL="${APP_LABEL:-nginx-testapp}"
EXPECTED_REPLICAS="${EXPECTED_REPLICAS:-3}"

PRE_SECONDS="${PRE_SECONDS:-60}"
POST_SECONDS="${POST_SECONDS:-60}"
RECOVERY_TIMEOUT_SECONDS="${RECOVERY_TIMEOUT_SECONDS:-120}"

INTERVAL="${INTERVAL:-1}"
TIMEOUT="${TIMEOUT:-2}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Derselbe synchrone Monitor wie in den K3s-Pod- und Node-Tests.
MONITOR_SCRIPT="${REPO_ROOT}/experiments/k3s/scripts/request_monitor.py"

MONITOR_PID=""
RUN_SUCCESS="false"

mkdir -p "${RUN_DIR}"

cleanup() {
  local exit_code=$?

  if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
    echo "Stopping synchronous request monitor ..."
    kill -TERM "${MONITOR_PID}" >/dev/null 2>&1 || true
    wait "${MONITOR_PID}" >/dev/null 2>&1 || true
  fi

  if [[ "${RUN_SUCCESS}" == "true" ]]; then
    echo "passed" > "${RUN_DIR}/run_status.txt"
  else
    echo "failed" > "${RUN_DIR}/run_status.txt"
  fi

  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

fail() {
  echo "$*" | tee "${RUN_DIR}/error.txt" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Required file not found: $1"
}

require_file "${MONITOR_SCRIPT}"

echo "=================================================="
echo "KubeEdge synchronous pod-failure test"
echo "Run directory:               ${RUN_DIR}"
echo "URL:                         ${URL}"
echo "Namespace:                   ${NAMESPACE}"
echo "Application label:           ${APP_LABEL}"
echo "Expected replicas:           ${EXPECTED_REPLICAS}"
echo "Baseline duration:           ${PRE_SECONDS} s"
echo "Post-recovery duration:      ${POST_SECONDS} s"
echo "Recovery timeout:            ${RECOVERY_TIMEOUT_SECONDS} s"
echo "Request interval:            ${INTERVAL} s"
echo "Request timeout:             ${TIMEOUT} s"
echo "=================================================="

date --iso-8601=seconds > "${RUN_DIR}/test_start_time.txt"

echo "${URL}" > "${RUN_DIR}/url.txt"
echo "${NAMESPACE}" > "${RUN_DIR}/namespace.txt"
echo "${APP_LABEL}" > "${RUN_DIR}/app_label.txt"
echo "${EXPECTED_REPLICAS}" > "${RUN_DIR}/expected_replicas.txt"
echo "${PRE_SECONDS}" > "${RUN_DIR}/pre_seconds.txt"
echo "${POST_SECONDS}" > "${RUN_DIR}/post_seconds.txt"
echo "${RECOVERY_TIMEOUT_SECONDS}" > "${RUN_DIR}/recovery_timeout_seconds.txt"
echo "${INTERVAL}" > "${RUN_DIR}/interval_seconds.txt"
echo "${TIMEOUT}" > "${RUN_DIR}/timeout_seconds.txt"
echo "${MONITOR_SCRIPT}" > "${RUN_DIR}/monitor_script.txt"

echo "Capturing baseline cluster state ..."
kubectl get nodes -o wide > "${RUN_DIR}/nodes_before.txt"
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_before.txt"
kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" -o yaml \
  > "${RUN_DIR}/deployment_before.yaml"
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp \
  > "${RUN_DIR}/events_before.txt"

READY_BEFORE="$(
  kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" \
    -o jsonpath='{.status.readyReplicas}'
)"
AVAILABLE_BEFORE="$(
  kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" \
    -o jsonpath='{.status.availableReplicas}'
)"

echo "${READY_BEFORE:-0}" > "${RUN_DIR}/ready_replicas_before.txt"
echo "${AVAILABLE_BEFORE:-0}" > "${RUN_DIR}/available_replicas_before.txt"

if [[ "${READY_BEFORE:-0}" != "${EXPECTED_REPLICAS}" ]] \
  || [[ "${AVAILABLE_BEFORE:-0}" != "${EXPECTED_REPLICAS}" ]]; then
  fail "Precondition failed: deployment does not have ${EXPECTED_REPLICAS} ready and available replicas."
fi

echo "Starting synchronous K3s-compatible request monitor ..."
date --iso-8601=seconds > "${RUN_DIR}/monitor_start_time.txt"

python3 "${MONITOR_SCRIPT}" \
  --url "${URL}" \
  --output "${RUN_DIR}/requests.csv" \
  --interval "${INTERVAL}" \
  --timeout "${TIMEOUT}" &
MONITOR_PID=$!

sleep 2

if ! kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
  fail "Request monitor exited unexpectedly."
fi

echo "Collecting baseline for ${PRE_SECONDS} seconds ..."
sleep "${PRE_SECONDS}"

POD_JSON="$(
  kubectl get pods -n "${NAMESPACE}" \
    -l "app=${APP_LABEL}" \
    -o json
)"

POD_TO_DELETE="$(
  printf '%s' "${POD_JSON}" | python3 -c '
import json
import sys

pods = json.load(sys.stdin).get("items", [])
candidates = []

for pod in pods:
    metadata = pod.get("metadata", {})
    status = pod.get("status", {})

    if metadata.get("deletionTimestamp") is not None:
        continue

    if status.get("phase") != "Running":
        continue

    containers = status.get("containerStatuses") or []
    if not containers or not all(c.get("ready") is True for c in containers):
        continue

    candidates.append((
        metadata.get("creationTimestamp", ""),
        metadata.get("name", "")
    ))

if not candidates:
    raise SystemExit(1)

candidates.sort()
print(candidates[0][1])
'
)" || fail "No fully Ready running pod found for deletion."

POD_NODE="$(
  kubectl get pod -n "${NAMESPACE}" "${POD_TO_DELETE}" \
    -o jsonpath='{.spec.nodeName}'
)"

echo "${POD_TO_DELETE}" > "${RUN_DIR}/deleted_pod.txt"
echo "${POD_NODE}" > "${RUN_DIR}/deleted_pod_node.txt"

echo "Deleting pod ${POD_TO_DELETE} on node ${POD_NODE} ..."
date --iso-8601=seconds > "${RUN_DIR}/fault_time.txt"

kubectl delete pod -n "${NAMESPACE}" "${POD_TO_DELETE}" \
  --wait=false \
  > "${RUN_DIR}/delete_command_output.txt"

echo "timestamp,ready_nonterminating,nonterminating,deleted_pod_nonterminating,replacement_pods" \
  > "${RUN_DIR}/recovery_observations.csv"

RECOVERY_DETECTED="false"

for _ in $(seq 1 "${RECOVERY_TIMEOUT_SECONDS}"); do
  NOW="$(date --iso-8601=seconds)"

  RECOVERY_JSON="${RUN_DIR}/recovery_state.json"

  kubectl get pods -n "${NAMESPACE}" \
    -l "app=${APP_LABEL}" \
    -o json > "${RECOVERY_JSON}"

  RECOVERY_STATE="$(
    python3 - "${RECOVERY_JSON}" "${POD_TO_DELETE}" <<'RECOVERY_PY'
import json
import sys

json_path = sys.argv[1]
deleted_pod = sys.argv[2]

with open(json_path, encoding="utf-8") as f:
    pods = json.load(f).get("items", [])

ready_nonterminating = 0
nonterminating = 0
deleted_pod_nonterminating = 0
replacement_pods = 0

for pod in pods:
    metadata = pod.get("metadata", {})
    status = pod.get("status", {})
    name = metadata.get("name", "")

    if metadata.get("deletionTimestamp") is not None:
        continue

    nonterminating += 1

    if name == deleted_pod:
        deleted_pod_nonterminating = 1
    else:
        replacement_pods += 1

    containers = status.get("containerStatuses") or []
    if containers and all(container.get("ready") is True for container in containers):
        ready_nonterminating += 1

print(
    f"{ready_nonterminating},"
    f"{nonterminating},"
    f"{deleted_pod_nonterminating},"
    f"{replacement_pods}"
)
RECOVERY_PY
  )"
  IFS=',' read -r READY_NONTERMINATING NONTERMINATING \
    DELETED_POD_NONTERMINATING REPLACEMENT_PODS <<< "${RECOVERY_STATE}"

  echo "${NOW},${READY_NONTERMINATING},${NONTERMINATING},${DELETED_POD_NONTERMINATING},${REPLACEMENT_PODS}" \
    >> "${RUN_DIR}/recovery_observations.csv"

  if [[ "${READY_NONTERMINATING}" -ge "${EXPECTED_REPLICAS}" ]] \
    && [[ "${NONTERMINATING}" -ge "${EXPECTED_REPLICAS}" ]] \
    && [[ "${DELETED_POD_NONTERMINATING}" == "0" ]] \
    && [[ "${REPLACEMENT_PODS}" -ge "${EXPECTED_REPLICAS}" ]]; then

    date --iso-8601=seconds > "${RUN_DIR}/recovery_time.txt"

    kubectl get pods -n "${NAMESPACE}" -o wide \
      > "${RUN_DIR}/pods_at_recovery.txt"

    kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" -o yaml \
      > "${RUN_DIR}/deployment_at_recovery.yaml"

    RECOVERY_DETECTED="true"
    break
  fi

  sleep 1
done

if [[ "${RECOVERY_DETECTED}" != "true" ]]; then
  date --iso-8601=seconds > "${RUN_DIR}/recovery_timeout_time.txt"

  kubectl get nodes -o wide > "${RUN_DIR}/nodes_at_recovery_timeout.txt"
  kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_at_recovery_timeout.txt"
  kubectl get events -A --sort-by=.metadata.creationTimestamp \
    > "${RUN_DIR}/events_at_recovery_timeout.txt"

  fail "Recovery criterion not reached within ${RECOVERY_TIMEOUT_SECONDS} seconds."
fi

python3 - \
  "$(cat "${RUN_DIR}/fault_time.txt")" \
  "$(cat "${RUN_DIR}/recovery_time.txt")" \
  > "${RUN_DIR}/pod_recovery_seconds.txt" <<'PY'
from datetime import datetime
import sys

fault = datetime.fromisoformat(sys.argv[1])
recovery = datetime.fromisoformat(sys.argv[2])

print(f"{(recovery - fault).total_seconds():.3f}")
PY

echo "Recovery detected after $(cat "${RUN_DIR}/pod_recovery_seconds.txt") seconds."
echo "Collecting ${POST_SECONDS} seconds of post-recovery monitoring ..."
sleep "${POST_SECONDS}"

echo "Capturing final cluster state ..."
kubectl get nodes -o wide > "${RUN_DIR}/nodes_after.txt"
kubectl get pods -n "${NAMESPACE}" -o wide > "${RUN_DIR}/pods_after.txt"
kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" -o yaml \
  > "${RUN_DIR}/deployment_after.yaml"
kubectl get pods -n kubeedge -o wide > "${RUN_DIR}/kubeedge_pods_after.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp \
  > "${RUN_DIR}/events_after.txt"

READY_AFTER="$(
  kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" \
    -o jsonpath='{.status.readyReplicas}'
)"
AVAILABLE_AFTER="$(
  kubectl get deployment -n "${NAMESPACE}" "${APP_LABEL}" \
    -o jsonpath='{.status.availableReplicas}'
)"

echo "${READY_AFTER:-0}" > "${RUN_DIR}/ready_replicas_after.txt"
echo "${AVAILABLE_AFTER:-0}" > "${RUN_DIR}/available_replicas_after.txt"

if [[ "${READY_AFTER:-0}" != "${EXPECTED_REPLICAS}" ]] \
  || [[ "${AVAILABLE_AFTER:-0}" != "${EXPECTED_REPLICAS}" ]]; then
  fail "Postcondition failed: deployment does not have ${EXPECTED_REPLICAS} ready and available replicas."
fi

date --iso-8601=seconds > "${RUN_DIR}/test_end_time.txt"

RUN_SUCCESS="true"

echo "Test completed successfully."
