# KubeEdge Latenztest: 1min

## Szenario

In diesem Szenario wurde auf der Router-VM eine künstliche Netzwerklatenz von `60s` gesetzt. Die Latenz wurde auf dem Interface `ens161` angewendet und beeinflusst damit den Datenpfad zwischen Cloud- und Edge-Seite. Die Messung wurde mit dem asynchronen Request-Monitor und `MAX_IN_FLIGHT=10` durchgeführt.

Die Messreihe umfasst 10 Versuchsläufe.

## Methodische Validierung

Alle 10 Versuchsläufe wurden abgeschlossen. In allen Läufen wurde die Latenz ausschließlich auf dem Router-Interface `ens161` gesetzt.

Validierung über alle Läufe:

- `delay=60s`
- `router_ifaces=ens161`
- `tc_active=yes`
- `tc_cleanup_documented=yes`
- `latency_applied=yes`

Damit ist die Messreihe methodisch konsistent mit den finalen einseitigen KubeEdge-Latenztests und vergleichbarer zu den K3s-Latenztests.

## Request Success Rate und Fehlerrate

Die Baseline war in allen Läufen stabil. Während der Störphase sank die externe Erreichbarkeit der Anwendung deutlich. Nach Entfernen der Latenz erholte sich die Anwendung weitgehend.

| Metrik | Ergebnis |
|---|---:|
| Runs | 10 |
| Overall Success Rate Median | 81.69 % |
| Overall Error Rate Median | 18.31 % |
| Baseline Success Rate Median | 100.00 % |
| Baseline Error Rate Median | 0.00 % |
| Fault Success Rate Median | 22.90 % |
| Fault Error Rate Median | 77.10 % |
| After Success Rate Median | 97.49 % |
| After Error Rate Median | 2.51 % |

## Latenzverhalten und Recovery

Während der Störphase lagen viele Requests nahe am Timeout von ca. 180s. Die p95- und p99-Werte der Störphase zeigen entsprechend sehr hohe Antwortzeiten. Nach Entfernen der Latenz sank die mediane Antwortzeit wieder auf das Niveau der Baseline.

| Metrik | Ergebnis |
|---|---:|
| Baseline Median Latency | 1.27 ms |
| Fault Median Latency | 9568.51 ms |
| Fault p95 Latency | 180930.93 ms |
| Fault p99 Latency | 180997.58 ms |
| After Median Latency | 1.39 ms |
| Recovery Latency Median | 2.05 s |
| Recovery Latency Mean | 7.40 s |
| Recovery Latency Max | 27.41 s |

Die Recovery Time beschreibt hier die Wiederherstellung der extern sichtbaren Anwendungserreichbarkeit nach Entfernen der künstlichen Latenz. Diese erfolgte im Median nach ca. 2.05s. Einzelne Ausreißer führten zu einer höheren mittleren Recovery-Zeit.

## Nachlaufphase

In allen 10 Läufen wurden Requests in der Nachlaufphase erfasst. Es gab keine Läufe mit `after_requests=0`. Die Nachlaufphase ist daher für dieses Szenario aussagekräftig.

| Metrik | Ergebnis |
|---|---:|
| After Requests Median | 179 |
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
| Runs mit allen Nodes Ready im After-Snapshot | 7/10 |
| Runs mit stabilem After-Snapshot | 7/10 |
| NodeNotReady-Event-Lines Median | 17 |
| TaintManager Marking Lines Median | 9 |
| TaintManager Cancel Lines Median | 9 |

In den Läufen `run-02`, `run-03` und `run-10` war im After-Snapshot der Edge-Knoten `e2` noch als `NotReady` sichtbar. Die finale Clusterprüfung nach Abschluss der gesamten Messreihe zeigte jedoch wieder alle Nodes im Zustand `Ready`.

## Bewertung

Die 60s-Latenz führte zu einer deutlichen Beeinträchtigung der extern sichtbaren Anwendungserreichbarkeit. Während der Störphase sank die mediane Success Rate auf 22.90 %, während die mediane Fehlerrate auf 77.10 % anstieg. Nach Entfernen der Latenz erholte sich die Anwendung auf HTTP-Ebene weitgehend; die mediane Success Rate im Nachlauf betrug 97.49 %.

Gleichzeitig löste die Störung interne Clusterreaktionen aus. In allen Läufen wurden NodeNotReady- und TaintManagerEviction-Ereignisse beobachtet, und die drei Testapp-Pods wurden pro Lauf ersetzt. Container-Restarts innerhalb bestehender Pods traten dagegen nicht auf.

Damit zeigt das Szenario eine klare Trennung zwischen externer Wiederherstellung und interner Stabilisierung. Die Anwendung war nach Entfernen der Latenz schnell wieder erreichbar, der Clusterzustand war jedoch nicht in allen Läufen innerhalb der Nachlaufzeit vollständig stabil. Die Stabilisierungszeit kann daher für dieses Szenario nicht in allen Läufen exakt bestimmt werden, sondern wird über den After-Snapshot und die finale Clusterprüfung qualitativ bewertet.
