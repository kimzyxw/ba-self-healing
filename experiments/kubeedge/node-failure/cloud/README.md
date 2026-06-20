# KubeEdge Cloud Node Failure Tests

Dieses Verzeichnis enthält die finalen Messdaten zu Cloud-Node-Ausfällen in der KubeEdge-Testumgebung. Ziel der Versuche war es, das Verhalten der Testanwendung und des KubeEdge-Clusters beim vollständigen Ausfall einzelner Cloud-Knoten zu untersuchen.

## Testumgebung

Die KubeEdge-Testumgebung bestand aus drei Cloud-Knoten (`c1`, `c2`, `c3`), zwei Edge-Knoten (`e1`, `e2`) und einer dedizierten Router-VM zwischen Cloud- und Edge-Netz. Die Cloud-Knoten bildeten die K3s-basierte Control Plane und führten zusätzlich die KubeEdge-Cloud-Komponenten aus. Die Edge-Knoten liefen mit `edgecore` und stellten die Testanwendung über einen NodePort-Service bereit.

Die Testanwendung war ein `nginx:stable` Deployment im Namespace `testapp` mit drei Replikaten und einem NodePort-Service auf Port `30080`.

Für die Cloud-Node-Ausfalltests wurde `c1` nicht ausgeschaltet, da dieser Knoten als Steuer- und Monitoring-Knoten verwendet wurde. Getestet wurden daher die Cloud-Knoten `c2` und `c3`.

| Knoten |                     Rolle |     Cloud-IP |
| ------ | ------------------------: | -----------: |
| c1     | Control Plane, Monitoring | 10.10.10.133 |
| c2     |             Control Plane | 10.10.10.134 |
| c3     |             Control Plane | 10.10.10.135 |
| e1     |                 Edge Node | 10.10.20.131 |
| e2     |                 Edge Node | 10.10.20.132 |

Die HTTP-Requests wurden von `c1` aus gegen den NodePort von `e1` gesendet:

```text
http://10.10.20.131:30080/
```

Damit wurde während der Cloud-Node-Ausfälle die Verfügbarkeit der Edge-seitigen Anwendung beobachtet, während jeweils ein Cloud-Control-Plane-Knoten ausfiel.

## Vorversuche

Vor der finalen Messreihe wurden Vorversuche mit einem automatischen Recovery-Timeout von 600 Sekunden durchgeführt. Diese zeigten, dass ausgefallene Cloud-Knoten nach dem Neustart der VM nicht zuverlässig innerhalb von 600 Sekunden wieder als `Ready` erkannt wurden. Ein zusätzlicher Zwischentest mit einem erhöhten Recovery-Timeout von 1800 Sekunden zeigte anschließend, dass eine automatische Wiederherstellung ohne manuellen Eingriff möglich ist, jedoch deutlich länger als 600 Sekunden dauern kann.

Die Vorversuche liegen im Unterverzeichnis `_preliminary-tests` und sind nicht Teil der finalen Auswertung.

Für die finale Messreihe wurde daher ein einheitlicher Recovery-Timeout von 1800 Sekunden verwendet.

## Route-Preflight

Vor und nach jedem Versuchslauf wurde ein Route-Preflight durchgeführt. Dieser Schritt stellte sicher, dass die statischen Routen zwischen Cloud- und Edge-Netz korrekt gesetzt waren und der HTTP-Messpfad nicht durch fehlende Routingregeln verfälscht wurde.

Die verwendeten Routen waren:

| Richtung      | Route                            |
| ------------- | -------------------------------- |
| Cloud zu Edge | `10.10.20.0/24 via 10.10.10.136` |
| Edge zu Cloud | `10.10.10.0/24 via 10.10.20.133` |

Der Preflight prüfte zusätzlich die Erreichbarkeit der Edge-Knoten per Ping, SSH und HTTP-Requests gegen beide NodePorts. In allen zehn finalen Versuchsläufen war der Preflight sowohl vor als auch nach dem Lauf erfolgreich.

## Durchführung

Es wurden zehn finale Cloud-Node-Ausfallläufe durchgeführt. Dabei wurden `c2` und `c3` abwechselnd ausgeschaltet.

