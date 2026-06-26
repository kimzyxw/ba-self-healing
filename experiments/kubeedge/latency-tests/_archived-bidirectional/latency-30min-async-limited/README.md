# KubeEdge Latenztest: 30 Minuten

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einer extrem hohen Cloud-Edge-Latenz verhält. Dafür wurde zwischen Cloud- und Edge-Netz auf der Router-VM eine künstliche Verzögerung von `1800s` pro Richtung eingebracht. Da die Störung auf beiden Router-Interfaces aktiv war, ergibt sich für vollständige Roundtrips eine theoretische Zusatzlatenz von etwa `3600s`.

Ziel war es, das Verhalten der Testanwendung und der KubeEdge-/Kubernetes-Self-Healing-Mechanismen unter einem extremen Kommunikationsproblem zwischen Cloud- und Edge-Schicht zu bewerten. Dabei wurde insbesondere betrachtet, ob die Anwendung während der Störung erreichbar bleibt, ob Kubernetes Kontrollmechanismen wie Taints, Evictions oder Scheduling auslöst und ob nach Entfernen der Störung wieder ein stabiler Zustand erreicht wird.

## Versuchsaufbau

| Parameter                   |                          Wert |
| --------------------------- | ----------------------------: |
| System                      |                      KubeEdge |
| Szenario                    | `latency-30min-async-limited` |
| Anzahl Läufe                |                            10 |
| Verzögerung                 |          `1800s` pro Richtung |
| Erwartete zusätzliche RTT   |                   ca. `3600s` |
| Vorlaufphase                |                        `180s` |
| Störphase                   |                       `5400s` |
| Nachlaufphase               |                        `180s` |
| HTTP-Timeout                |                       `3600s` |
| Request-Intervall           |                          `1s` |
| Maximale parallele Requests |                          `10` |
| Ziel-URL                    |  `http://10.10.20.131:30080/` |
| Router-Interfaces           |               `ens161 ens256` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Die künstliche Latenz wurde auf der Router-VM mit `tc/netem` auf den Interfaces `ens161` und `ens256` gesetzt. Dadurch wurde der Cloud-Edge-Verkehr symmetrisch verzögert.

## Durchführung

Die Messreihe wurde mit dem asynchronen Request-Monitor mit begrenzter Parallelität durchgeführt. Pro Lauf wurden maximal zehn Requests parallel offen gehalten. Dadurch wird verhindert, dass bei extrem langen Timeouts ein unkontrollierter Request-Backlog entsteht.

Vor jedem Lauf wartete das Szenario-Skript auf einen stabil erreichbaren NodePort. Dieses Vorgehen wurde bereits beim 10min-Latenztest eingeführt, da sich gezeigt hatte, dass der Cluster nach langen Störungen nicht immer sofort wieder stabil erreichbar ist.

Die finale Messreihe umfasst zehn vollständige Läufe von `run-01` bis `run-10`. Alle Läufe enthalten vollständige Messdaten, eine `summary.txt`, dokumentierte `tc`-Zustände und Kubernetes-Zustände vor und nach dem Lauf.

## Validierung der Testdurchführung

| Validierung                          |   Ergebnis |
| ------------------------------------ | ---------: |
| Ausgewertete Läufe                   |       `10` |
| Before-Preflight erfolgreich         |    `10/10` |
| After-Preflight erfolgreich          |     `2/10` |
| Routerpfad gültig                    |    `10/10` |
| `tc/netem` während der Störung aktiv |    `10/10` |
| `tc/netem` nach dem Lauf entfernt    |    `10/10` |
| Median Laufdauer                     | `5769.00s` |

Die wesentlichen Validierungskriterien sind erfüllt. Vor jedem Lauf war der Cluster erreichbar, der Netzwerkpfad verlief über die Router-VM, die Latenzstörung war während der Störphase aktiv und wurde anschließend wieder entfernt.

In den `tc`-Ausgaben wurde die Verzögerung teilweise als `delay 1.8e+03s` dargestellt. Dies entspricht `1800s`. Der Analyzer wurde entsprechend angepasst, sodass diese wissenschaftliche Schreibweise korrekt als aktive `1800s`-Latenz erkannt wird.

