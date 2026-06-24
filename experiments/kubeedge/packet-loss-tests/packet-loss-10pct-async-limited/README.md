# KubeEdge Paketverlusttest: 10 %

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem Paketverlust von `10%` zwischen Cloud- und Edge-Netz verhält. Der Paketverlust wurde auf der Router-VM mit `tc/netem` auf dem Interface `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Paketverlusttests als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein moderater Paketverlust bereits Auswirkungen auf die Erreichbarkeit der Testanwendung oder auf Kubernetes-/KubeEdge-interne Self-Healing-Mechanismen hat. Dabei wurde insbesondere betrachtet, ob Nodes als `NotReady` markiert werden, Pods neu gestartet werden oder Scheduling-, Eviction- oder sonstige Wiederherstellungsmechanismen sichtbar werden.

## Versuchsaufbau

| Parameter                   |                              Wert |
| --------------------------- | --------------------------------: |
| System                      |                          KubeEdge |
| Szenario                    | `packet-loss-10pct-async-limited` |
| Anzahl Läufe                |                              `10` |
| Paketverlust                |                             `10%` |
| Router-Interface            |                          `ens161` |
| Vorlaufphase                |                            `180s` |
| Störphase                   |                            `600s` |
| Nachlaufphase               |                            `180s` |
| HTTP-Timeout                |                            `300s` |
| Request-Intervall           |                              `1s` |
| Maximale parallele Requests |                              `10` |
| Ziel-URL                    |      `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Paketverlust wurde auf der Router-VM zentral eingebracht, sodass der Verkehr zwischen Cloud- und Edge-Netz über den gestörten Routerpfad lief.

## Validierung der Testdurchführung

| Validierung                       | Ergebnis |
| --------------------------------- | -------: |
| Ausgewertete Läufe                |  `10/10` |
| Routerpfad gültig                 |  `10/10` |
| Paketverlust aktiv                |  `10/10` |
| `tc/netem` nach dem Lauf entfernt |  `10/10` |
| After-Preflight erfolgreich       |  `10/10` |

Die Messreihe ist vollständig und methodisch sauber auswertbar. In allen zehn Läufen wurde der Routerpfad korrekt validiert, der Paketverlust mit `tc/netem loss 10%` erfolgreich aktiviert und nach der Störphase wieder entfernt. Auch der After-Preflight war in allen Läufen erfolgreich.

Der Cluster befand sich nach Abschluss der Messreihe wieder in einem stabilen Zustand. Alle Nodes waren `Ready`, die drei Pods der Testanwendung liefen weiterhin im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                        |       Wert |
| ----------------------------- | ---------: |
| Overall Success Rate, Median  |  `100.00%` |
| Overall Error Rate, Median    |    `0.00%` |
| Overall Median Latenz         |   `1.17ms` |
| Overall p95 Latenz            | `204.50ms` |
| Overall p99 Latenz            | `210.14ms` |
| Overall max. Latenz, Median   | `419.43ms` |
| Baseline Success Rate, Median |  `100.00%` |
| Baseline Median Latenz        |   `1.10ms` |
| Baseline p95 Latenz           |   `1.58ms` |
| Baseline p99 Latenz           |   `2.15ms` |
| Fault Success Rate, Median    |  `100.00%` |
| Fault Error Rate, Median      |    `0.00%` |
| Fault Median Latenz           |   `1.21ms` |
| Fault p95 Latenz              | `207.77ms` |
| Fault p99 Latenz              | `212.18ms` |
| Fault max. Latenz, Median     | `419.43ms` |
| Fault Timeouts gesamt         |        `0` |
| After Success Rate, Median    |  `100.00%` |
| After Median Latenz           |   `1.10ms` |
| Recovery Time, Median         |    `0.48s` |
| Recovery Time, Maximum        |    `0.91s` |

## Beobachtungen

Während der gesamten Messreihe blieb die Testanwendung vollständig erreichbar. Sowohl in der Baseline-Phase als auch während der aktiven Paketverlustphase und in der Nachlaufphase lag die mediane Erfolgsrate bei `100.00%`. Es traten keine HTTP-Fehler und keine Timeouts auf.

