# KubeEdge Latenztest 1min – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Experiment wurde das Verhalten der KubeEdge-Testumgebung bei stark erhöhter Netzwerklatenz zwischen Cloud- und Edge-Netz untersucht. Ziel war es zu prüfen, wie sich eine künstlich eingebrachte Latenz von 60s pro Richtung auf die Erreichbarkeit der Testanwendung, die Antwortzeiten und den Zustand der KubeEdge- und Kubernetes-Komponenten auswirkt.

Die Messreihe ist methodisch an den entsprechenden 1min-Latenztest der K3s-Versuchsreihe angelehnt. Wie bei K3s wurden zehn Wiederholungen mit 180s Vorlauf, 600s Störphase und 180s Nachlauf durchgeführt.

## Versuchsaufbau

Die Testumgebung bestand aus einem KubeEdge-Cluster mit drei Cloud-Nodes und zwei Edge-Nodes. Die Cloud-Nodes liefen im Cloud-Netz `10.10.10.0/24`, die Edge-Nodes im Edge-Netz `10.10.20.0/24`. Zwischen beiden Netzen befand sich eine separate Router-VM, über die der relevante Datenverkehr geleitet wurde.

Die Testanwendung war ein dreifach repliziertes NGINX-Deployment im Namespace `testapp`. Die Anwendung wurde über einen NodePort-Service auf den Edge-Nodes bereitgestellt. Die HTTP-Anfragen wurden von `c1` an den Edge-Node `e1` unter `http://10.10.20.131:30080/` gesendet.

## Messmethode

Für die Messung wurde ein asynchroner Request-Monitor verwendet. Dieser sendete im Abstand von 1s HTTP-Anfragen an die Testanwendung und protokollierte Startzeit, Endzeit, HTTP-Statuscode, Antwortzeit und Fehlerstatus. Die maximale Anzahl gleichzeitig offener Requests wurde auf 10 begrenzt, um unkontrollierte Backlog-Effekte zu vermeiden.

Die Netzwerklatenz wurde auf der Router-VM mittels `tc/netem` eingebracht. Die Störung wurde symmetrisch auf beiden relevanten Router-Interfaces aktiviert:

* `ens161`: Router Richtung Edge-Netz
* `ens256`: Router Richtung Cloud-Netz

Dadurch ergab sich für HTTP-Anfragen eine erwartete Round-Trip-Verzögerung von ungefähr 120s.

## Parameter

| Parameter                 |                         Wert |
| ------------------------- | ---------------------------: |
| System                    |                     KubeEdge |
| Szenario                  | `latency-1min-async-limited` |
| Eingebrachte Latenz       |             60s pro Richtung |
| Erwartete Round-Trip-Zeit |                     ca. 120s |
| Vorlauf                   |                         180s |
| Störphase                 |                         600s |
| Nachlauf                  |                         180s |
| Wiederholungen            |                           10 |
| HTTP-Timeout              |                         180s |
| Request-Intervall         |                           1s |
| Max. parallele Requests   |                           10 |
| Router-Interfaces         |              `ens161 ens256` |
| Ziel-URL                  | `http://10.10.20.131:30080/` |

## Validierung

Die Messreihe wurde vor und nach jedem Lauf durch Route-Preflights validiert. Zusätzlich wurden der verwendete Netzwerkpfad, die aktive `tc/netem`-Konfiguration sowie das Cleanup nach der Störphase dokumentiert.

| Validierung                            | Ergebnis |
| -------------------------------------- | -------: |
| Vorhandene Runs                        |    10/10 |
| Preflight vor dem Lauf erfolgreich     |    10/10 |
| Preflight nach dem Lauf erfolgreich    |    10/10 |
| Routerpfad validiert                   |    10/10 |
| `tc/netem` während der Störphase aktiv |    10/10 |
| `tc/netem` nach der Störphase entfernt |    10/10 |

Die Traceroute-Prüfung bestätigte, dass der Verkehr von `c1` zu `e1` über die Router-VM und die Router-Adresse `10.10.10.136` lief. In allen zehn Läufen wurde `tc/netem delay 60s` auf beiden Interfaces aktiviert und anschließend wieder entfernt.

## Laufzeiten