| Lauf      | Ausgefallener Knoten | Monitor-URL                  |
| --------- | -------------------- | ---------------------------- |
| run-01-c2 | c2                   | `http://10.10.20.131:30080/` |
| run-02-c3 | c3                   | `http://10.10.20.131:30080/` |
| run-03-c2 | c2                   | `http://10.10.20.131:30080/` |
| run-04-c3 | c3                   | `http://10.10.20.131:30080/` |
| run-05-c2 | c2                   | `http://10.10.20.131:30080/` |
| run-06-c3 | c3                   | `http://10.10.20.131:30080/` |
| run-07-c2 | c2                   | `http://10.10.20.131:30080/` |
| run-08-c3 | c3                   | `http://10.10.20.131:30080/` |
| run-09-c2 | c2                   | `http://10.10.20.131:30080/` |
| run-10-c3 | c3                   | `http://10.10.20.131:30080/` |

Jeder Lauf bestand aus:

| Phase                           |  Dauer |
| ------------------------------- | -----: |
| Vorlauf                         |   30 s |
| geplante VM-Ausfallzeit         |  120 s |
| Nachlauf                        |   60 s |
| Request-Intervall               |    1 s |
| HTTP-Timeout                    |    2 s |
| Recovery-Timeout für Node Ready | 1800 s |

Der Ausfall wurde manuell über VMware Fusion ausgelöst, indem die jeweilige Cloud-VM ausgeschaltet und nach Ablauf der geplanten Ausfallzeit wieder gestartet wurde. Danach wartete das Skript bis zu 1800 Sekunden darauf, dass der betroffene Cloud-Knoten wieder als `Ready` erkannt wurde.

Während des gesamten Laufs wurden HTTP-Requests an die Testanwendung gesendet. Zusätzlich wurden Kubernetes-Zustände, Pod-Verteilungen, Events, Node-Status und Zeitpunkte der Fehlererkennung und Wiederherstellung gespeichert.

## Aggregierte Ergebnisse

| Metrik                              | Ergebnis |
| ----------------------------------- | -------: |
| Anzahl finaler Läufe                |       10 |
| Preflight vor dem Lauf erfolgreich  |    10/10 |
| Preflight nach dem Lauf erfolgreich |    10/10 |
| Node-Ausfall erkannt                |    10/10 |
| Node wieder Ready erkannt           |    10/10 |
| Manual-Prompt erreicht              |     0/10 |
| Bestätigte manuelle Eingriffe       |     0/10 |
| Gesamte HTTP-Requests               |    11918 |
| Erfolgreiche HTTP-Requests          |    11918 |
| Fehlgeschlagene HTTP-Requests       |        0 |
| Mittlere Request Success Rate       | 100,00 % |
| Median Request Success Rate         | 100,00 % |
| Fehlerrate                          |   0,00 % |
| Fehlerarten                         |    keine |

## Recovery-Zeiten

| Metrik                                       |   Minimum |    Median | Mittelwert |   Maximum |
| -------------------------------------------- | --------: | --------: | ---------: | --------: |
| Zeit bis Node `Unknown`/nicht `Ready`        |   47,00 s |   53,50 s |    53,10 s |   61,00 s |
| Recovery ab Fehlerzeitpunkt                  | 1055,00 s | 1056,00 s |  1084,40 s | 1290,00 s |
| Zeit von bestätigtem Ausschalten bis `Ready` | 1049,00 s | 1051,50 s |  1079,00 s | 1285,00 s |
| Zeit von VM-Neustart bis `Ready`             |  901,00 s |  921,00 s |   942,00 s | 1150,00 s |

## Ergebnisse nach Cloud-Knoten

| Knoten | Läufe | Mittlere Success Rate | Minimale Success Rate | Median bis NotReady/Unknown | Median Recovery ab Fehlerzeitpunkt | Median VM-Neustart bis Ready |
| ------ | ----: | --------------------: | --------------------: | --------------------------: | ---------------------------------: | ---------------------------: |
| c2     |     5 |              100,00 % |              100,00 % |                     54,00 s |                          1055,00 s |                     921,00 s |
| c3     |     5 |              100,00 % |              100,00 % |                     53,00 s |                          1061,00 s |                     921,00 s |

Die Ergebnisse für `c2` und `c3` sind sehr ähnlich. Beide Cloud-Knoten wurden nach dem Ausschalten zuverlässig als nicht verfügbar erkannt und später ohne manuellen Eingriff wieder als `Ready` in das Cluster integriert.

## Latenzen der erfolgreichen Requests

| Metrik                   |  Minimum |   Median | Mittelwert |   Maximum |
| ------------------------ | -------: | -------: | ---------: | --------: |
| Median-Latenz pro Lauf   |  2,47 ms |  2,49 ms |    2,51 ms |   2,62 ms |
| p95-Latenz pro Lauf      |  7,02 ms |  8,47 ms |    8,51 ms |  10,14 ms |
| Maximale Latenz pro Lauf | 59,30 ms | 94,92 ms |  100,12 ms | 145,48 ms |

