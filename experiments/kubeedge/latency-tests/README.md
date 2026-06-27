# KubeEdge Latenztests

## Überblick

Dieses Verzeichnis enthält die finalen KubeEdge-Latenztests. Ziel der Messreihe war es, das Verhalten der Anwendung und des KubeEdge-Clusters unter künstlich erhöhter Netzwerklatenz zwischen Cloud- und Edge-Seite zu untersuchen.

Die Latenz wurde auf der Router-VM mithilfe von `tc/netem` gesetzt. In der finalen Messreihe wurde ausschließlich das Router-Interface `ens161` verwendet. Damit entspricht die Versuchsdurchführung methodisch dem finalen einseitigen Netzwerkpfad und ist vergleichbarer zu den K3s-Latenztests.

Untersuchte Szenarien:

| Szenario | Delay | Runs |
|---|---:|---:|
| `latency-1s-async-limited` | 1s | 10 |
| `latency-1min-async-limited` | 60s | 10 |
| `latency-10min-async-limited` | 600s | 10 |
| `latency-30min-async-limited` | 1800s | 10 |

Alle Szenarien wurden mit dem asynchronen Request-Monitor und `MAX_IN_FLIGHT=10` durchgeführt.

## Methodische Validierung

Für alle finalen Latenzszenarien wurden 10 Versuchsläufe ausgewertet. Die Latenz wurde jeweils auf `ens161` gesetzt.

| Szenario | Delay | Router-Interface | `latency_applied` | Hinweis |
|---|---:|---|---|---|
| 1s | 1s | `ens161` | yes | valide |
| 1min | 60s | `ens161` | yes | valide |
| 10min | 600s | `ens161` | yes | valide |
| 30min | 1800s | `ens161` | yes | `tc_active` als Parsing-Artefakt |

Beim 30min-Szenario wurde `tc_active` in der automatisch erzeugten Summary als `no` ausgegeben. Die zugehörigen `tc_during.txt`-Dateien zeigen jedoch eine aktive netem-Regel auf `ens161` mit `delay 1.8e+03s`. Dies entspricht `1800s`. Da zusätzlich `latency_applied=yes` gesetzt ist, wird dies als Parsing-Artefakt der Validierung bewertet und nicht als fehlgeschlagene Latenzinjektion.

## Vergleich der wichtigsten Metriken

| Szenario | Fault Success Median | Fault Error Median | After Success Median | Recovery Median | Pod-Ersetzungen | Stable After Snapshot |
|---|---:|---:|---:|---:|---:|---:|
| 1s | 100.00 % | 0.00 % | 100.00 % | 1.18 s | 0/10 | 10/10 |
| 1min | 22.90 % | 77.10 % | 97.49 % | 2.05 s | 10/10 | 7/10 |
| 10min | 2.62 % | 97.38 % | 98.31 % | 3.41 s | 10/10 | 8/10 |
| 30min | 3.12 % | 96.88 % | 96.33 % | 3.77 s | 10/10 | 6/10 |

## Request Success Rate und Fehlerrate

Die Baseline war in allen Szenarien stabil. Für alle vier Latenzstufen betrug die mediane Baseline Success Rate 100 %.

Bei 1s zusätzlicher Latenz blieb die Anwendung während der Störphase vollständig erreichbar. Die mediane Fault Success Rate lag bei 100 %, die mediane Fault Error Rate bei 0 %. Die Latenz wirkte sich damit zwar auf die Antwortzeit aus, führte aber nicht zu einer messbaren Dienstunterbrechung.

Ab 1min Latenz änderte sich das Verhalten deutlich. Die mediane Fault Success Rate sank auf 22.90 %, während die mediane Fault Error Rate auf 77.10 % stieg. Bei 10min und 30min Latenz war die Anwendung während der Störphase nahezu nicht mehr extern erreichbar. Die mediane Fault Success Rate betrug nur noch 2.62 % bzw. 3.12 %.

Nach Entfernen der Latenz erholte sich die Anwendung in allen Szenarien deutlich. Die mediane After Success Rate lag bei 1min bei 97.49 %, bei 10min bei 98.31 % und bei 30min bei 96.33 %.

## Recovery Time / MTTR

Die Recovery Time beschreibt hier die Wiederherstellung der extern sichtbaren Anwendungserreichbarkeit nach Entfernen der künstlichen Latenz.

| Szenario | Recovery Median | Recovery Mean | Recovery Max |
|---|---:|---:|---:|
| 1s | 1.18 s | 1.23 s | 1.63 s |
| 1min | 2.05 s | 7.40 s | 27.41 s |
| 10min | 3.41 s | 8.62 s | 26.47 s |
| 30min | 3.77 s | 5.76 s | 16.24 s |

Die externe Recovery erfolgte nach Entfernen der Störung in allen Szenarien im Median innerhalb weniger Sekunden. Bei 1min und 10min traten jedoch einzelne Ausreißer auf, wodurch die mittlere Recovery-Zeit deutlich über dem Median lag.

## Stabilisierungszeit

