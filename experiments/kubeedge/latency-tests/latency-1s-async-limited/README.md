# KubeEdge Latenztest 1s – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Experiment wurde das Verhalten der KubeEdge-Testumgebung bei erhöhter Netzwerklatenz zwischen Cloud- und Edge-Netz untersucht. Ziel war es zu prüfen, ob eine künstlich eingebrachte Latenz von 1s pro Richtung Auswirkungen auf die Erreichbarkeit der Testanwendung, die Antwortzeiten oder den Zustand der KubeEdge- und Kubernetes-Komponenten hat.

Die Messreihe ist methodisch an den entsprechenden 1s-Latenztest der K3s-Versuchsreihe angelehnt. Wie bei K3s wurden zehn Wiederholungen mit 180s Vorlauf, 300s Störphase und 180s Nachlauf durchgeführt.

## Versuchsaufbau

Die Testumgebung bestand aus einem KubeEdge-Cluster mit drei Cloud-Nodes und zwei Edge-Nodes. Die Cloud-Nodes liefen im Cloud-Netz `10.10.10.0/24`, die Edge-Nodes im Edge-Netz `10.10.20.0/24`. Zwischen beiden Netzen befand sich eine separate Router-VM, über die der gesamte relevante Datenverkehr geleitet wurde.

Die Testanwendung war ein dreifach repliziertes NGINX-Deployment im Namespace `testapp`. Die Anwendung wurde über einen NodePort-Service auf den Edge-Nodes bereitgestellt. Die HTTP-Anfragen wurden von `c1` an den Edge-Node `e1` unter `http://10.10.20.131:30080/` gesendet.

## Messmethode

Für die Messung wurde ein asynchroner Request-Monitor verwendet. Dieser sendete im Abstand von 1s HTTP-Anfragen an die Testanwendung und protokollierte Startzeit, Endzeit, HTTP-Statuscode, Antwortzeit und Fehlerstatus. Die maximale Anzahl gleichzeitig offener Requests wurde auf 10 begrenzt, um unkontrollierte Backlog-Effekte zu vermeiden.

Die Netzwerklatenz wurde auf der Router-VM mittels `tc/netem` eingebracht. Im Unterschied zum ersten technischen Smoke-Test wurde die finale Messreihe symmetrisch durchgeführt. Dazu wurde der Delay auf beiden relevanten Router-Interfaces aktiviert:

* `ens161`: Router Richtung Edge-Netz
* `ens256`: Router Richtung Cloud-Netz

Dadurch ergab sich für HTTP-Anfragen eine erwartete Round-Trip-Verzögerung von ungefähr 2s.

## Parameter

| Parameter                 |                         Wert |
| ------------------------- | ---------------------------: |
| System                    |                     KubeEdge |
| Szenario                  |   `latency-1s-async-limited` |
| Eingebrachte Latenz       |              1s pro Richtung |
| Erwartete Round-Trip-Zeit |                       ca. 2s |
| Vorlauf                   |                         180s |
| Störphase                 |                         300s |
| Nachlauf                  |                         180s |
| Wiederholungen            |                           10 |
| HTTP-Timeout              |                          30s |
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

Die Traceroute-Prüfung bestätigte, dass der Verkehr von `c1` zu `e1` über die Router-VM und die Router-Adresse `10.10.10.136` lief. In allen zehn Läufen wurde `tc/netem delay 1s` auf beiden Interfaces aktiviert und anschließend wieder entfernt.

## Laufzeiten

Die Laufzeiten der einzelnen Durchläufe waren stabil und reproduzierbar. Die erwartete reine Messdauer betrug 660s pro Lauf. Die tatsächlich dokumentierten Laufzeiten lagen zwischen 668s und 669s und enthalten zusätzlich geringe Overheads durch Preflight, Statusabfragen und Auswertung.

| Kennzahl            |    Wert |
| ------------------- | ------: |
| Laufzeit Minimum    | 668.00s |
| Laufzeit Median     | 668.00s |
| Laufzeit Mittelwert | 668.10s |
| Laufzeit Maximum    | 669.00s |

Damit traten in der finalen Messreihe keine Hinweise auf Host-Pausen, VM-Unterbrechungen oder Monitor-Artefakte auf.

## Ergebnisse

### Verfügbarkeit

Die Testanwendung blieb während der gesamten Messreihe erreichbar. Es wurden keine fehlgeschlagenen HTTP-Requests beobachtet.

