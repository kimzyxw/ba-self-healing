#!/usr/bin/env bash
set -euo pipefail

# Run multiple KubeEdge node/component failure tests.
#
# Usage:
#   ./experiments/kubeedge/scripts/run_node_failure_scenario_async.sh edge
#   ./experiments/kubeedge/scripts/run_node_failure_scenario_async.sh cloud
#
# Optional environment variables:
#   RUNS=10
#   START_RUN=1
#   SLEEP_BETWEEN_RUNS=60
#   PRE_SECONDS=180
#   FAULT_SECONDS=300
#   POST_SECONDS=180

SCENARIO="${1:?Usage: $0 <edge|cloud>}"

RUNS="${RUNS:-10}"
START_RUN="${START_RUN:-1}"
SLEEP_BETWEEN_RUNS="${SLEEP_BETWEEN_RUNS:-60}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SINGLE_RUN_SCRIPT="${SCRIPT_DIR}/run_node_failure_test_async.sh"

case "${SCENARIO}" in
  edge)
    BASE_DIR="${REPO_ROOT}/experiments/kubeedge/node-failure/edge"
    SERVICE_NAME="edgecore.service"
    TARGETS=("e1:10.10.20.131" "e2:10.10.20.132")
    ;;
  cloud)
    BASE_DIR="${REPO_ROOT}/experiments/kubeedge/node-failure/cloud"
    SERVICE_NAME="k3s.service"
    TARGETS=("c2:10.10.10.134" "c3:10.10.10.135")
    ;;
  *)
    echo "ERROR: unsupported scenario '${SCENARIO}'. Use edge or cloud."
    exit 1
    ;;
esac

mkdir -p "${BASE_DIR}"

LOG="${BASE_DIR}/scenario-run.log"

echo "KubeEdge node failure scenario '${SCENARIO}' started at $(date -Is)" | tee -a "${LOG}"
echo "Base directory: ${BASE_DIR}" | tee -a "${LOG}"
echo "Runs: ${RUNS}" | tee -a "${LOG}"
echo "Start run: ${START_RUN}" | tee -a "${LOG}"
echo "Sleep between runs: ${SLEEP_BETWEEN_RUNS}s" | tee -a "${LOG}"
echo "Service: ${SERVICE_NAME}" | tee -a "${LOG}"

for i in $(seq "${START_RUN}" $((START_RUN + RUNS - 1))); do
  idx=$(( (i - START_RUN) % ${#TARGETS[@]} ))
  target="${TARGETS[$idx]}"
  TARGET_NODE="${target%%:*}"
  TARGET_IP="${target##*:}"

  RUN_NAME="$(printf "run-%02d-%s" "${i}" "${TARGET_NODE}")"
  RUN_DIR="${BASE_DIR}/${RUN_NAME}"

  if [[ -e "${RUN_DIR}" ]]; then
    echo "ERROR: ${RUN_DIR} already exists. Refusing to overwrite existing run data." | tee -a "${LOG}"
    exit 1
  fi

  echo "==================================================" | tee -a "${LOG}"
  echo "Starting ${SCENARIO} ${RUN_NAME} at $(date -Is)" | tee -a "${LOG}"
  echo "Target: ${TARGET_NODE} (${TARGET_IP})" | tee -a "${LOG}"
  echo "==================================================" | tee -a "${LOG}"

  "${SINGLE_RUN_SCRIPT}" \
    "${SCENARIO}" \
    "${TARGET_NODE}" \
    "${TARGET_IP}" \
    "${SERVICE_NAME}" \
    "${RUN_DIR}" 2>&1 | tee -a "${LOG}"

  echo "Finished ${SCENARIO} ${RUN_NAME} at $(date -Is)" | tee -a "${LOG}"

  if [[ "${i}" -lt $((START_RUN + RUNS - 1)) ]]; then
    echo "Waiting ${SLEEP_BETWEEN_RUNS}s before next run..." | tee -a "${LOG}"
    sleep "${SLEEP_BETWEEN_RUNS}"
  fi
done

echo "KubeEdge node failure scenario '${SCENARIO}' finished at $(date -Is)" | tee -a "${LOG}"
