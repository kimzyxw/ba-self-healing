# KubeEdge Edge Node Failure Tests

Dieses Verzeichnis enthält die finalen Messdaten zu Edge-Node-Ausfällen in der KubeEdge-Testumgebung. Ziel der Versuche war es, das Verhalten der Testanwendung und des KubeEdge-Clusters beim vollständigen Ausfall einzelner Edge-Knoten zu untersuchen.

## Testumgebung

Die KubeEdge-Testumgebung bestand aus drei Cloud-Knoten (`c1`, `c2`, `c3`), zwei Edge-Knoten (`e1`, `e2`) und einer dedizierten Router-VM zwischen Cloud- und Edge-Netz. Die Testanwendung war ein `nginx:stable` Deployment im Namespace `testapp` mit drei Replikaten und einem NodePort-Service auf Port `30080`.

Die Edge-Knoten hatten folgende Rollen und Adressen:

| Knoten |     Rolle |      Edge-IP |
| ------ | --------: | -----------: |
| e1     | Edge Node | 10.10.20.131 |
| e2     | Edge Node | 10.10.20.132 |

Die Requests wurden von `c1` aus gegen den NodePort des jeweils nicht ausgeschalteten Edge-Knotens gesendet:

| Ausgefallener Knoten | Monitor-URL                  |
| -------------------- | ---------------------------- |
| e1                   | `http://10.10.20.132:30080/` |
| e2                   | `http://10.10.20.131:30080/` |

Damit blieb der HTTP-Messpfad während des Ausfalls grundsätzlich auf einen weiterhin laufenden Edge-Knoten gerichtet. Gleichzeitig wurde beobachtet, ob der ausgefallene Edge-Knoten durch KubeEdge als nicht verfügbar erkannt und nach dem Neustart wieder in das Cluster integriert wurde.

## Route-Preflight

Vor und nach jedem Versuchslauf wurde ein Route-Preflight durchgeführt. Dieser Schritt war notwendig, da die statischen Routen zwischen Cloud- und Edge-Netz nach VM-Neustarts nicht dauerhaft erhalten blieben. Analog zur K3s-Testumgebung wurden die Routen deshalb vor jedem Lauf gesetzt und validiert.

Die verwendeten Routen waren:

| Richtung      | Route                            |
| ------------- | -------------------------------- |
| Cloud zu Edge | `10.10.20.0/24 via 10.10.10.136` |
| Edge zu Cloud | `10.10.10.0/24 via 10.10.20.133` |

Der Preflight prüfte zusätzlich die Erreichbarkeit der Edge-Knoten per Ping, SSH und NodePort. In allen zehn finalen Versuchsläufen war der Preflight sowohl vor als auch nach dem Lauf erfolgreich.

## Durchführung

Es wurden zehn finale Edge-Node-Ausfallläufe durchgeführt:

| Lauf      | Ausgefallener Knoten | Monitor-URL                  |
| --------- | -------------------- | ---------------------------- |
| run-01-e1 | e1                   | `http://10.10.20.132:30080/` |
| run-02-e2 | e2                   | `http://10.10.20.131:30080/` |
| run-03-e1 | e1                   | `http://10.10.20.132:30080/` |
| run-04-e2 | e2                   | `http://10.10.20.131:30080/` |
| run-05-e1 | e1                   | `http://10.10.20.132:30080/` |
| run-06-e2 | e2                   | `http://10.10.20.131:30080/` |
| run-07-e1 | e1                   | `http://10.10.20.132:30080/` |
| run-08-e2 | e2                   | `http://10.10.20.131:30080/` |
| run-09-e1 | e1                   | `http://10.10.20.132:30080/` |
| run-10-e2 | e2                   | `http://10.10.20.131:30080/` |

Jeder Lauf bestand aus einer Vorlaufphase von 30 Sekunden, einer Ausfallphase von ungefähr 120 Sekunden und einer Nachlaufphase von 60 Sekunden. Der Ausfall wurde manuell über VMware Fusion ausgelöst, indem die jeweilige Edge-VM ausgeschaltet und nach Ablauf der Fault-Phase wieder gestartet wurde.

Während des gesamten Laufs wurde die Testanwendung im Abstand von einer Sekunde per HTTP abgefragt. Zusätzlich wurden Kubernetes-Zustände, Pod-Verteilungen, Events, Node-Status und Zeitpunkte der Fehlererkennung und Wiederherstellung gespeichert.

## Aggregierte Ergebnisse

| Metrik                                         |      Ergebnis |
| ---------------------------------------------- | ------------: |
| Anzahl finaler Läufe                           |            10 |
| Preflight vor dem Lauf erfolgreich             |         10/10 |
| Preflight nach dem Lauf erfolgreich            |         10/10 |
| Node-Ausfall erkannt                           |         10/10 |
| Node wieder Ready erkannt                      |         10/10 |
| Ungeplante manuelle Eingriffe                  |             0 |
| Mittlere Request Success Rate                  |       90,52 % |
| Median Request Success Rate                    |       90,93 % |
| Minimale Request Success Rate                  |       87,78 % |
| Maximale Request Success Rate                  |       92,28 % |
| Mittlere Fehlerrate                            |        9,48 % |
| Maximale Fehlerrate                            |       12,22 % |
| Median bis Node `Unknown`/nicht `Ready`        |       53,00 s |
| Mittelwert bis Node `Unknown`/nicht `Ready`    |       52,60 s |
| Median bis Node wieder `Ready`                 |      154,50 s |
| Mittelwert bis Node wieder `Ready`             |      155,00 s |
| Median von bestätigtem Ausschalten bis `Ready` |      149,50 s |
| Median von VM-Neustart bis `Ready`             |       19,00 s |
| Fehlerarten                                    | `ReadTimeout` |
| Anzahl fehlgeschlagener Requests               |           234 |
| Pod-Restart-Delta über alle Läufe              |            15 |