| Kennzahl                           | Ergebnis |
| ---------------------------------- | -------: |
| Overall Request Success Rate       | 100.00 % |
| Fault Success Rate                 | 100.00 % |
| Fault Error Rate                   |   0.00 % |
| Fehlgeschlagene Requests insgesamt |        0 |
| Fehlertypen während der Störphase  |    keine |

### Antwortzeiten

In der Baseline-Phase lagen die Antwortzeiten im niedrigen einstelligen Millisekundenbereich. Während der Störphase stiegen die Antwortzeiten erwartungsgemäß auf ungefähr 2s. Nach Entfernen der Latenz normalisierten sich die Antwortzeiten wieder auf wenige Millisekunden.

| Kennzahl             | Minimum |  Median | Mittelwert | Maximum |
| -------------------- | ------: | ------: | ---------: | ------: |
| Baseline Median [ms] |    1.71 |    2.33 |       2.30 |    2.59 |
| Fault Median [ms]    | 2003.07 | 2003.47 |    2003.46 | 2003.74 |
| Fault p95 [ms]       | 2005.32 | 2006.03 |    2006.01 | 2006.56 |
| After Median [ms]    |    1.64 |    2.04 |       2.00 |    2.32 |

Der Fault-Median von etwa 2003 ms bestätigt, dass die symmetrisch eingebrachte Latenz korrekt wirkte. Die gemessenen Werte entsprechen der erwarteten Round-Trip-Zeit von ungefähr 2s.

### Recovery

Als Recovery-Zeit wurde die Zeit zwischen Entfernen der `tc/netem`-Regel und dem ersten erfolgreichen Request mit einer Antwortzeit unter 500 ms betrachtet.

| Kennzahl            |  Wert |
| ------------------- | ----: |
| Recovery Minimum    | 1.55s |
| Recovery Median     | 1.77s |
| Recovery Mittelwert | 1.83s |
| Recovery Maximum    | 2.09s |

Die Recovery-Zeiten lagen damit durchgehend im Bereich weniger Sekunden.

## Beobachtungen zu Maximalwerten

In einzelnen Läufen wurden Maximalwerte zwischen ungefähr 4s und 5.5s beobachtet. Diese Werte betreffen einzelne Requests und beeinflussen weder Median noch p95 signifikant. Da die p95-Werte während der Störphase in allen Läufen stabil bei etwa 2005–2007 ms lagen, werden die Maximalwerte als normale Phasenübergangseffekte interpretiert. Solche Requests können genau während des Aktivierens oder Entfernens der Latenz gestartet worden sein und dadurch über Phasengrenzen hinweg laufen.

Im Gegensatz zu einer vorherigen verworfenen Messreihe traten in der finalen Serie keine extremen Laufzeit-Artefakte, fehlenden Fault-Phasen oder unplausiblen Requestzahlen auf.

## Kubernetes- und KubeEdge-Verhalten

Die gespeicherten Node-, Pod- und Event-Zustände vor und nach jedem Lauf zeigen keine Hinweise auf kritische Zustandsänderungen. Die Nodes blieben im Zustand `Ready`, die Pods der Testanwendung blieben `Running`, und es wurden keine zusätzlichen Self-Healing-Effekte wie Pod-Neuplanung, Node-Statuswechsel oder manuelle Recovery-Maßnahmen beobachtet.

Die erhöhte Latenz wirkte sich somit primär auf die Antwortzeit der Anwendung aus, nicht jedoch auf die Verfügbarkeit der Anwendung oder die Stabilität der KubeEdge-Komponenten.

## Interpretation

Die Messreihe zeigt, dass KubeEdge bei einer symmetrisch eingebrachten Latenz von 1s pro Richtung stabil bleibt. Die Testanwendung war während der gesamten Störphase erreichbar, und es wurden keine fehlgeschlagenen Requests beobachtet. Die Antwortzeiten stiegen erwartungsgemäß auf ungefähr 2s an und normalisierten sich nach Entfernen der Latenz innerhalb weniger Sekunden.

Damit stellt eine 1s-Latenz in der betrachteten Testumgebung keinen Ausfallzustand dar, der sichtbare Self-Healing-Mechanismen auslöst. Stattdessen handelt es sich um eine kontrollierte Degradation der Antwortzeit bei weiterhin vollständiger Verfügbarkeit.

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
