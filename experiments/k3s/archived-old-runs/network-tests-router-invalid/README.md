# Verworfenes Testszenario: Latenzsimulation über Router-VM

## Ziel

Ziel des Tests war die Untersuchung des Verhaltens eines hochverfügbaren K3s-Clusters unter erhöhter Netzwerkverzögerung. Die Latenz sollte mithilfe von `tc netem` auf einer dedizierten Router-VM simuliert werden. Das Testszenario orientierte sich an dem in der Vorarbeit von Sebastian Heiden beschriebenen Ansatz, bei dem Netzwerkstörungen zentral über eine Router- bzw. Bridge-VM erzeugt werden.

## Testaufbau

Der Cluster bestand aus drei Server-Knoten (`k3s-s1` bis `k3s-s3`) und zwei Worker-Knoten (`k3s-w1`, `k3s-w2`). Zusätzlich wurde eine Router-VM betrieben.

Alle Knoten befanden sich im VMware-Netzwerk `192.168.228.0/24`. Die Testanwendung wurde über einen Kubernetes NodePort bereitgestellt und mittels eines Python-Monitoringskripts kontinuierlich abgefragt.

Die Latenz wurde auf der Router-VM mittels `tc netem delay` auf dem Interface `ens256` erzeugt.

## Durchgeführte Tests

Es wurden zehn vollständige Testläufe des Szenarios `latency-1s-30min` durchgeführt.

Jeder Testlauf bestand aus:

* 5 Minuten Baseline-Messung
* 30 Minuten simulierte Latenz
* 5 Minuten Nachlauf

Die Störung wurde erfolgreich auf der Router-VM gesetzt und nach Ablauf des Zeitfensters wieder entfernt. Sämtliche Messdaten wurden vollständig aufgezeichnet.

## Beobachtungen

Alle zehn Testläufe wurden technisch erfolgreich abgeschlossen.

Die Auswertung zeigte:

* Alle Testdateien wurden erzeugt.
* Pro Durchlauf wurden ca. 2400 HTTP-Anfragen aufgezeichnet.
* Es traten keine fehlgeschlagenen Requests auf.
* Kein Cluster-Knoten wechselte in den Status `NotReady`.
* Die gemessenen Antwortzeiten lagen weiterhin im Bereich von wenigen Millisekunden.

Die erwartete zusätzliche Latenz von einer Sekunde konnte in den Messdaten nicht beobachtet werden.

## Ursachenanalyse

Zur Validierung wurde die Latenz manuell auf der Router-VM aktiviert und anschließend ein direkter HTTP-Test durchgeführt.

Trotz aktivierter Latenz betrug die gemessene Antwortzeit weiterhin nur wenige Millisekunden.

Eine Analyse der Netzwerktopologie ergab, dass sich sowohl die K3s-Knoten als auch der Hostsystem-Zugriff im selben VMware-Bridge-Netz (`192.168.228.0/24`) befanden.

Dadurch wurde der Netzwerkverkehr direkt zwischen den beteiligten Systemen übertragen, ohne die Router-VM zu durchlaufen. Die auf der Router-VM konfigurierte Latenz beeinflusste den tatsächlich genutzten Kommunikationspfad daher nicht.

## Bewertung

Die Testdurchführung selbst war erfolgreich und reproduzierbar. Die erzeugte Netzwerkstörung wirkte jedoch nicht auf den gemessenen Datenpfad.

Die Messergebnisse erlauben daher keine Aussage über das Verhalten des Clusters unter erhöhter Netzwerklatenz.

Aus diesem Grund werden die Ergebnisse dieses Testblocks nicht in die spätere Evaluation übernommen und als verworfener Vorversuch archiviert.

## Konsequenzen für die weiteren Versuche

Für die Wiederholung der Netzwerktests sind Anpassungen der Netzwerktopologie erforderlich, also der Neuaufbau des Clusters in einer Architektur, bei der der relevante Datenverkehr zwingend über die Router-VM geleitet wird.

# ursprünglich geplantes Szenario: K3s – Latenztests

## Vorbedingungen

Vor Beginn der Latenztests:

