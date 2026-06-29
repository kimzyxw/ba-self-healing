# K3s Pod-Failure Rerun Final

Dieses Verzeichnis enthält die finalen Pod-Ausfalltests des neu aufgebauten K3s-Clusters. Die Testreihe dient der Untersuchung des nativen Self-Healing-Verhaltens von K3s beim Ausfall einzelner Pods der Testanwendung.

## Ziel der Testreihe

Ziel der Testreihe war es, zu prüfen, ob K3s nach dem gezielten Löschen eines einzelnen Pods den gewünschten Sollzustand der Anwendung automatisch wiederherstellt. Während jedes Testlaufs wurde die Erreichbarkeit der Anwendung kontinuierlich über HTTP-Anfragen geprüft. Dadurch können sowohl die Serviceverfügbarkeit als auch die Wiederherstellungszeit der Anwendung bewertet werden.

Im Fokus stehen insbesondere folgende Metriken:

* Request Success Rate
* Fehlerrate
* Recovery Time / MTTR
* Stabilisierungszeit
* Pod-Restarts
* Node-Status, insbesondere das Auftreten von `Ready` und `NotReady`

## Cluster und Testanwendung

Verwendet wurde ein K3s-Cluster mit drei Server-/Control-Plane-Nodes und zwei Worker-Nodes:

* `k3s-s1` (`10.10.10.129`)
* `k3s-s2` (`10.10.10.130`)
* `k3s-s3` (`10.10.10.131`)
* `k3s-w1` (`10.10.20.129`)
* `k3s-w2` (`10.10.20.130`)

Die Testanwendung läuft im Namespace `testapp` als Deployment `nginx-test` mit drei Replikaten. Die Anwendung wird über einen NodePort-Service auf Port `30080` bereitgestellt.

## Netzwerkabsicherung

Damit die Versuchsdurchführung methodisch konsistent bleibt, werden zu Beginn jedes Testlaufs die statischen Routen erneut gesetzt und geprüft. Dadurch wird sichergestellt, dass der Verkehr zwischen Server-Netz und Worker-Netz über die Router-VM läuft und nicht über das NAT-Netz der Virtualisierungsumgebung.

Verwendete Routen:

* Server-Nodes: `10.10.20.0/24 via 10.10.10.136 dev ens256`
* Worker-Nodes: `10.10.10.0/24 via 10.10.20.133 dev ens256`

Das Ergebnis dieser Prüfung wird pro Run in `routes_ok.txt` gespeichert. Nur Runs mit `routes_ok=true` werden als methodisch gültig betrachtet.

## Durchführung

Die finalen zehn Pod-Ausfalltests wurden mit folgendem Befehl gestartet:

```bash
RUNS=10 PRE_SECONDS=30 POST_SECONDS=60 INTERVAL=1 TIMEOUT=2 RUN_PAUSE_SECONDS=10 \
  experiments/k3s/scripts/run_pod_failure_scenario.sh \
  http://10.10.10.129:30080/ \
  experiments/k3s/pod-failure-rerun-final
```

Pro Run wurde folgender Ablauf durchgeführt:

1. Setzen und Prüfen der statischen Routen.
2. Erfassen des Ausgangszustands von Nodes, Pods, Deployment, Service und Events.
3. Start des synchronen Request-Monitors.
4. Baseline-Phase von 30 Sekunden.
5. Löschen eines laufenden Pods der Testanwendung.
6. Warten auf Wiederherstellung von drei laufenden und bereiten Pods.
7. Prüfung des stabilen Clusterzustands.
8. Post-Phase von 60 Sekunden.
9. Speichern aller Rohdaten und der Run-Zusammenfassung.

## Request-Monitoring

Für die Pod-Ausfalltests wurde der synchrone Request-Monitor `experiments/k3s/scripts/request_monitor.py` verwendet. Dieser sendet in einem festen Intervall von einer Sekunde HTTP-Anfragen an die Testanwendung und schreibt die Ergebnisse in `requests.csv`.