Der After-Preflight war nur in 2 von 10 Läufen erfolgreich. Dies wird nicht als Ausschlussgrund gewertet, sondern als Teil des beobachteten Systemverhaltens: Direkt nach einer 90-minütigen Störphase mit 30min-Latenz pro Richtung war der NodePort häufig noch nicht stabil erreichbar. Entscheidend ist, dass die Läufe vollständig abgeschlossen wurden, `tc/netem` bereinigt wurde und der Cluster im finalen Endzustand wieder stabil war.

## Aggregierte Ergebnisse

| Metrik                                  |                   Wert |
| --------------------------------------- | ---------------------: |
| Overall Success Rate, Median            |                `6.66%` |
| Overall Error Rate, Median              |               `93.34%` |
| Overall Median Latenz                   |            `1118.59ms` |
| Overall p95 Latenz                      |            `3105.44ms` |
| Baseline Median Latenz                  |               `1.16ms` |
| Fault Success Rate, Median              |                `0.01%` |
| Fault Error Rate, Median                |               `99.99%` |
| Fault Median Latenz                     |            `1379.88ms` |
| Fault p95 Latenz                        |            `3106.51ms` |
| Fault p99 Latenz                        |          `134166.85ms` |
| Fault Max Latenz, Median                |          `942081.26ms` |
| After Median Latenz                     |               `1.50ms` |
| Recovery Time, Median                   |               `44.65s` |
| Recovery Time, Maximum                  |               `95.27s` |
| Requests gesamt                         |                `46478` |
| Fehlgeschlagene Requests gesamt         |                `43441` |
| Häufigster Fehlertyp in der Fault-Phase | `ClientConnectorError` |

## Ergebnisse pro Lauf

| Run    | Overall Success | Fault Success | Fault Error | After Success | Recovery |
| ------ | --------------: | ------------: | ----------: | ------------: | -------: |
| run-01 |         `7.63%` |       `0.02%` |    `99.98%` |      `93.33%` |  `5.61s` |
| run-02 |         `6.57%` |       `0.02%` |    `99.98%` |      `71.26%` | `69.67s` |
| run-03 |         `5.65%` |       `0.02%` |    `99.98%` |      `47.22%` | `95.27s` |
| run-04 |         `6.74%` |       `0.02%` |    `99.98%` |      `76.54%` | `16.69s` |
| run-05 |         `6.29%` |       `0.00%` |   `100.00%` |      `68.33%` | `57.37s` |
| run-06 |         `7.40%` |       `0.00%` |   `100.00%` |      `98.88%` |  `2.49s` |
| run-07 |         `3.92%` |       `0.00%` |   `100.00%` |       `0.00%` |     `NA` |
| run-08 |         `6.53%` |       `0.00%` |   `100.00%` |      `66.11%` | `63.56s` |
| run-09 |         `7.76%` |       `0.00%` |   `100.00%` |      `96.67%` |  `6.30s` |
| run-10 |         `6.85%` |       `0.02%` |    `99.98%` |      `75.42%` | `44.65s` |

`run-07` ist auffällig, da innerhalb der Nachlaufphase kein erfolgreicher Request unterhalb der Recovery-Schwelle gefunden wurde. Deshalb ist die Recovery Time für diesen Lauf nicht bestimmbar. Der Endzustand der gesamten Messreihe war dennoch stabil.

## Beobachtetes Self-Healing-Verhalten

Während der Störphase war die Anwendung aus Client-Sicht praktisch nicht erreichbar. Die mediane Fault Success Rate lag bei nur `0.01%`, während die mediane Fault Error Rate `99.99%` betrug. Der dominante Fehler war `ClientConnectorError`. Damit konnte die Anwendung während der aktiven Störung trotz vorhandener Pods nicht sinnvoll genutzt werden.

Aus Sicht der Self-Healing-Mechanismen ist wichtig, dass KubeEdge bzw. Kubernetes nicht einfach einen klassischen Pod-Ausfall behandelt hat. Die Pods liefen grundsätzlich weiter, aber die Kommunikation zwischen Cloud- und Edge-Schicht war so stark verzögert, dass der Kontrollzustand des Clusters nicht stabil blieb.

