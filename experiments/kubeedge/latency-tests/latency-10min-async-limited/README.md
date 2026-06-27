# KubeEdge Latenztest: 10min

## Szenario

In diesem Szenario wurde auf der Router-VM eine künstliche Netzwerklatenz von `600s` gesetzt. Die Latenz wurde auf dem Interface `ens161` angewendet und beeinflusst damit den Datenpfad zwischen Cloud- und Edge-Seite. Die Messung wurde mit dem asynchronen Request-Monitor und `MAX_IN_FLIGHT=10` durchgeführt.

Die Messreihe umfasst 10 Versuchsläufe.

## Methodische Validierung

Alle 10 Versuchsläufe wurden abgeschlossen. In allen Läufen wurde die Latenz ausschließlich auf dem Router-Interface `ens161` gesetzt.

Validierung über alle Läufe:

- `delay=600s`
- `router_ifaces=ens161`
- `tc_active=yes`
- `tc_cleanup_documented=yes`
- `latency_applied=yes`

Damit ist die Messreihe methodisch konsistent mit den finalen einseitigen KubeEdge-Latenztests und vergleichbarer zu den K3s-Latenztests.

## Request Success Rate und Fehlerrate

Die Baseline war in allen Läufen stabil. Während der Störphase war die externe Erreichbarkeit der Anwendung nahezu vollständig eingeschränkt. Nach Entfernen der Latenz erholte sich die Anwendung weitgehend.

| Metrik | Ergebnis |
|---|---:|
| Runs | 10 |
| Overall Success Rate Median | 61.73 % |
| Overall Error Rate Median | 38.27 % |
| Baseline Success Rate Median | 100.00 % |
| Baseline Error Rate Median | 0.00 % |
| Fault Success Rate Median | 2.62 % |
| Fault Error Rate Median | 97.38 % |
| After Success Rate Median | 98.31 % |
| After Error Rate Median | 1.69 % |

## Latenzverhalten und Recovery

Während der Störphase lagen viele Requests im Bereich sehr langer Antwortzeiten beziehungsweise nahe am Timeout. Nach Entfernen der Latenz sank die mediane Antwortzeit wieder auf das Niveau der Baseline.

| Metrik | Ergebnis |
|---|---:|
| Baseline Median Latency | 1.32 ms |
| Fault Median Latency | 4106.44 ms |
| Fault p95 Latency | 135189.96 ms |
| Fault p99 Latency | 136333.01 ms |
| After Median Latency | 1.49 ms |
| Recovery Latency Median | 3.41 s |
| Recovery Latency Mean | 8.62 s |
| Recovery Latency Max | 26.47 s |

Die Recovery Time beschreibt hier die Wiederherstellung der extern sichtbaren Anwendungserreichbarkeit nach Entfernen der künstlichen Latenz. Diese erfolgte im Median nach ca. 3.41s. Einzelne Ausreißer führten zu einer höheren mittleren Recovery-Zeit.

## Nachlaufphase

In allen 10 Läufen wurden Requests in der Nachlaufphase erfasst. Es gab keine Läufe mit `after_requests=0`. Die Nachlaufphase ist daher für dieses Szenario aussagekräftig.

| Metrik | Ergebnis |
|---|---:|
| After Requests Median | 177 |
| Runs mit `after_requests=0` | 0/10 |

## Pod-Restarts und Pod-Ersetzungen

In den Testapp-Pods wurden keine Container-Restarts beobachtet. Gleichzeitig wurden in allen 10 Läufen die drei Testapp-Pods ersetzt.

| Metrik | Ergebnis |
|---|---:|
| Runs mit Pod-Namensänderungen | 10/10 |
| Entfernte Testapp-Pods pro Run | 3 |
| Neue Testapp-Pods pro Run | 3 |
| Container-Restart-Delta | 0 |

Damit ist zwischen Container-Restarts und Pod-Ersetzungen zu unterscheiden. Die beobachtete Reaktion bestand nicht in Neustarts bestehender Container, sondern in der Ersetzung der Pods infolge interner Clusterreaktionen.

## Node-Status und Ereignisse

Während der Messreihe wurden NodeNotReady-Ereignisse auf den Edge-Knoten beobachtet. Außerdem traten TaintManagerEviction-Ereignisse auf, die mit der beobachteten Pod-Ersetzung zusammenhängen.

| Metrik | Ergebnis |
|---|---:|
| Runs mit allen Nodes Ready im After-Snapshot | 8/10 |
| Runs mit stabilem After-Snapshot | 8/10 |
| NodeNotReady-Event-Lines Median | 17 |
| TaintManager Marking Lines Median | 9 |
| TaintManager Cancel Lines Median | 9 |

In den Läufen `run-03` und `run-05` war im After-Snapshot der Edge-Knoten `e2` noch als `NotReady` sichtbar. Die finale Clusterprüfung nach Abschluss der gesamten Messreihe zeigte jedoch wieder alle Nodes im Zustand `Ready`.

## Bewertung

Die 600s-Latenz führte während der Störphase zu einer nahezu vollständigen Einschränkung der extern sichtbaren Anwendungserreichbarkeit. Die mediane Fault Success Rate betrug nur 2.62 %, während die mediane Fehlerrate auf 97.38 % anstieg. Nach Entfernen der Latenz erholte sich die Anwendung auf HTTP-Ebene deutlich; die mediane Success Rate im Nachlauf betrug 98.31 %.

Gleichzeitig löste die Störung interne Clusterreaktionen aus. In allen Läufen wurden NodeNotReady- und TaintManagerEviction-Ereignisse beobachtet, und die drei Testapp-Pods wurden pro Lauf ersetzt. Container-Restarts innerhalb bestehender Pods traten dagegen nicht auf.

Damit zeigt das Szenario eine klare Trennung zwischen externer Wiederherstellung und interner Stabilisierung. Die Anwendung war nach Entfernen der Latenz im Median nach wenigen Sekunden wieder erreichbar, der Clusterzustand war jedoch nicht in allen Läufen innerhalb der Nachlaufzeit vollständig stabil. Die Stabilisierungszeit kann daher für dieses Szenario nicht in allen Läufen exakt bestimmt werden, sondern wird über den After-Snapshot und die finale Clusterprüfung qualitativ bewertet.