Pro Request werden unter anderem folgende Werte gespeichert:

* Startzeitpunkt der Anfrage
* Endzeitpunkt der Anfrage
* HTTP-Statuscode
* Antwortdauer in Millisekunden
* Erfolgsstatus
* Fehlertyp, falls vorhanden

## Erhobene Metriken

Die wichtigsten Metriken werden pro Run in `summary.txt` gespeichert:

* `total_requests`: Gesamtzahl der Requests
* `ok_requests`: Anzahl erfolgreicher Requests
* `failed_requests`: Anzahl fehlgeschlagener Requests
* `success_rate_percent`: Request Success Rate
* `error_rate_percent`: Fehlerrate
* `recovery_seconds`: Recovery Time der Anwendung
* `stabilization_seconds`: Zeit bis zum stabilen Clusterzustand
* `pod_restart_delta`: Änderung der Container-Restart-Zähler
* `node_notready_detected`: Auftreten eines NodeNotReady-Zustands
* `node_notready_seconds`: Dauer von NodeNotReady-Zuständen
* `final_ready`: finaler Zustand aller Nodes
* `valid`: Gültigkeit des Runs

## Ergebnisüberblick

Alle zehn finalen Pod-Ausfallruns wurden gültig abgeschlossen.

Zusammenfassung der finalen Runs:

* Runs: 10
* gültige Runs: 10
* Routes OK: 10
* fehlgeschlagene Requests: 0
* minimale Request Success Rate: 100 %
* Pod-Restarts: 0
* NodeNotReady-Ereignisse: 0
* finaler Clusterzustand: alle Nodes `Ready`

Die Recovery-Zeiten lagen zwischen 1 und 2 Sekunden. Die Stabilisierungszeiten lagen zwischen 1 und 3 Sekunden.

## Relevante Artefakte

Pro Run werden unter anderem folgende Dateien gespeichert:

* `requests.csv`: kontinuierliches HTTP-Request-Monitoring
* `summary.txt`: zentrale Metriken des Runs
* `routes_ok.txt`: Ergebnis der Routenprüfung
* `route-checks/`: Detailausgaben der Routen- und Ping-Prüfungen
* `nodes_before.txt`: Node-Zustand vor dem Pod-Ausfall
* `nodes_after.txt`: Node-Zustand nach dem Pod-Ausfall
* `pods_before.txt`: Pod-Zustand vor dem Pod-Ausfall
* `pods_after.txt`: Pod-Zustand nach dem Pod-Ausfall
* `events_before.txt`: Kubernetes-Events vor dem Run
* `events_after.txt`: Kubernetes-Events nach dem Run
* `node_status_poll.csv`: fortlaufender Node-Status während des Runs

## Appendix-Tabelle

Die Appendix-Tabelle wird reproduzierbar aus den Run-Daten erzeugt:

```bash
python3 experiments/k3s/scripts/make_k3s_pod_failure_appendix_runs.py
```

Die erzeugte LaTeX-Tabelle liegt unter:

```text
appendix-tables/k3s_pod_failure_appendix_runs.tex
```

Die zugehörige CSV-Datei liegt unter:

```text
experiments/k3s/pod-failure-rerun-final/k3s_pod_failure_appendix_runs.csv
```

Die Tabelle verwendet folgende Spalten:

```text
Run & Störung & Ziel & Req. & OK & Fail & Succ. [%] & Err. [%] & Rec. [s] & Stab. [s] & Pod-Rest. & NodeNotReady & NotReady [s] & Final Ready & gültig
```

## Hinweis zu Smoke- und Debugläufen

Vor der finalen Testreihe wurden mehrere Smoke- und Debugläufe durchgeführt, um das Skript, die Routenprüfung und die Erfassung der Metriken zu validieren. Diese Läufe sind nicht Bestandteil der finalen Auswertung. Für die Appendix-Tabelle und die Ergebnisauswertung werden ausschließlich die Runs aus `experiments/k3s/pod-failure-rerun-final` verwendet.
