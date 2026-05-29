# K3s Worker Node Failure Experiment

## Ziel

Messung des Self-Healing- und Recovery-Verhaltens von K3s bei Ausfall eines Worker-Nodes.

Während jedes Testlaufs wurde eine Worker-VM in VMware Fusion manuell ausgeschaltet und anschließend wieder gestartet. Parallel wurde die Erreichbarkeit der NGINX-Testanwendung über ein kontinuierliches Request-Monitoring gemessen.

## Voraussetzungen

- K3s-Cluster betriebsbereit
- Namespace `testapp` vorhanden
- Deployment `nginx-test` mit 3 Replikaten vorhanden
- Service der Testanwendung über NodePort erreichbar
- `request_monitor.py` vorhanden
- Zugriff auf VMware Fusion zum manuellen Ausschalten und Starten der VM

## Durchführung eines Testlaufs

### 1. Testordner anlegen

```bash
RUN=01
NODE=k3s-w2
BASE=~/ba-self-healing/experiments/k3s/node-failure/worker/run-$RUN-$NODE
mkdir -p $BASE

date -Is | tee $BASE/test_start_time.txt
echo "$NODE" | tee $BASE/failed_node.txt
echo "VM manually powered off in VMware Fusion and manually restarted" | tee $BASE/fault_method.txt

kubectl get nodes -o wide > $BASE/nodes_before.txt
kubectl get pods -n testapp -o wide > $BASE/pods_before.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_before.txt

### 2. Request-Monitor starten

BASE=~/ba-self-healing/experiments/k3s/node-failure/worker/run-01-k3s-w2

python3 ~/ba-self-healing/experiments/k3s/scripts/request_monitor.py \
  --url http://192.168.228.129:30243 \
  --output $BASE/requests.csv \
  --interval 1 \
  --timeout 2

### 3. Fehlerzeitpunkt speichern

date -Is | tee $BASE/fault_time.txt

### 4. Worker-Node-Ausfall erzeugen

Die jeweilige Worker-VM wird in VMware Fusion manuell ausgeschaltet.

### 5. Zustand wählrend des Ausfalls erfassen

Sobald der betroffene Node als NotReady angezeigt wird:

kubectl get nodes -o wide > $BASE/nodes_during.txt
kubectl get pods -n testapp -o wide > $BASE/pods_during.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_during.txt

### 6. VM/Node manuell wieder starten

### 7. Testergebnis speichern

kubectl get nodes -o wide > $BASE/nodes_after.txt
kubectl get pods -n testapp -o wide > $BASE/pods_after.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_after.txt

date -Is | tee $BASE/test_end_time.txt

### 8. Request Monitor stoppen

Ctrl+C

### 9. Vollständigkeit prüfen

ls -lh $BASE

Erwartete Dateien:
test_start_time.txt
fault_time.txt
test_end_time.txt
failed_node.txt
fault_method.txt
nodes_before.txt
nodes_during.txt
nodes_after.txt
pods_before.txt
pods_during.txt
pods_after.txt
events_before.txt
events_during.txt
events_after.txt
requests.csv

### Wiederholungen

Für die Worker-Node-Ausfalltests wurden 10 Testläufe durchgeführt.
Run 01 wurde mit k3s-w1 durchgeführt. Auf diesem Node befand sich zum Zeitpunkt des Ausfalls kein Pod der Testanwendung. Die Runs 02 bis 10 wurden mit k3s-w2 durchgeführt, da dort während der Versuchsphase jeweils ein Pod der Testanwendung lief.

### Beobachtung zum Pod-Status

Während der Worker-Node-Ausfalltests konnte beobachtet werden, dass Pods auf einem betroffenen Node im Kubernetes-Status weiterhin als Running angezeigt werden konnten, obwohl der Node bereits NotReady war. Der Pod-Status beschreibt in dieser Phase den zuletzt bekannten Zustand im Kubernetes-API-Server und entspricht nicht zwingend dem tatsächlich ausführbaren Zustand des Containers auf dem ausgeschalteten Node.
Aus diesem Grund wurde die Service-Verfügbarkeit primär über das Request-Monitoring bewertet. Node- und Pod-Zustände sowie Kubernetes-Events wurden ergänzend zur Interpretation des internen Clusterverhaltens verwendet.
Validierung der Messdaten

Nach Abschluss der Testläufe wurde geprüft, ob alle erwarteten Dateien vorhanden sind und ob für jeden Lauf eine requests.csv erzeugt wurde.

for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/node-failure/worker/run-$i-k3s-w*
  echo "=== worker run-$i ==="
  ls $BASE/requests.csv \
     $BASE/fault_time.txt \
     $BASE/test_start_time.txt \
     $BASE/test_end_time.txt \
     $BASE/nodes_before.txt \
     $BASE/nodes_during.txt \
     $BASE/nodes_after.txt \
     $BASE/pods_before.txt \
     $BASE/pods_during.txt \
     $BASE/pods_after.txt >/dev/null && echo "OK files"
  tail -n +2 $BASE/requests.csv | wc -l
done

Zusätzlich wurde die Anzahl erfolgreicher und fehlgeschlagener Requests geprüft:

for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/node-failure/worker/run-$i-k3s-w*
  echo "=== worker run-$i ==="
  awk -F',' 'NR>1 {total++; if ($4=="True") ok++; else fail++}
  END {print "total="total, "ok="ok, "fail="fail}' $BASE/requests.csv
done

## Hinweis zu Run 01

Run 01 wurde mit `k3s-w1` durchgeführt. Auf diesem Node befand sich zum Zeitpunkt des Ausfalls kein Pod der Testanwendung. Außerdem wurden für diesen ersten Lauf keine separaten `nodes_during.txt`- und `pods_during.txt`-Dateien gespeichert. Der Lauf wird daher primär zur Beobachtung der Node-Status-Recovery verwendet und nicht als gleichwertiger Workload-Recovery-Lauf interpretiert.