Die erwartete reine Messdauer betrug 960s pro Lauf. Die tatsächlich dokumentierten Laufzeiten lagen zwischen 968s und 969s und enthalten zusätzlich geringe Overheads durch Preflight, Statusabfragen und Auswertung.

| Kennzahl            |    Wert |
| ------------------- | ------: |
| Laufzeit Minimum    | 968.00s |
| Laufzeit Median     | 968.00s |
| Laufzeit Mittelwert | 968.20s |
| Laufzeit Maximum    | 969.00s |

Damit traten in der finalen Messreihe keine Hinweise auf Host-Pausen, VM-Unterbrechungen oder Monitor-Artefakte auf.

## Ergebnisse

### Verfügbarkeit

Während der Baseline-Phase war die Testanwendung stabil erreichbar. Während der Störphase kam es dagegen zu einer deutlichen Degradation der Erreichbarkeit. Die Fault Success Rate lag im Median nur noch bei 7,91 %, während die Fault Error Rate im Median 92,09 % betrug.

| Kennzahl                 | Minimum | Median | Mittelwert | Maximum |
| ------------------------ | ------: | -----: | ---------: | ------: |
| Overall Success Rate [%] |   59.48 |  75.58 |      74.94 |   86.65 |
| Overall Error Rate [%]   |   13.35 |  24.42 |      25.06 |   40.52 |
| Fault Success Rate [%]   |    2.41 |   7.91 |       7.69 |   17.39 |
| Fault Error Rate [%]     |   82.61 |  92.09 |      92.31 |   97.59 |

Insgesamt wurden 4695 Requests erfasst. Davon schlugen 1195 Requests fehl. Während der Störphase traten vor allem `ClientConnectorError` und `TimeoutError` auf. Zusätzlich wurden vereinzelt `ServerDisconnectedError` und `ClientOSError` beobachtet.

| Fehlertyp während der Störphase | Anzahl |
| ------------------------------- | -----: |
| `ClientConnectorError`          |    920 |
| `TimeoutError`                  |    148 |
| `ServerDisconnectedError`       |     12 |
| `ClientOSError`                 |      2 |

### Antwortzeiten

In der Baseline-Phase lagen die Antwortzeiten im niedrigen einstelligen Millisekundenbereich. Während der Störphase waren die Antwortzeiten stark erhöht oder Requests schlugen fehl. Da viele Requests während der Fault-Phase nicht erfolgreich abgeschlossen wurden, ist der allgemeine Fault-Median nur eingeschränkt aussagekräftig. Für die Interpretation sind daher zusätzlich die Erfolgsrate, Fehlerrate und die Latenzen erfolgreicher Fault-Requests zu betrachten.

| Kennzahl             |   Minimum |    Median | Mittelwert |   Maximum |
| -------------------- | --------: | --------: | ---------: | --------: |
| Baseline Median [ms] |      1.27 |      1.67 |       1.73 |      2.32 |
| Overall Median [ms]  |      1.54 |      1.88 |       1.95 |      2.54 |
| Overall p95 [ms]     |  69333.20 |  97719.11 |  101871.40 | 135167.88 |
| Fault Median [ms]    |   2653.87 |  12203.57 |   23018.95 |  68141.63 |
| Fault p95 [ms]       | 180107.29 | 180583.83 |  180599.63 | 180942.21 |
| Fault p99 [ms]       | 180538.24 | 180654.06 |  180724.20 | 180972.95 |
| Fault Maximum [ms]   | 180607.16 | 180907.02 |  180863.29 | 181025.26 |
| After Median [ms]    |      1.33 |      1.56 |       1.62 |      2.12 |

Die hohen Fault-p95- und Fault-p99-Werte liegen nahe am konfigurierten HTTP-Timeout von 180s. Dies zeigt, dass viele Requests während der Störphase nicht innerhalb eines nutzbaren Zeitfensters abgeschlossen wurden.

### Erfolgreiche Requests während der Störphase

Die erfolgreichen Requests während der Störphase zeigen Antwortzeiten in der erwarteten Größenordnung der eingebrachten symmetrischen Latenz. Für HTTP-Anfragen ergibt sich durch 60s Verzögerung pro Richtung eine erwartete Round-Trip-Zeit von ungefähr 120s. Einzelne erfolgreiche Requests lagen darunter oder darüber, abhängig davon, ob sie vollständig innerhalb der Störphase oder an Phasenübergängen gestartet beziehungsweise beendet wurden.