Da keine HTTP-Requests fehlschlugen, wurden die Latenzmetriken ausschließlich aus erfolgreichen Requests berechnet.

## Interpretation

Die Ergebnisse zeigen, dass die Edge-seitige Testanwendung während der Cloud-Node-Ausfälle vollständig verfügbar blieb. In allen zehn finalen Läufen wurden sämtliche HTTP-Requests erfolgreich beantwortet. Die Request Success Rate lag daher durchgehend bei 100 Prozent.

Gleichzeitig zeigte sich, dass die Reintegration ausgefallener Cloud-Knoten nach einem harten VM-Ausfall deutlich länger dauert als bei den zuvor untersuchten Edge-Node-Ausfällen. Die betroffenen Cloud-Knoten wurden im Median nach 53,5 Sekunden als nicht mehr `Ready` beziehungsweise als `Unknown` erkannt. Nach dem Neustart der VM dauerte es im Median 921 Sekunden, bis der jeweilige Cloud-Knoten wieder als `Ready` erkannt wurde.

Damit ist die Anwendung aus Nutzersicht sehr robust gegenüber dem Ausfall eines einzelnen Cloud-Knotens, solange andere Cloud-Knoten und die Edge-Knoten weiterhin verfügbar sind. Die vollständige Wiederherstellung des Clusterzustands ist jedoch deutlich verzögert. Der Self-Healing-Prozess wirkt auf Anwendungsebene sehr stabil, auf Control-Plane-Ebene aber langsam.

Auffällig ist, dass kein manueller Eingriff erforderlich war. In den Vorversuchen mit einem Recovery-Timeout von 600 Sekunden wurde zunächst der Eindruck erzeugt, dass die Cloud-Knoten nicht automatisch zurückkehren. Die finale Messreihe mit einem Timeout von 1800 Sekunden zeigt jedoch, dass die Wiederherstellung automatisch erfolgt, aber typischerweise länger als 600 Sekunden dauert.

## Methodische Hinweise

Für die finale Auswertung wurden ausschließlich die Läufe `run-01-c2` bis `run-10-c3` auf oberster Ebene dieses Verzeichnisses berücksichtigt. Vorversuche und technische Smoke-Tests wurden ausgeschlossen.

Der Route-Preflight ist Bestandteil der finalen Methodik. Er setzt und validiert vor und nach jedem Lauf die für die Versuchsumgebung notwendigen statischen Routen zwischen Cloud- und Edge-Netz. Dadurch wird sichergestellt, dass beobachtete Effekte nicht auf fehlerhafte Routingzustände der VM-Testumgebung zurückzuführen sind.

Die HTTP-Requests wurden bewusst gegen `e1` gesendet, während Cloud-Knoten `c2` oder `c3` ausfielen. Dadurch wurde die Verfügbarkeit der Edge-seitigen Anwendung während eines Cloud-Control-Plane-Ausfalls gemessen.

## Dateien

Wichtige Ergebnisdateien:

| Datei                                      | Inhalt                                                    |
| ------------------------------------------ | --------------------------------------------------------- |
| `cloud-node-failure-summary.csv`           | Aggregierte Übersicht pro Lauf                            |
| `cloud-node-failure-summary-aggregate.txt` | Aggregierte Kennzahlen über alle finalen Läufe            |
| `run-XX-*/summary.txt`                     | Zusammenfassung eines einzelnen Laufs                     |
| `run-XX-*/requests.csv`                    | HTTP-Request-Messdaten                                    |
| `run-XX-*/route_preflight_before/`         | Route- und Erreichbarkeitsprüfung vor dem Lauf            |
| `run-XX-*/route_preflight_after/`          | Route- und Erreichbarkeitsprüfung nach dem Lauf           |
| `run-XX-*/nodes_*.txt`                     | Node-Zustände vor, während und nach dem Lauf              |
| `run-XX-*/pods_*.txt`                      | Pod-Zustände vor, während und nach dem Lauf               |
| `run-XX-*/events_*.txt`                    | Kubernetes-Events vor, während und nach dem Lauf          |
| `_preliminary-tests/`                      | Vorversuche, nicht Teil der finalen Auswertung            |
| `_technical-smoke-tests/`                  | Technische Smoke-Tests, nicht Teil der finalen Auswertung |
