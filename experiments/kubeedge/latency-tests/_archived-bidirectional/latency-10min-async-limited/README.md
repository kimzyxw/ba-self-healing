# KubeEdge Latenztest: 10 Minuten

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einer sehr hohen Cloud-Edge-Latenz verhält. Dafür wurde zwischen Cloud- und Edge-Netz auf der Router-VM eine künstliche Verzögerung von `600s` pro Richtung eingebracht. Da die Störung auf beiden Router-Interfaces aktiv war, ergibt sich für vollständige Roundtrips eine theoretische Zusatzlatenz von etwa `1200s`.

Ziel war es zu beobachten, ob die Testanwendung während der Störung erreichbar bleibt, ob KubeEdge bzw. Kubernetes Edge-Nodes als nicht erreichbar bewertet und ob nach Entfernen der Störung wieder ein stabiler Zustand erreicht wird.

## Versuchsaufbau

| Parameter                   |                          Wert |
| --------------------------- | ----------------------------: |
| System                      |                      KubeEdge |
| Szenario                    | `latency-10min-async-limited` |
| Anzahl Läufe                |                            10 |
| Verzögerung                 |           `600s` pro Richtung |
| Erwartete zusätzliche RTT   |                   ca. `1200s` |
| Vorlaufphase                |                        `180s` |
| Störphase                   |                       `1800s` |
| Nachlaufphase               |                        `180s` |
| HTTP-Timeout                |                       `1800s` |
| Request-Intervall           |                          `1s` |
| Maximale parallele Requests |                          `10` |
| Ziel-URL                    |  `http://10.10.20.131:30080/` |
| Router-Interfaces           |               `ens161 ens256` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Die künstliche Latenz wurde auf der Router-VM über `tc/netem` auf den Interfaces `ens161` und `ens256` gesetzt. Dadurch wurde der Cloud-Edge-Verkehr symmetrisch verzögert.

## Durchführung

Die Läufe `run-01` bis `run-03` wurden im ersten Durchgang vollständig durchgeführt. Ein anschließender Resume-Lauf wurde zunächst abgebrochen bzw. nicht für die finale Auswertung verwendet, da nach einem Lauf der NodePort noch nicht stabil war und nachfolgende Läufe bereits im Before-Preflight scheiterten. Diese partiellen Daten wurden archiviert und nicht in die finale Auswertung einbezogen.

Für die finale Fortsetzung wurde das Szenario-Skript angepasst. Vor jedem weiteren Lauf wartet das Skript nun, bis der NodePort mehrfach stabil erreichbar ist. Außerdem wird ein fehlgeschlagener After-Preflight dokumentiert, ohne die Auswertung des jeweiligen Laufs abzubrechen. Dadurch werden auch Fälle erfasst, in denen der Cluster nach Ende der Störung noch nicht sofort vollständig stabil ist.

Die finale Auswertung umfasst:

* `run-01` bis `run-03` aus dem ersten vollständigen Durchgang
* `run-04` bis `run-10` aus dem finalen Resume-Durchgang mit stabilitätsbasierter Wartephase

Alle zehn finalen Läufe enthalten vollständige Messdaten und eine `summary.txt`.

## Validierung der Testdurchführung

| Validierung                          |   Ergebnis |
| ------------------------------------ | ---------: |
| Ausgewertete Läufe                   |       `10` |
| Before-Preflight erfolgreich         |    `10/10` |
| After-Preflight erfolgreich          |     `3/10` |
| Routerpfad gültig                    |    `10/10` |
| `tc/netem` während der Störung aktiv |    `10/10` |
| `tc/netem` nach dem Lauf entfernt    |    `10/10` |
| Median Laufdauer                     | `2168.00s` |

Die wesentlichen Validierungskriterien sind erfüllt: Vor jedem Lauf war der Cluster erreichbar, der Verkehr lief über den Routerpfad, die Latenzstörung war während der Störphase aktiv und wurde anschließend wieder entfernt.

Der After-Preflight schlug in 7 von 10 Läufen fehl. Dies wird nicht als Messfehler gewertet, sondern als beobachtetes Systemverhalten: Direkt nach einer 10-minütigen Latenzstörung war der NodePort häufig noch nicht stabil erreichbar, obwohl die eigentliche Störung bereits entfernt und dokumentiert bereinigt war. Der finale Endzustand des Clusters war wieder stabil.

## Aggregierte Ergebnisse

| Metrik                                  |                   Wert |
| --------------------------------------- | ---------------------: |
| Overall Success Rate, Median            |               `31.24%` |
| Overall Error Rate, Median              |               `68.76%` |
| Overall Median Latenz                   |            `1056.46ms` |
| Overall p95 Latenz                      |          `134166.64ms` |
| Baseline Median Latenz                  |               `1.02ms` |
| Fault Success Rate, Median              |                `0.07%` |
| Fault Error Rate, Median                |               `99.93%` |
| Fault Median Latenz                     |            `2065.83ms` |
| Fault p95 Latenz                        |          `135167.03ms` |
| Fault p99 Latenz                        |          `135591.34ms` |
| Fault Max Latenz, Median                |         `1142263.82ms` |
| After Median Latenz                     |               `1.05ms` |
| Recovery Time, Median                   |               `26.71s` |
| Recovery Time, Maximum                  |               `59.93s` |
| Requests gesamt                         |                 `9934` |
| Fehlgeschlagene Requests gesamt         |                 `6870` |
| Häufigster Fehlertyp in der Fault-Phase | `ClientConnectorError` |