Beispiele aus den Läufen zeigen `success_p95`-Werte erfolgreicher Fault-Requests im Bereich von ungefähr 90s bis über 150s. Dies entspricht der erwartbaren Größenordnung für eine symmetrische 60s-Latenz und bestätigt, dass die Störung tatsächlich wirkte.

### Recovery

Als Recovery-Zeit wurde die Zeit zwischen Entfernen der `tc/netem`-Regel und dem ersten erfolgreichen Request mit einer Antwortzeit unter 500 ms betrachtet.

| Kennzahl            |   Wert |
| ------------------- | -----: |
| Recovery Minimum    |  0.82s |
| Recovery Median     |  1.66s |
| Recovery Mittelwert |  4.47s |
| Recovery Maximum    | 20.09s |

Die meisten Läufe normalisierten sich innerhalb weniger Sekunden. Einzelne Läufe zeigten längere Recovery-Zeiten, insbesondere Run 04 mit 20.09s und Run 10 mit 11.79s. Diese Werte deuten darauf hin, dass nach Entfernen der Latenz noch offene oder abbrechende Verbindungen nachwirken konnten. Insgesamt normalisierte sich die Anwendung jedoch nach der Störphase wieder.

## Kubernetes- und KubeEdge-Verhalten

Die gespeicherten Node-, Pod- und Event-Zustände vor und nach jedem Lauf zeigen keine Hinweise auf kritische Zustandsänderungen. Die Nodes blieben im Zustand `Ready`, die Pods der Testanwendung blieben `Running`, und es wurden keine zusätzlichen Self-Healing-Effekte wie Pod-Neuplanung, Node-Statuswechsel oder manuelle Recovery-Maßnahmen beobachtet.

Die starke Latenz wirkte sich somit primär auf die Anwendungskommunikation und die clientseitige Erreichbarkeit aus. Auf Cluster-Ebene wurde kein klassischer Kubernetes- oder KubeEdge-Ausfallzustand ausgelöst.

## Interpretation

Die Messreihe zeigt, dass eine symmetrische Latenz von 60s pro Richtung die KubeEdge-Testanwendung aus Client-Sicht stark beeinträchtigt. Während die Anwendung bei 1s-Latenz vollständig erreichbar blieb, sank die Fault Success Rate bei 60s-Latenz im Median auf 7,91 %. Die Fault Error Rate stieg entsprechend auf 92,09 %.

Trotz der starken Einschränkung der Anwendungserreichbarkeit blieb die KubeEdge-Infrastruktur stabil. Es wurden keine Node-Ausfälle, Pod-Neuplanungen oder zusätzlichen Self-Healing-Reaktionen beobachtet. Die Störung führte damit nicht zu einer automatischen Reparaturreaktion des Clusters, sondern zu einer deutlichen Degradation der Anwendungskommunikation.

Für die Bewertung dieses Szenarios ist deshalb nicht allein der Fault-Median entscheidend. Aussagekräftiger ist die Kombination aus Fault Success Rate, Fault Error Rate, Timeout- und Verbindungsfehlern sowie Recovery nach Entfernen der Latenz.

## Dateien

Die wichtigsten Ergebnisdateien dieser Messreihe sind:

* `latency-summary.csv`: tabellarische Auswertung pro Run
* `latency-summary-aggregate.txt`: aggregierte Kennzahlen der Messreihe
* `scenario-run.log`: zeitlicher Ablauf aller zehn Läufe
* `run-XX-router/requests.csv`: Rohdaten des Request-Monitors pro Lauf
* `run-XX-router/summary.txt`: Zusammenfassung pro Lauf
* `run-XX-router/tc_during.txt`: dokumentierte aktive `tc/netem`-Regel
* `run-XX-router/tc_after.txt`: dokumentiertes Cleanup nach der Störphase
* `run-XX-router/nodes_before.txt` und `nodes_after.txt`: Node-Zustand vor und nach dem Lauf
* `run-XX-router/pods_before.txt` und `pods_after.txt`: Pod-Zustand vor und nach dem Lauf
* `run-XX-router/events_before.txt` und `events_after.txt`: Kubernetes-Events vor und nach dem Lauf