Im Vergleich zum Paketverlusttest mit `1%` sind die Auswirkungen auf die Latenz deutlicher sichtbar. Während der Median der Fault-Latenz mit `1.21ms` weiterhin sehr niedrig blieb, stiegen die oberen Perzentile deutlich an. Der Fault-p95 lag im Median bei `207.77ms`, der Fault-p99 bei `212.18ms`, und die maximale Fault-Latenz lag im Median bei `419.43ms`.

Damit zeigt sich, dass der Paketverlust durch TCP-Neuübertragungen oder kurzfristige Verzögerungen messbar wird, ohne die Verfügbarkeit der Anwendung zu beeinträchtigen.

## Kubernetes- und KubeEdge-Ereignisse

In den Event-Dateien wurden keine auffälligen Ereignisse gefunden. Insbesondere wurden keine Hinweise auf folgende Zustände oder Mechanismen beobachtet:

* keine `NodeNotReady`-Zustände
* keine `Unhealthy`-Events
* keine `Killing`-Events
* keine `BackOff`-Zustände
* keine `Failed`-Events
* keine Evictions
* keine Taints durch Node-Probleme
* kein Rescheduling der Testanwendung

Die drei Pods der Testanwendung liefen nach Abschluss der Messreihe weiterhin stabil auf `e1` und zeigten keine Restarts.

## Beobachtetes Self-Healing-Verhalten

Bei `10%` Paketverlust wurden keine sichtbaren Self-Healing-Mechanismen ausgelöst. Der Cluster blieb aus Sicht von Kubernetes und KubeEdge stabil genug, sodass keine Reparaturmaßnahmen erforderlich waren.

Das bedeutet nicht, dass Self-Healing versagt hat, sondern dass die Störung unterhalb der Schwelle lag, bei der Kubernetes oder KubeEdge den Zustand als fehlerhaft einstufen. Die Anwendung blieb erreichbar, die Edge-Nodes blieben `Ready`, und es gab keine Hinweise auf Pod-bezogene Wiederherstellungsmaßnahmen.

Die beobachtete Stabilität ist daher vor allem auf die Robustheit der Netzwerk- und Transportebene zurückzuführen. Einzelne Paketverluste wurden offenbar kompensiert, ohne dass Kubernetes-seitige Recovery-Mechanismen eingreifen mussten.

## Interpretation

Der Test zeigt, dass KubeEdge bei `10%` Paketverlust weiterhin stabil arbeitet. Die Anwendung war in allen zehn Läufen vollständig verfügbar. Die Störung beeinflusste vor allem die oberen Latenzperzentile, nicht jedoch die Erfolgsrate.

Im Vergleich zum `1%`-Szenario ist der Effekt auf die Latenz deutlich stärker: Während bei `1%` Paketverlust nur einzelne kleinere Ausreißer sichtbar waren, erzeugt `10%` Paketverlust regelmäßig Latenzspitzen im Bereich von etwa `200ms`. Diese Verzögerungen bleiben jedoch begrenzt und führen nicht zu Timeouts.

Im Hinblick auf Self-Healing ist das Ergebnis erneut ein Negativbefund: Es wurden keine Self-Healing-Mechanismen sichtbar, weil kein Zustand erreicht wurde, der aus Sicht des Systems eine Wiederherstellung erfordert hätte.

## Vergleichbare Einordnung

Das Verhalten entspricht der Erwartung aus den K3s-Paketverlusttests. Auch dort blieb die Anwendung bei `10%` Paketverlust vollständig erreichbar, während hauptsächlich erhöhte Latenzspitzen beobachtet wurden. Für beide Systeme stellt `10%` Paketverlust damit eine messbare, aber noch nicht kritisch wirkende Netzwerkstörung dar.

## Fazit

Ein Paketverlust von `10%` beeinträchtigt die KubeEdge-Testumgebung messbar durch erhöhte Latenzspitzen, führt jedoch nicht zu HTTP-Fehlern, Timeouts oder sichtbaren Kubernetes-/KubeEdge-Self-Healing-Reaktionen.

Die Anwendung blieb in allen zehn Läufen vollständig verfügbar. Alle Nodes blieben `Ready`, die Pods liefen stabil weiter, und es wurden keine auffälligen Events beobachtet. Damit liegt `10%` Paketverlust in der untersuchten Umgebung noch unterhalb der Schwelle, bei der KubeEdge Self-Healing-Mechanismen sichtbar aktiviert.