- Alle Nodes im Status `Ready`
- Testanwendung erreichbar
- 20 erfolgreiche Requests in Folge auf die Test-URL
- Keine aktiven `tc netem`-Regeln auf dem Router

## Ziel

Untersuchung des Verhaltens eines K3s-Clusters unter künstlich erhöhter Netzwerklatenz.

Die Latenz wird mittels `tc netem` auf der Router-VM simuliert. Während der Tests werden kontinuierlich HTTP-Anfragen an die Testanwendung gesendet und die Antwortzeiten sowie mögliche Ausfälle aufgezeichnet.

---

## Testaufbau

### Cluster

- 3 Server-Nodes
  - k3s-s1
  - k3s-s2
  - k3s-s3

- 2 Worker-Nodes
  - k3s-w1
  - k3s-w2

### Router

- Router-VM zwischen Cluster und externem Netzwerk
- Simulation der Latenz mit Linux Traffic Control (`tc netem`)

### Testanwendung

Namespace:

```bash
testapp
```

Service:

```bash
nginx-service
```

NodePort:

```bash
30243
```

Test-URL:

```bash
http://192.168.228.130:30243
```

---

## Durchführung

Jeder Testlauf besteht aus drei Phasen:

### 1. Baseline

Dauer:

```text
5 Minuten
```

Normale Kommunikation ohne Störung.

### 2. Störungsphase

Dauer:

```text
30 Minuten
```

Simulation einer konstanten Netzwerklatenz.

### 3. Nachlaufphase

Dauer:

```text
5 Minuten
```

Beobachtung des Systems nach Entfernung der Störung.

Gesamtdauer pro Lauf:

```text
40 Minuten
```

---

## Getestete Szenarien

| Szenario | Latenz |
|-----------|---------|
| latency-100ms | 100 ms |
| latency-1s | 1 s |
| latency-1min | 1 min |
| latency-10min | 10 min |
| latency-30min | 30 min |

Für jedes Szenario werden 10 Durchläufe durchgeführt.

---

## Gespeicherte Daten

Jeder Testlauf erzeugt ein eigenes Verzeichnis.

Beispiel:

```text
network-tests/
└── latency-100ms/
    └── run-01-router/
```

Enthaltene Dateien:

```text
test_start_time.txt
fault_time.txt
recovery_time.txt
test_end_time.txt

nodes_before.txt
nodes_after.txt

pods_before.txt
pods_after.txt

events_before.txt
events_after.txt

requests.csv
```

---

## Validierung der Testläufe

### Vollständigkeit prüfen

```bash
cd ~/ba-self-healing/experiments/k3s

for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/network-tests/latency-100ms/run-$i-router

  echo "=== run-$i ==="

  ls \
    $BASE/test_start_time.txt \
    $BASE/fault_time.txt \
    $BASE/recovery_time.txt \
    $BASE/test_end_time.txt \
    $BASE/requests.csv \
    $BASE/nodes_before.txt \
    $BASE/nodes_after.txt \
    $BASE/pods_before.txt \
    $BASE/pods_after.txt \
    $BASE/events_before.txt \
    $BASE/events_after.txt \
    >/dev/null && echo "OK files"
done
```

---

### Anzahl der Requests prüfen

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/network-tests/latency-100ms/run-$i-router

  echo "=== run-$i ==="

  tail -n +2 $BASE/requests.csv | wc -l
done
```

---

### Erfolgreiche und fehlgeschlagene Requests zählen

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do
  BASE=~/ba-self-healing/experiments/k3s/network-tests/latency-100ms/run-$i-router

  echo "=== run-$i ==="

  awk -F',' '
  NR>1 {
    total++;
    if ($4=="True")
      ok++;
    else
      fail++;
  }
  END {
    print "total="total, "ok="ok, "fail="fail
  }' $BASE/requests.csv
done
```

---

## Hinweise

Die künstliche Latenz wird auf der Router-VM mittels:

```bash
tc netem delay
```

erzeugt.

Nach jedem Testlauf wird die Konfiguration wieder entfernt, sodass der Router in seinen Ausgangszustand zurückkehrt.