In den Kubernetes-Events wurden insbesondere folgende Reaktionen beobachtet:

* `FailedScheduling` für Pods der Testanwendung
* Hinweise auf untolerated Taints auf den Edge-Nodes
* fehlende Eignung der Cloud-Nodes aufgrund von Node-Affinity bzw. Node-Selector
* spätere `Successfully assigned`-Events
* `TaintManagerEviction` mit `Cancelling deletion`

Diese Events zeigen, dass Kubernetes Kontrollmechanismen aktiviert wurden. Neue oder ersetzte Pods konnten zeitweise nicht geplant werden, weil die Edge-Nodes durch Taints nicht verfügbar waren und die Cloud-Nodes aufgrund der Scheduling-Vorgaben der Edge-Anwendung nicht als Ausweichziel infrage kamen. Dadurch war Self-Healing nur eingeschränkt möglich: Der Cluster reagierte zwar auf den gestörten Zustand, konnte die Anwendung während der Störphase aber nicht durch Rescheduling auf Cloud-Knoten stabilisieren.

Im Vergleich zu kürzeren Latenztests ist dieses Szenario deshalb besonders relevant: Die Störung betrifft nicht nur einzelne HTTP-Requests, sondern führt zu sichtbaren Auswirkungen auf Scheduling, Taint-Verarbeitung und Wiederherstellung der Anwendung.

## Interpretation

Bei einer symmetrischen Latenz von `1800s` pro Richtung und einer Störphase von `5400s` ist die Testanwendung während der Störung nahezu vollständig nicht erreichbar. Die sehr niedrige Fault Success Rate zeigt, dass KubeEdge die Anwendung unter diesen Bedingungen aus Client-Sicht nicht verfügbar halten kann.

Die Baseline-Phase war in allen Läufen stabil. Auch nach Entfernen der Störung normalisierten sich erfolgreiche Requests wieder auf niedrige Latenzen im Millisekundenbereich. Dennoch war der direkte Übergang in einen stabilen Nachlaufzustand nicht in allen Läufen gegeben. Dies zeigt sich an der niedrigen After-Preflight-Erfolgsrate und an teilweise reduzierten After Success Rates.

Self-Healing findet in diesem Szenario nicht in Form einer sofortigen Wiederherstellung der Anwendungsverfügbarkeit während der Störung statt. Stattdessen zeigt sich ein verzögertes und eingeschränktes Kontrollverhalten: Kubernetes erkennt problematische Zustände, versucht Pods zu planen oder Löschungen rückgängig zu machen, ist aber durch Edge-Taints und Scheduling-Vorgaben begrenzt. Die Wiederherstellung erfolgt erst nach Entfernen der Netzstörung und teilweise mit Verzögerung.

## Endzustand

Nach Abschluss der finalen Messreihe war der Cluster wieder stabil:

* alle Nodes `Ready`
* drei Testapp-Pods `Running`
* NodePort auf `e1` und `e2` wieder erreichbar mit `code=200`
* `tc/netem` auf beiden Router-Interfaces entfernt
* Router-Interfaces wieder mit `fq_codel`

Damit ist die Messreihe vollständig und auswertbar. Die After-Preflight-Warnungen werden als beobachteter Wiederherstellungseffekt dokumentiert und nicht als Messfehler gewertet.

## Kurzfazit

Eine Latenz von `1800s` pro Richtung führt bei KubeEdge zu einem nahezu vollständigen Anwendungsausfall während der Störphase. Die nativen Self-Healing-Mechanismen reagieren zwar sichtbar über Scheduling-, Taint- und Eviction-bezogene Ereignisse, können die Anwendung während der extremen Cloud-Edge-Verzögerung jedoch nicht verfügbar halten. Nach Entfernen der Störung stabilisiert sich der Cluster wieder, allerdings nicht in jedem Lauf innerhalb des kurzen Nachlauf- bzw. After-Preflight-Zeitfensters.