## Ergebnisse pro Lauf

| Run    | Overall Success | Fault Success | Fault Error | After Success | Recovery |
| ------ | --------------: | ------------: | ----------: | ------------: | -------: |
| run-01 |        `32.68%` |       `0.00%` |   `100.00%` |     `100.00%` | `41.99s` |
| run-02 |        `30.36%` |       `0.63%` |    `99.37%` |      `68.02%` |  `8.09s` |
| run-03 |        `29.63%` |       `0.00%` |   `100.00%` |      `92.37%` | `59.93s` |
| run-04 |        `25.98%` |       `0.15%` |    `99.85%` |      `85.33%` | `13.58s` |
| run-05 |        `24.52%` |       `0.00%` |   `100.00%` |      `44.52%` | `33.63s` |
| run-06 |        `32.11%` |       `0.00%` |   `100.00%` |     `100.00%` | `35.72s` |
| run-07 |        `35.23%` |       `0.00%` |   `100.00%` |     `100.00%` | `13.77s` |
| run-08 |        `33.84%` |       `0.15%` |    `99.85%` |     `100.00%` | `22.92s` |
| run-09 |        `34.36%` |       `0.44%` |    `99.56%` |     `100.00%` |  `5.53s` |
| run-10 |        `29.39%` |       `0.15%` |    `99.85%` |      `90.76%` | `30.50s` |

## Beobachtetes Cluster-Verhalten

Während der Störphase wurden in allen betrachteten Läufen relevante Kubernetes-Events beobachtet. Besonders auffällig waren:

* `NodeNotReady` für die Edge-Nodes `e1` und `e2`
* `Node is not ready` für Edge-Komponenten und Testapp-Pods
* `TaintManagerEviction` für Pods der Testanwendung
* `FailedScheduling`, da die Edge-Nodes zeitweise durch Taints nicht nutzbar waren und die Cloud-Nodes wegen Node-Affinity bzw. Node-Selector nicht als Zielknoten infrage kamen
* spätere `Successfully assigned`-Events
* spätere `Cancelling deletion`-Events durch den TaintManager

Damit wurde bei 10 Minuten Latenz nicht nur eine erhöhte Request-Latenz beobachtet, sondern ein tatsächlicher Kontroll- und Scheduling-Effekt im Cluster. KubeEdge bzw. Kubernetes bewertete die Edge-Knoten zeitweise als nicht erreichbar. Dadurch kam es zu Eviction- und Scheduling-Reaktionen, obwohl die Anwendung nach Entfernen der Störung wieder stabil erreichbar wurde.

## Interpretation

Bei einer symmetrischen Latenz von `600s` pro Richtung ist die Testanwendung aus Client-Sicht während der Störphase praktisch nicht mehr erreichbar. Die mediane Fault Success Rate liegt bei nur `0.07%`, während die mediane Fault Error Rate `99.93%` beträgt. Der dominante Fehlertyp ist `ClientConnectorError`.

Die Baseline-Phase war in allen Läufen stabil. Auch nach der Störung normalisierten sich die Antwortzeiten erfolgreicher Requests wieder auf niedrige Werte im Millisekundenbereich. Trotzdem zeigt der fehlgeschlagene After-Preflight in mehreren Läufen, dass der NodePort direkt nach Ende der langen Latenzstörung nicht immer sofort stabil erreichbar war.

Im Unterschied zu kürzeren Latenzszenarien ist bei 10 Minuten Latenz eine klare Cluster-Reaktion sichtbar. Die Edge-Nodes werden temporär als `NodeNotReady` markiert, Pods werden zur Löschung markiert und neue Pods können zeitweise nicht geplant werden. Die Ursache liegt darin, dass die Edge-Nodes durch Taints nicht verfügbar sind, während die Cloud-Nodes aufgrund der Scheduling-Vorgaben der Edge-Anwendung nicht als Ausweichziel verwendet werden können.

## Endzustand

Nach Abschluss der finalen Messreihe war der Cluster wieder stabil:

* alle Nodes `Ready`
* drei Testapp-Pods `Running`
* NodePort wieder erreichbar mit `code=200`
* `tc/netem` auf beiden Router-Interfaces entfernt
* Router-Interfaces wieder mit `fq_codel`

Damit ist die Messreihe trotz dokumentierter After-Preflight-Warnungen vollständig und auswertbar.

## Kurzfazit

Eine Latenz von `600s` pro Richtung führt bei KubeEdge zu einem nahezu vollständigen Ausfall der Anwendung während der Störphase. Gleichzeitig reagiert der Cluster sichtbar auf die gestörte Cloud-Edge-Kommunikation: Edge-Nodes werden als `NotReady` markiert, Pods werden zur Eviction vorgesehen und Scheduling schlägt zeitweise fehl. Nach Entfernen der Störung erholt sich das System wieder, jedoch nicht in jedem Lauf sofort innerhalb des kurzen Nachlauf- bzw. After-Preflight-Zeitfensters.
