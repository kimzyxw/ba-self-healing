# KubeEdge Pod Failure Experiment

## Ziel

Dieses Experiment untersucht das Self-Healing-Verhalten von KubeEdge beim Ausfall eines einzelnen Pods der Testanwendung.

In jedem Testlauf wurde ein laufender Pod des Deployments `nginx-testapp` im Namespace `testapp` gelöscht. Anschließend wurde gemessen, wie lange KubeEdge bzw. Kubernetes benötigt, bis wieder drei Pods der Testanwendung im Zustand `Running` und `1/1` Ready vorhanden sind. Parallel wurde die Erreichbarkeit der Anwendung über einen synchronen HTTP-Request-Monitor gemessen.

Die Durchführung ist möglichst analog zu den zuvor durchgeführten K3s-Pod-Ausfalltests aufgebaut. Im Unterschied zu den Netzwerkexperimenten wurde hier bewusst der synchrone Request-Monitor verwendet.

## Testumgebung

* System: KubeEdge
* Cloud Nodes: `c1`, `c2`, `c3`
* Edge Nodes: `e1`, `e2`
* Namespace: `testapp`
* Deployment: `nginx-testapp`
* Erwartete Replikate: 3
* Service: `nginx-testapp`
* Service-Typ: NodePort
* Monitor-URL: `http://10.10.20.131:30080/`
* Request-Intervall: 1 s
* Request-Timeout: 2 s
* Vorlauf: 30 s
* Nachlauf: 60 s
* Wiederholungen: 10

Obwohl EdgeMesh im Cluster installiert ist, wurde die Verfügbarkeit der Testanwendung in diesem Experiment über den NodePort gemessen. Dadurch bleibt der Zugriffspfad möglichst vergleichbar zu den K3s-Experimenten.

## Methodik

Jeder Testlauf besteht aus drei Phasen:

1. **Vorlaufphase**
   Der stabile Ausgangszustand wird erfasst. Dazu werden Node-Zustände, Pod-Zustände, KubeEdge-Komponenten und Kubernetes-Events gespeichert. Gleichzeitig startet der synchrone Request-Monitor.

2. **Fehlerphase**
   Ein laufender Pod der Testanwendung wird gelöscht. Der Fehlerzeitpunkt wird in `fault_time.txt` gespeichert. Die Pod-Löschung erfolgt mit `kubectl delete pod --wait=false`, damit das Recovery-Polling unmittelbar nach der Fehlerauslösung beginnt und nicht durch ein blockierendes Delete-Kommando verzögert wird.

3. **Recovery- und Nachlaufphase**
   Das Skript prüft einmal pro Sekunde, ob wieder drei Pods der Testanwendung im Zustand `Running` und `1/1` Ready vorhanden sind. Dieser Zeitpunkt wird als `recovery_time.txt` gespeichert. Danach läuft der Request-Monitor für die definierte Nachlaufzeit weiter.

## Ergebnisdateien

Jeder Lauf liegt in einem eigenen Ordner `run-XX`.

Wichtige Dateien pro Lauf:

* `requests.csv`: HTTP-Messwerte des synchronen Request-Monitors
* `summary.txt`: Zusammenfassung des jeweiligen Laufs
* `deleted_pod.txt`: gelöschter Pod
* `deleted_pod_node.txt`: Node des gelöschten Pods
* `test_start_time.txt`: Startzeitpunkt des Laufs
* `fault_time.txt`: Zeitpunkt der Pod-Löschung
* `recovery_time.txt`: Zeitpunkt der Wiederherstellung
* `test_end_time.txt`: Endzeitpunkt des Laufs
* `recovery_poll.log`: Polling bis zur Wiederherstellung
* `pods_before.txt` / `pods_after.txt`: Zustand der Testanwendung vor und nach dem Lauf
* `nodes_before.txt` / `nodes_after.txt`: Node-Zustände vor und nach dem Lauf
* `kubeedge_pods_before.txt` / `kubeedge_pods_after.txt`: Zustand der KubeEdge-Komponenten
* `events_before.txt` / `events_after.txt`: Kubernetes-Events

Die aggregierte Auswertung wird erzeugt mit:

```bash
python3 experiments/kubeedge/scripts/aggregate_pod_failure.py
```

Das Skript erzeugt:

* `pod-failure-summary.csv`
* `pod-failure-summary-aggregate.txt`

## Ergebnisse

Alle zehn finalen Testläufe wurden vollständig durchgeführt. Für alle Läufe waren die erwarteten Ergebnisdateien vorhanden.

