# K3s Pod Failure Experiment

## Ziel

Messung des Self-Healing-Verhaltens von K3s bei einem einzelnen Pod-Ausfall.

Während jedes Testlaufs wird ein laufender Pod der Testanwendung gelöscht. Anschließend wird beobachtet, wie schnell Kubernetes einen Ersatz-Pod erstellt und die gewünschte Replikazahl wiederherstellt.

## Voraussetzungen

* K3s-Cluster betriebsbereit
* Namespace `testapp` vorhanden
* Deployment `nginx-test` mit 3 Replikaten vorhanden
* Service der Testanwendung erreichbar
* `request_monitor.py` vorhanden

## Durchführung eines Testlaufs

### 1. Testordner anlegen

```bash
RUN=01
BASE=~/ba-self-healing/experiments/k3s/pod-failure/run-$RUN
mkdir -p $BASE

date -Is | tee $BASE/test_start_time.txt

kubectl get nodes -o wide > $BASE/nodes_before.txt
kubectl get pods -n testapp -o wide > $BASE/pods_before.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_before.txt
```

### 2. Request-Monitor starten

```bash
BASE=~/ba-self-healing/experiments/k3s/pod-failure/run-01

python3 ~/ba-self-healing/experiments/k3s/scripts/request_monitor.py \
  --url http://192.168.228.129:30243 \
  --output $BASE/requests.csv \
  --interval 1 \
  --timeout 2
```

### 3. Baseline erfassen

Ca. 30 Sekunden warten.

### 4. Pod-Ausfall erzeugen

Aktuelle Pods anzeigen:

```bash
kubectl get pods -n testapp -o wide
```

Fehlerzeitpunkt speichern:

```bash
date -Is | tee $BASE/fault_time.txt
```

Pod löschen:

```bash
kubectl delete pod -n testapp <POD_NAME>
```

### 5. Recovery beobachten

```bash
kubectl get pods -n testapp -o wide
```

Warten bis wieder drei Pods im Status `Running` vorhanden sind.

### 6. Nachlauf erfassen

Nach erfolgreicher Wiederherstellung weitere ca. 60 Sekunden messen.

### 7. Testergebnis speichern

```bash
kubectl get nodes -o wide > $BASE/nodes_after.txt
kubectl get pods -n testapp -o wide > $BASE/pods_after.txt
kubectl get events -A --sort-by=.metadata.creationTimestamp > $BASE/events_after.txt

date -Is | tee $BASE/test_end_time.txt
```

### 8. Request-Monitor stoppen

```text
Ctrl+C
```

### 9. Vollständigkeit prüfen

```bash
ls -lh $BASE
```

Erwartete Dateien:

* test_start_time.txt
* fault_time.txt
* test_end_time.txt
* nodes_before.txt
* nodes_after.txt
* pods_before.txt
* pods_after.txt
* events_before.txt
* events_after.txt
* requests.csv

## Wiederholungen

Für die Bachelorarbeit wurden 10 unabhängige Testläufe durchgeführt.

Hierfür wird lediglich die Variable `RUN` angepasst:

```bash
RUN=02
RUN=03
...
RUN=10
```
