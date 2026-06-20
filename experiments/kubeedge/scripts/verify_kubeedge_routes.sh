#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-}"
if [ -z "$OUT_DIR" ]; then
  OUT_DIR="experiments/kubeedge/_route-preflight/$(date +%Y%m%d-%H%M%S)"
fi

mkdir -p "$OUT_DIR"

CLOUD_ROUTER_IP="10.10.10.136"
EDGE_ROUTER_IP="10.10.20.133"

C1_EDGE_IFACE="ens256"
E1_MGMT="172.16.41.146"
E2_MGMT="172.16.41.147"

C2_CLOUD="10.10.10.134"
C3_CLOUD="10.10.10.135"

E1_EDGE="10.10.20.131"
E2_EDGE="10.10.20.132"

{
  echo "===== KubeEdge Route Preflight ====="
  date -Is
  echo "out_dir=$OUT_DIR"
  echo "cloud_router_ip=$CLOUD_ROUTER_IP"
  echo "edge_router_ip=$EDGE_ROUTER_IP"
  echo
} | tee "$OUT_DIR/preflight.log"

echo "===== Set route on cloud nodes: Cloud -> Edge =====" | tee -a "$OUT_DIR/preflight.log"
sudo -n /usr/sbin/ip route replace 10.10.20.0/24 via "$CLOUD_ROUTER_IP" dev "$C1_EDGE_IFACE"
ssh "kim@$C2_CLOUD" "sudo -n /usr/sbin/ip route replace 10.10.20.0/24 via $CLOUD_ROUTER_IP dev ens256"
ssh "kim@$C3_CLOUD" "sudo -n /usr/sbin/ip route replace 10.10.20.0/24 via $CLOUD_ROUTER_IP dev ens256"

{
  echo
  echo "===== c1 routes ====="
  ip route
  echo
  echo "===== c1 route get edge nodes ====="
  ip route get "$E1_EDGE"
  ip route get "$E2_EDGE"

  echo
  echo "===== c2 route get edge nodes ====="
  ssh "kim@$C2_CLOUD" "hostname; ip route get $E1_EDGE; ip route get $E2_EDGE"

  echo
  echo "===== c3 route get edge nodes ====="
  ssh "kim@$C3_CLOUD" "hostname; ip route get $E1_EDGE; ip route get $E2_EDGE"
} | tee "$OUT_DIR/cloud_routes.txt"

echo "===== Set route on e1: Edge -> Cloud =====" | tee -a "$OUT_DIR/preflight.log"
ssh "kim@$E1_MGMT" "sudo -n /usr/sbin/ip route replace 10.10.10.0/24 via $EDGE_ROUTER_IP dev ens256"

echo "===== Set route on e2: Edge -> Cloud =====" | tee -a "$OUT_DIR/preflight.log"
ssh "kim@$E2_MGMT" "sudo -n /usr/sbin/ip route replace 10.10.10.0/24 via $EDGE_ROUTER_IP dev ens256"

{
  echo "===== e1 route get c1 ====="
  ssh "kim@$E1_MGMT" "hostname; ip route get 10.10.10.133; ip route"
  echo
  echo "===== e2 route get c1 ====="
  ssh "kim@$E2_MGMT" "hostname; ip route get 10.10.10.133; ip route"
} | tee "$OUT_DIR/edge_routes.txt"

{
  echo "===== Connectivity from c1 to edge nodes ====="
  ping -c 3 "$E1_EDGE"
  ping -c 3 "$E2_EDGE"

  nc -vz -w 3 "$E1_EDGE" 22
  nc -vz -w 3 "$E2_EDGE" 22
} | tee "$OUT_DIR/connectivity.txt"

{
  echo "===== NodePort from c1 ====="

  for url in \
    "http://$E1_EDGE:30080/" \
    "http://$E2_EDGE:30080/"
  do
    echo
    echo "----- $url -----"
    for i in {1..5}; do
      curl -sS -o /dev/null -w "code=%{http_code} time=%{time_total}\n" --max-time 5 "$url"
    done
  done
} | tee "$OUT_DIR/nodeport.txt"

{
  echo "===== Kubernetes state ====="
  kubectl get nodes -o wide
  echo
  kubectl get pods -n testapp -o wide
  echo
  kubectl get pods -n kubeedge -o wide
} | tee "$OUT_DIR/kubernetes_state.txt"

if grep -q "code=000" "$OUT_DIR/nodeport.txt"; then
  echo "Preflight FAILED: NodePort check failed" | tee -a "$OUT_DIR/preflight.log"
  exit 1
fi

echo "Preflight OK" | tee -a "$OUT_DIR/preflight.log"
