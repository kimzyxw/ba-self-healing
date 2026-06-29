# K3s Node-Failure Rerun Final

Dieses Verzeichnis enthält die finalen Node-Ausfalltests des neu aufgebauten K3s-Clusters. Die Testreihe dient der Untersuchung des nativen Self-Healing-Verhaltens von K3s beim Ausfall einzelner Worker- und Server-Nodes.

## Ziel der Testreihe

Ziel der Testreihe war es, zu prüfen, wie K3s auf den temporären Ausfall einzelner Cluster-Nodes reagiert. Dafür wurden ausgewählte virtuelle Maschinen während eines laufenden Request-Monitorings manuell ausgeschaltet und anschließend wieder gestartet.

Beobachtet wurde, ob der betroffene Node wieder als `Ready` erkannt wird, ob die Testanwendung erreichbar bleibt und wie lange die Wiederherstellung des stabilen Clusterzustands dauert.

Im Fokus stehen insbesondere folgende Metriken:

- Request Success Rate
- Fehlerrate
- Recovery Time / MTTR
- Stabilisierungszeit
- Pod-Restarts
- Node-Status, insbesondere `Ready`, `NotReady` und `Unknown`
- finaler Clusterzustand
- Gültigkeit des Runs

## Cluster und Testanwendung

Verwendet wurde ein K3s-Cluster mit drei Server-/Control-Plane-Nodes und zwei Worker-Nodes:

- `k3s-s1` (`10.10.10.129`)
- `k3s-s2` (`10.10.10.130`)
- `k3s-s3` (`10.10.10.131`)
- `k3s-w1` (`10.10.20.129`)
- `k3s-w2` (`10.10.20.130`)

Die Testanwendung läuft im Namespace `testapp` als Deployment `nginx-test` mit drei Replikaten. Die Anwendung wird über einen NodePort-Service auf Port `30080` bereitgestellt.

Der Request-Monitor läuft von `k3s-s1` aus gegen:

    http://10.10.10.129:30080/

## Untersuchte Node-Ausfälle

Die finalen Tests wurden in zwei Gruppen durchgeführt:

- Worker-Node-Ausfälle: `k3s-w1` und `k3s-w2`
- Server-Node-Ausfälle: `k3s-s2` und `k3s-s3`

Der Node `k3s-s1` wurde nicht ausgeschaltet, da auf diesem Node die Teststeuerung, `kubectl` und das Request-Monitoring ausgeführt wurden.

## Netzwerkabsicherung

Zu Beginn und am Ende jedes Testlaufs werden die statischen Routen erneut gesetzt und geprüft. Dadurch wird sichergestellt, dass der Verkehr zwischen Server-Netz und Worker-Netz über die Router-VM läuft und nicht über das NAT-Netz der Virtualisierungsumgebung.

Verwendete Routen:

- Server-Nodes: `10.10.20.0/24 via 10.10.10.136 dev ens256`
- Worker-Nodes: `10.10.10.0/24 via 10.10.20.133 dev ens256`

Die Ergebnisse der Routenprüfung werden pro Run in folgenden Verzeichnissen gespeichert:

- `route_preflight_before/`
- `route_preflight_after/`

Nur Runs mit `preflight_before_ok=true` und `preflight_after_ok=true` werden als methodisch gültig betrachtet.

## Durchführung

Die finalen Worker-Node-Ausfalltests liegen unter:

    experiments/k3s/node-failure/worker-rerun-final

Die finalen Server-Node-Ausfalltests liegen unter:

    experiments/k3s/node-failure/server-rerun-final

Die Tests wurden mit folgendem Skript ausgeführt:

    experiments/k3s/scripts/run_node_failure_manual.sh

Pro Run wurde folgender Ablauf durchgeführt:

1. Setzen und Prüfen der statischen Routen.
2. Erfassen des Ausgangszustands von Nodes, Pods, Deployment, Service, Endpoints und Events.
3. Start des synchronen Request-Monitors.
4. Baseline-Phase von 30 Sekunden.
5. Manuelles Ausschalten der betroffenen VM in VMware Fusion.
6. Warten auf Erkennung des Node-Ausfalls.
7. Geplante Ausfallphase von 120 Sekunden ab bestätigtem Ausschalten der VM.
8. Manuelles Wiederstarten der betroffenen VM.
9. Warten auf erneute Erkennung des Nodes als `Ready`.
10. Warten auf stabilen Clusterzustand.
11. Post-Phase von 60 Sekunden.
12. Erneutes Prüfen der statischen Routen.
13. Speichern aller Rohdaten und der Run-Zusammenfassung.

Für die Server-Node-Ausfälle wurde die Wartezeit auf automatische Wiedererkennung des Nodes erhöht, da Server-/Control-Plane-Nodes nach dem Neustart deutlich länger bis zum Zustand `Ready` benötigen können.