## Ergebnisse nach Edge-Knoten

| Knoten | Läufe | Mittlere Success Rate | Minimale Success Rate | Median Recovery Time | Mittlere Recovery Time |
| ------ | ----: | --------------------: | --------------------: | -------------------: | ---------------------: |
| e1     |     5 |               91,18 % |               90,48 % |             154,00 s |               153,80 s |
| e2     |     5 |               89,86 % |               87,78 % |             156,00 s |               156,20 s |

Die Unterschiede zwischen `e1` und `e2` waren gering. Beide Edge-Knoten wurden nach dem Ausschalten zuverlässig als nicht verfügbar erkannt und nach dem Neustart wieder in den Zustand `Ready` überführt.

## Interpretation

Die Ergebnisse zeigen, dass KubeEdge den vollständigen Ausfall einzelner Edge-Knoten in allen zehn Läufen erkannte und die betroffenen Knoten nach dem Neustart wieder in das Cluster integrierte. Ein ungeplanter manueller Eingriff, beispielsweise ein Neustart von `edgecore`, war nicht erforderlich.

Während der Ausfallphase traten jedoch in jedem Lauf temporäre HTTP-Fehler auf. Alle fehlgeschlagenen Requests waren `ReadTimeouts`. Die Fehler traten jeweils direkt nach dem Ausschalten der Edge-VM auf und dauerten etwa bis zur Erkennung beziehungsweise Anpassung des Systemzustands an. Danach stabilisierte sich die Anwendung wieder.

Die Request Success Rate lag im Mittel bei 90,52 %. Damit blieb die Anwendung über den getesteten Zugriffspfad überwiegend erreichbar, war während des Edge-Node-Ausfalls aber nicht vollständig unterbrechungsfrei verfügbar. Die beobachteten Fehler sind plausibel, da der NodePort-Service und die Endpoints unmittelbar nach dem Ausfall noch kurzzeitig auf den betroffenen Edge-Knoten verweisen können oder Verbindungsversuche blockieren, bis der Ausfall im Clusterzustand sichtbar wird.

Auffällig ist die konsistente Zeit bis zur Erkennung des Ausfalls: Der betroffene Edge-Knoten wurde im Median nach 53 Sekunden als nicht mehr `Ready` beziehungsweise `Unknown` erkannt. Nach dem Neustart der VM wurde der Knoten im Median nach 19 Sekunden wieder als `Ready` angezeigt. Bezogen auf den gesamten Zeitraum vom Fehlerzeitpunkt bis zur vollständigen Wiedererkennung lag die Recovery Time im Median bei 154,5 Sekunden.

## Methodische Hinweise

Die Route-Preflight-Prüfung ist Bestandteil der finalen Methodik. Sie stellt sicher, dass die Messung nicht durch fehlende statische Routen der Testinfrastruktur verfälscht wird. Die Routen wurden bewusst nicht dauerhaft über Netplan verändert, da frühere Tests gezeigt hatten, dass Änderungen an der Netzwerkkonfiguration zu unerwünschten Nebeneffekten wie doppelten IP-Adressen oder falschen Gateways führen können. Stattdessen wurden die Routen analog zu den K3s-Netzwerktests vor jedem Lauf gesetzt und überprüft.

Die Verzeichnisse `smoke-test-*` beziehungsweise `_technical-smoke-tests` enthalten technische Vorversuche und sind nicht Teil der finalen Auswertung. Für die Auswertung wurden ausschließlich die Läufe `run-01-e1` bis `run-10-e2` berücksichtigt.

## Dateien

Wichtige Ergebnisdateien:

| Datei                                     | Inhalt                                           |
| ----------------------------------------- | ------------------------------------------------ |
| `edge-node-failure-summary.csv`           | Aggregierte Übersicht pro Lauf                   |
| `edge-node-failure-summary-aggregate.txt` | Aggregierte Kennzahlen über alle Läufe           |
| `run-XX-*/summary.txt`                    | Zusammenfassung eines einzelnen Laufs            |
| `run-XX-*/requests.csv`                   | HTTP-Request-Messdaten                           |
| `run-XX-*/route_preflight_before/`        | Route- und Erreichbarkeitsprüfung vor dem Lauf   |
| `run-XX-*/route_preflight_after/`         | Route- und Erreichbarkeitsprüfung nach dem Lauf  |
| `run-XX-*/nodes_*.txt`                    | Node-Zustände vor, während und nach dem Lauf     |
| `run-XX-*/pods_*.txt`                     | Pod-Zustände vor, während und nach dem Lauf      |
| `run-XX-*/events_*.txt`                   | Kubernetes-Events vor, während und nach dem Lauf |