Die Stabilisierungszeit konnte in den Latenzszenarien nicht durchgängig als exakte Dauer bestimmt werden, da der After-Snapshot nicht in allen Läufen bereits einen vollständig stabilen Clusterzustand zeigte.

| Szenario | Stable After Snapshot |
|---|---:|
| 1s | 10/10 |
| 1min | 7/10 |
| 10min | 8/10 |
| 30min | 6/10 |

Beim 1s-Szenario waren alle Testapp-Pods und alle Nodes in allen Läufen im After-Snapshot stabil. Ab 1min Latenz traten dagegen interne Clusterreaktionen auf. In mehreren Läufen war insbesondere der Edge-Knoten `e2` im After-Snapshot noch als `NotReady` sichtbar.

Damit ist zwischen externer Recovery und interner Stabilisierung zu unterscheiden: Die Anwendung war nach Entfernen der Latenz auf HTTP-Ebene wieder weitgehend erreichbar, während der interne Clusterzustand in einigen Läufen noch nicht vollständig stabil war.

## Pod-Restarts und Pod-Ersetzungen

In keinem der Latenzszenarien wurden Container-Restarts innerhalb bestehender Testapp-Pods beobachtet. Das Container-Restart-Delta lag jeweils bei 0.

Gleichzeitig traten ab 1min Latenz Pod-Ersetzungen auf:

| Szenario | Runs mit Pod-Ersetzungen | Container-Restart-Delta Median |
|---|---:|---:|
| 1s | 0/10 | 0 |
| 1min | 10/10 | 0 |
| 10min | 10/10 | 0 |
| 30min | 10/10 | 0 |

Damit ist methodisch zwischen Container-Restarts und Pod-Ersetzungen zu unterscheiden. Die beobachtete Self-Healing-Reaktion bestand ab 1min Latenz nicht in Neustarts bestehender Container, sondern in der Ersetzung der Testapp-Pods infolge interner Clusterreaktionen.

## Node-Status und Events

Bereits im 1s-Szenario wurden einzelne NodeNotReady-Event-Lines erfasst, jedoch ohne Pod-Ersetzungen und ohne instabilen After-Snapshot. Ab 1min Latenz waren die Clusterreaktionen deutlich ausgeprägter.

| Szenario | NodeNotReady-Event-Lines Median | TaintManager Marking Lines Median |
|---|---:|---:|
| 1s | 4 | 0 |
| 1min | 17 | 9 |
| 10min | 17 | 9 |
| 30min | 17 | 9 |

Ab 1min Latenz traten in allen Szenarien NodeNotReady- und TaintManagerEviction-Ereignisse auf. Diese Ereignisse stehen im Zusammenhang mit den beobachteten Pod-Ersetzungen. Die Störung der Cloud-Edge-Kommunikation führte somit nicht nur zu erhöhten Antwortzeiten, sondern auch zu internen Kontroll- und Scheduling-Reaktionen des Clusters.

## Bewertung

Die KubeEdge-Latenztests zeigen einen klaren Schwelleneffekt. Eine zusätzliche Latenz von 1s beeinträchtigte die externe Dienstverfügbarkeit nicht. Die Anwendung blieb während der Störphase vollständig erreichbar, und es wurden keine Pod-Ersetzungen beobachtet.

Ab 1min Latenz verschlechterte sich die externe Dienstverfügbarkeit deutlich. Die mediane Fault Success Rate sank auf 22.90 %. Gleichzeitig traten NodeNotReady- und TaintManagerEviction-Ereignisse auf, und die Testapp-Pods wurden in allen Läufen ersetzt. Bei 10min und 30min Latenz war die Anwendung während der Störphase nahezu vollständig nicht mehr erreichbar.

Nach Entfernen der Latenz erholte sich die Anwendung auf HTTP-Ebene in allen Szenarien deutlich. Die mediane After Success Rate lag bei den längeren Latenzen zwischen 96.33 % und 98.31 %. Die Recovery Time lag im Median jeweils im Bereich weniger Sekunden.

Für die Self-Healing-Bewertung ist jedoch die Trennung zwischen externer Wiederherstellung und interner Stabilisierung zentral. Während die Anwendung nach Entfernen der Störung schnell wieder erreichbar war, zeigte der Cluster ab 1min Latenz interne Reaktionen wie NodeNotReady-Events, TaintManagerEviction und Pod-Ersetzungen. In mehreren Läufen war der Cluster im After-Snapshot noch nicht vollständig stabil.

Insgesamt zeigen die KubeEdge-Latenztests, dass KubeEdge bei kurzer zusätzlicher Latenz robust bleibt, bei längeren Cloud-Edge-Verzögerungen jedoch starke Einbußen der externen Dienstverfügbarkeit und deutliche interne Self-Healing-Reaktionen auftreten. Die externe Anwendungserreichbarkeit wird nach Entfernen der Störung schnell wiederhergestellt, während die vollständige interne Stabilisierung teilweise länger als die beobachtete Nachlaufphase dauern kann.