## Request-Monitoring

Für die Node-Ausfalltests wurde der synchrone Request-Monitor verwendet:

    experiments/k3s/scripts/request_monitor.py

Dieser sendet in einem festen Intervall von einer Sekunde HTTP-Anfragen an die Testanwendung und schreibt die Ergebnisse in `requests.csv`.

Pro Request werden unter anderem folgende Werte gespeichert:

- Startzeitpunkt der Anfrage
- Endzeitpunkt der Anfrage
- HTTP-Statuscode
- Antwortdauer in Millisekunden
- Erfolgsstatus
- Fehlertyp, falls vorhanden

## Erhobene Metriken

Die wichtigsten Metriken werden pro Run in `summary.txt` gespeichert:

- `total_requests`: Gesamtzahl der Requests
- `ok_requests`: Anzahl erfolgreicher Requests
- `failed_requests`: Anzahl fehlgeschlagener Requests
- `success_rate_percent`: Request Success Rate
- `error_rate_percent`: Fehlerrate
- `node_notready_detected`: Auftreten eines NodeNotReady- bzw. Unknown-Zustands
- `node_ready_detected`: erneute Erkennung des Nodes als Ready
- `node_notready_seconds`: Dauer zwischen NotReady-Erkennung und Ready-Erkennung
- `node_recovery_seconds`: Zeit zwischen Fehlerzeitpunkt und Ready-Erkennung
- `recovery_seconds`: Recovery Time des Runs
- `stabilization_seconds`: Zeit bis zum stabilen Clusterzustand
- `pod_restart_delta`: Änderung der Container-Restart-Zähler
- `preflight_before_ok`: Routenprüfung vor dem Fehler
- `preflight_after_ok`: Routenprüfung nach dem Fehler
- `manual_intervention`: dokumentiert, ob ein manueller Eingriff nach dem VM-Neustart notwendig war
- `final_ready`: finaler Zustand aller Nodes
- `valid`: Gültigkeit des Runs

## Relevante Artefakte

Pro Run werden unter anderem folgende Dateien gespeichert:

- `requests.csv`: kontinuierliches HTTP-Request-Monitoring
- `summary.txt`: zentrale Metriken des Runs
- `config.txt`: Konfiguration des Runs
- `route_preflight_before/`: Routenprüfung vor dem Fehler
- `route_preflight_after/`: Routenprüfung nach dem Fehler
- `nodes_before.txt`, `nodes_during.txt`, `nodes_after.txt`, `nodes_final.txt`: Node-Zustände
- `pods_before.txt`, `pods_during.txt`, `pods_after.txt`, `pods_final.txt`: Pod-Zustände
- `pods_all_before.txt`, `pods_all_during.txt`, `pods_all_after.txt`, `pods_all_final.txt`: clusterweite Pod-Zustände
- `deployment_before.txt`, `deployment_during.txt`, `deployment_after.txt`, `deployment_final.txt`: Deployment-Zustände
- `service_before.txt`, `service_during.txt`, `service_after.txt`, `service_final.txt`: Service-Zustände
- `endpoints_before.txt`, `endpoints_during.txt`, `endpoints_after.txt`, `endpoints_final.txt`: Endpoint-Zustände
- `events_before.txt`, `events_during.txt`, `events_after.txt`, `events_final.txt`: Kubernetes-Events
- `node_status_poll.csv`: fortlaufender Node-Status während des Runs

## Appendix-Tabelle

Die Appendix-Tabelle wird reproduzierbar aus den Run-Daten erzeugt mit:

    python3 experiments/k3s/scripts/make_k3s_node_failure_appendix_runs.py

Die erzeugte LaTeX-Tabelle liegt unter:

    appendix-tables/k3s_node_failure_appendix_runs.tex

Die zugehörige CSV-Datei liegt unter:

    experiments/k3s/node-failure/k3s_node_failure_appendix_runs.csv

Zusätzlich wird eine kompakte Aggregatdatei erzeugt:

    experiments/k3s/node-failure/k3s_node_failure_summary_aggregate.txt

Die Appendix-Tabelle verwendet folgende Spalten:

    Run & Störung & Ziel & Req. & OK & Fail & Succ. [%] & Err. [%] & Rec. [s] & Stab. [s] & Pod-Rest. & NodeNotReady & NotReady [s] & Final Ready & gültig

## Hinweis zu alten und abgebrochenen Läufen

Ältere manuelle Node-Ausfalltests und abgebrochene Wiederholungen bleiben im Repository erhalten, werden jedoch nicht für die finale Auswertung verwendet.

Für die Appendix-Tabelle und den Ergebnisteil werden ausschließlich die Daten aus folgenden Ordnern berücksichtigt:

- `experiments/k3s/node-failure/worker-rerun-final`
- `experiments/k3s/node-failure/server-rerun-final`