### Request Success Rate

Die Request Success Rate lag in allen zehn Läufen bei 100 %. Insgesamt traten während der Pod-Ausfälle keine fehlgeschlagenen HTTP-Requests auf.

* Mittelwert: 100,0 %
* Minimum: 100,0 %

### Fehlerrate

Die Fehlerrate lag in allen Läufen bei 0 %. Es wurden keine Timeouts, Verbindungsfehler oder nicht erfolgreiche HTTP-Statuscodes beobachtet.

* Mittelwert: 0,0 %
* Maximum: 0,0 %

### Recovery Time / MTTR

Alle Läufe erreichten wieder den gewünschten Zustand mit drei laufenden und bereiten Pods. Die gemessene Recovery Time lag zwischen 1 s und 5 s.

* Median: 3,0 s
* Mittelwert: 3,5 s
* Minimum: 1,0 s
* Maximum: 5,0 s

Die Recovery-Polls zeigen, dass nach der Pod-Löschung jeweils zunächst nur zwei von drei Pods bereit waren und anschließend innerhalb weniger Sekunden wieder drei bereite Pods erreicht wurden.

### Zeit bis stabiler Zustand

Für dieses Pod-Ausfall-Szenario entspricht der stabile Zustand dem Zeitpunkt, an dem wieder drei Pods der Testanwendung im Zustand `Running` und `1/1` Ready vorhanden sind. Dieser Zustand wurde in allen Läufen erreicht.

Zusätzlich blieben alle Nodes vor und nach den Läufen im Zustand `Ready`.

### Pod-Restarts

Es wurden keine Container-Restarts beobachtet. Die bestehenden Pods wurden nicht neu gestartet; stattdessen wurde jeweils ein Ersatz-Pod erzeugt.

* Pod-Restarts vor/nach den Läufen: 0

### Node-Status

Alle Cloud- und Edge-Nodes waren vor und nach den Läufen im Zustand `Ready`.

Beobachtete Nodes:

* `c1`
* `c2`
* `c3`
* `e1`
* `e2`

Es wurden keine Zustände `NotReady` oder `Unknown` beobachtet.

### Control-Plane-/Edge-Verhalten

Die KubeEdge-Komponenten liefen nach den Testläufen weiter stabil. In den aggregierten Ergebnissen waren insbesondere folgende Komponenten im Zustand `Running`:

* `cloudcore`
* `cloud-iptables-manager`
* `edge-eclipse-mosquitto`
* `edgemesh-agent`

Es wurden keine Hinweise auf Instabilitäten der KubeEdge-Komponenten beobachtet.

## Verteilung der gelöschten Pods

Die gelöschten Pods lagen gleichmäßig auf den beiden Edge Nodes:

* 5 Läufe mit gelöschtem Pod auf `e1`
* 5 Läufe mit gelöschtem Pod auf `e2`

Damit wurden beide Edge Nodes im Pod-Ausfall-Szenario berücksichtigt.

## Auffälligkeiten

In den finalen zehn Läufen traten keine kritischen Auffälligkeiten auf. Der zuvor beobachtete Ausreißer eines archivierten Vorlaufs wurde durch eine Anpassung des Skripts behoben. Ursache war vermutlich, dass `kubectl delete pod` ohne `--wait=false` blockierend ausgeführt wurde und dadurch das Recovery-Polling verzögert startete. Die betroffenen Vorläufe wurden archiviert und werden nicht für die finale Auswertung verwendet.

In den finalen Läufen wurde `kubectl delete pod --wait=false` verwendet. Dadurch beginnt die Messung der Wiederherstellung unmittelbar nach der Fehlerauslösung.

## Interpretation

KubeEdge stellte die gewünschte Replikazahl der Testanwendung nach dem Löschen eines einzelnen Pods zuverlässig wieder her. Die Service-Verfügbarkeit blieb während der gesamten Messreihe erhalten, da alle HTTP-Requests erfolgreich beantwortet wurden.

Das beobachtete Verhalten entspricht dem erwarteten Self-Healing-Verhalten auf Pod-Ebene: Der gelöschte Pod wurde durch einen neuen Pod ersetzt, ohne dass bestehende Pods neu gestartet wurden oder Node-Zustände beeinträchtigt wurden. Auch die KubeEdge-spezifischen Komponenten blieben stabil.

Für dieses Szenario zeigt KubeEdge damit ein zuverlässiges Self-Healing-Verhalten bei einzelnen Pod-Ausfällen.
