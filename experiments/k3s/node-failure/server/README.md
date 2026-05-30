# K3s Server-Node-Ausfalltests

## Ziel

Untersuchung des Verhaltens eines hochverfügbaren K3s-Clusters bei Ausfällen von Control-Plane-Knoten.

Der betroffene Server-Knoten wird in VMware Fusion manuell ausgeschaltet und nach etwa zwei Minuten wieder gestartet. Während des gesamten Versuchs werden kontinuierlich HTTP-Anfragen an die Testanwendung gesendet.

Falls der Knoten nach dem Neustart nicht selbstständig wieder in den Zustand `Ready` zurückkehrt, werden Diagnoseinformationen gesammelt und der K3s-Dienst manuell neu gestartet.

---

## Versuchsaufbau

Die einzelnen Durchläufe werden gespeichert als:

```text
run-01-k3s-s2
run-02-k3s-s3
...
run-10-k3s-s3
```

Jeder Durchlauf enthält:

* Zustand der Nodes vor, während und nach dem Ausfall
* Zustand der Pods vor, während und nach dem Ausfall
* Kubernetes-Events
* Ergebnisse des Request-Monitors
* Zeitpunkte des Ausfalls und der Wiederherstellung
* Informationen zu manuellen Eingriffen
* K3s-Logs und Statusinformationen zur Fehleranalyse

---

## Versuch starten

Beispiel für Run 01:

```bash
RUN=01
NODE=k3s-s2

BASE=~/ba-self-healing/experiments/k3s/node-failure/server/run-$RUN-$NODE
mkdir -p $BASE

date -Is | tee $BASE/test_start_time.txt
echo "$NODE" | tee $BASE/failed_node.txt
echo "VM manually powered off in VMware Fusion and manually restarted" | tee $BASE/fault_method.txt

kubectl get nodes -o wide > $BASE/nodes_before.txt
kubectl get pods -A -o wide > $BASE/pods_before.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_before.txt
```

---

## Request-Monitor starten

```bash
BASE=~/ba-self-healing/experiments/k3s/node-failure/server/run-01-k3s-s2

python3 ~/ba-self-healing/experiments/k3s/scripts/request_monitor.py \
  --url http://192.168.228.129:30243 \
  --output $BASE/requests.csv \
  --interval 1 \
  --timeout 2
```

---

## Ausfall auslösen

Nach etwa 30 Sekunden:

```bash
date -Is | tee $BASE/fault_time.txt
```

Anschließend die ausgewählte Server-VM in VMware Fusion ausschalten.

---

## Zustand während des Ausfalls erfassen

Sobald der Knoten den Zustand `NotReady` erreicht:

```bash
kubectl get nodes -o wide > $BASE/nodes_during.txt
kubectl get pods -A -o wide > $BASE/pods_during.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_during.txt
```

---

## Fehlgeschlagene Wiederherstellung dokumentieren

Falls der Knoten mehr als zwei Minuten nach dem Neustart weiterhin `NotReady` ist:

```bash
kubectl get nodes -o wide > $BASE/nodes_still_notready.txt
kubectl get pods -A -o wide > $BASE/pods_still_notready.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_still_notready.txt

date -Is | tee $BASE/still_notready_time.txt
```

---

## Diagnoseinformationen sammeln

Beispiel für k3s-s2:

```bash
ssh kim@192.168.228.130

sudo systemctl status k3s --no-pager > ~/k3s-status-run-01-server-s2.txt

sudo journalctl -u k3s \
  --since "15 minutes ago" \
  --no-pager > ~/k3s-run-01-server-s2.log
```

---

## Manuelle Wiederherstellung

```bash
sudo systemctl restart k3s
```

Manuellen Eingriff dokumentieren:

```bash
echo "sudo systemctl restart k3s on k3s-s2" \
  | tee $BASE/manual_intervention.txt

date -Is | tee $BASE/manual_intervention_time.txt
```

Logs kopieren:

```bash
scp kim@192.168.228.130:~/k3s-run-01-server-s2.log $BASE/
scp kim@192.168.228.130:~/k3s-status-run-01-server-s2.txt $BASE/
```

---

## Versuch abschließen

Nachdem der Knoten wieder den Zustand `Ready` erreicht hat:

```bash
kubectl get nodes -o wide > $BASE/nodes_after.txt
kubectl get pods -A -o wide > $BASE/pods_after.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_after.txt

date -Is | tee $BASE/test_end_time.txt
```

Den Request-Monitor mit

```text
Ctrl+C
```

beenden.

Anschließend prüfen:

```bash
ls -lh $BASE
```

---

## Validierung

Prüfen, ob alle benötigten Dateien vorhanden sind:

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/node-failure/server/run-$i-*

  echo "=== run-$i ==="

  ls $BASE/requests.csv \
     $BASE/fault_time.txt \
     $BASE/test_start_time.txt \
     $BASE/test_end_time.txt \
     $BASE/nodes_before.txt \
     $BASE/nodes_after.txt \
     $BASE/pods_before.txt \
     $BASE/pods_after.txt >/dev/null && echo "OK Dateien"
done
```

Anzahl erfolgreicher und fehlgeschlagener Requests auswerten:

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/node-failure/server/run-$i-*

  echo "=== run-$i ==="

  awk -F',' '
  NR>1 {
    total++;
    if ($4=="True") ok++;
    else fail++;
  }
  END {
    print "total="total, "ok="ok, "fail="fail
  }' $BASE/requests.csv
done
```

## Beobachtung

In allen zehn Durchläufen kehrte der ausgefallene Server-Knoten nach dem Neustart der VM nicht selbstständig in den Zustand `Ready` zurück. Erst nach einem manuellen Neustart des K3s-Dienstes mittels `sudo systemctl restart k3s` wurde der Knoten wieder korrekt in den Cluster eingebunden.

Dieses Verhalten wurde konsistent bei den Ausfällen von `k3s-s2` und `k3s-s3` beobachtet.
