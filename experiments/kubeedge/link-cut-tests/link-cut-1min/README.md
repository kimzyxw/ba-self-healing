# KubeEdge Verbindungsabbruchtest: 1min

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem Verbindungsabbruch von `1min` zwischen Cloud- und Edge-Netz verhält. Der Verbindungsabbruch wurde auf der Router-VM durch ein temporäres Deaktivieren des Interfaces `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Verbindungsabbrüchen als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein einminütiger Link-Cut Auswirkungen auf die Erreichbarkeit der NGINX-Testanwendung, den Node-Status, Pod-Neuerstellungen, Evictions oder KubeEdge-/Kubernetes-Self-Healing-Mechanismen hat.

## Versuchsaufbau

| Parameter                   |                         Wert |
| --------------------------- | ---------------------------: |
| System                      |                     KubeEdge |
| Szenario                    |              `link-cut-1min` |
| Anzahl Läufe                |                         `10` |
| Verbindungsabbruch          |                        `60s` |
| Fault-Typ                   |            `ip_link_down_up` |
| Router-Interface            |                     `ens161` |
| Vorlaufphase                |                       `180s` |
| Störphase                   |                        `60s` |
| Nachlaufphase               |                       `180s` |
| HTTP-Timeout                |                       `300s` |
| Request-Intervall           |                         `1s` |
| Maximale parallele Requests |                         `10` |
| Ziel-URL                    | `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Verbindungsabbruch wurde zentral auf der Router-VM ausgelöst, indem das Interface `ens161` für die Dauer der Störphase deaktiviert und anschließend wieder aktiviert wurde.

## Validierung der Testdurchführung

| Validierung                  | Ergebnis |
| ---------------------------- | -------: |
| Ausgewertete Läufe           |  `10/10` |
| Routerpfad gültig            |  `10/10` |
| Link-Cut angewendet          |  `10/10` |
| Interface wiederhergestellt  |  `10/10` |
| Router-Recovery dokumentiert |  `10/10` |

Die Messreihe ist vollständig und methodisch sauber auswertbar. In allen zehn Läufen war der Routerpfad gültig. Der Verbindungsabbruch wurde in allen Läufen erfolgreich gesetzt, und `interface_during_fault.txt` dokumentierte jeweils den Zustand `state DOWN`. Nach Ende der Störphase wurde das Interface in allen Läufen wieder in den Zustand `state UP` versetzt. Zusätzlich wurde die Wiederherstellung im Router-Log dokumentiert.

Der finale Clusterzustand war stabil: Alle Nodes waren `Ready`, die Testanwendung lief mit drei Pods im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                           |      Wert |
| -------------------------------- | --------: |
| Overall Success Rate, Median     | `100.00%` |
| Overall Success Rate, Mittelwert | `100.00%` |
| Overall Error Rate, Median       |   `0.00%` |
| Overall Error Rate, Mittelwert   |   `0.00%` |
| Overall Median Latenz            |  `1.41ms` |
| Overall p95 Latenz               |  `2.71ms` |
| Overall p99 Latenz               |  `4.92ms` |
| Overall max. Latenz, Median      | `37.89ms` |
| Overall Timeouts gesamt          |       `0` |
| Baseline Success Rate, Median    | `100.00%` |
| Baseline Median Latenz           |  `1.36ms` |
| Baseline p95 Latenz              |  `1.96ms` |
| Fault Success Rate, Median       | `100.00%` |
| Fault Success Rate, Mittelwert   | `100.00%` |
| Fault Error Rate, Median         |   `0.00%` |
| Fault Error Rate, Mittelwert     |   `0.00%` |
| Fault Median Latenz              |  `1.82ms` |
| Fault p95 Latenz                 |  `4.09ms` |
| Fault p99 Latenz                 |  `6.31ms` |
| Fault max. Latenz, Median        |  `6.31ms` |
| Fault Timeouts gesamt            |       `0` |
| After Success Rate, Median       | `100.00%` |
| After Median Latenz              |  `1.34ms` |
| After p95 Latenz                 |  `2.80ms` |
| After p99 Latenz                 |  `5.05ms` |
| Recovery Time, Minimum           |   `0.01s` |
| Recovery Time, Median            |   `0.44s` |
| Recovery Time, Mittelwert        |   `0.43s` |
| Recovery Time, Maximum           |   `0.92s` |

## Beobachtungen zur Anwendungserreichbarkeit

Die NGINX-Testanwendung blieb während der gesamten Messreihe erreichbar. Sowohl insgesamt als auch in der Baseline-, Fault- und Nachlaufphase lag die Success Rate bei `100.00%`. Es wurden keine fehlgeschlagenen HTTP-Requests und keine Timeouts beobachtet.

Während der Störphase stieg die mediane Latenz leicht von `1.36ms` in der Baseline auf `1.82ms` während des Faults. Auch die oberen Perzentile blieben niedrig: Der Fault-p95 lag bei `4.09ms`, der Fault-p99 bei `6.31ms`, und die maximale Fault-Latenz lag im Median ebenfalls bei `6.31ms`.

Damit führte ein Verbindungsabbruch von `1min` in dieser Testumgebung nicht zu einer sichtbaren Beeinträchtigung der Anwendungserreichbarkeit, obwohl auf Cluster-Ebene deutliche Zustandsänderungen sichtbar wurden.

## Kubernetes- und KubeEdge-Ereignisse

In allen zehn Läufen wurden auffällige Kubernetes-/KubeEdge-Ereignisse beobachtet. Dabei wurden jeweils die Edge-Nodes `e1` und `e2` als `NodeNotReady` gemeldet. Zusätzlich wurden KubeEdge-nahe Komponenten wie `edge-eclipse-mosquitto` und `edgemesh-agent` mit `NodeNotReady`-Warnungen erfasst.

Auch die Pods der NGINX-Testanwendung wurden in allen Läufen mit `NodeNotReady`-Warnungen erfasst, da sie auf `e1` liefen und dieser Node während der Störung zeitweise als nicht bereit eingestuft wurde.

Zusätzlich trat in allen Läufen `TaintManagerEviction` auf. Dabei wurde jedoch jeweils `Cancelling deletion` für die drei Pods der Testanwendung dokumentiert. Das bedeutet, dass die Löschung der Pods zwar eingeleitet bzw. vorbereitet wurde, nach Wiederherstellung des Nodes aber wieder abgebrochen wurde.

## Pod-Verhalten

Die drei Pods der NGINX-Testanwendung blieben in allen zehn Läufen identisch. Es wurden keine Pod-Neuerstellungen, keine Pod-Restarts und kein tatsächliches Rescheduling beobachtet.

Die Pods liefen durchgehend auf `e1`:

* `nginx-testapp-5c8f4cb9d7-dj67m`
* `nginx-testapp-5c8f4cb9d7-dnm2w`
* `nginx-testapp-5c8f4cb9d7-ww6hl`

Obwohl `NodeNotReady`- und `TaintManagerEviction`-Events auftraten, blieb die Testanwendung stabil. Die dokumentierten `Cancelling deletion`-Events zeigen, dass die angestoßenen Eviction- bzw. Löschprozesse nach Rückkehr des Nodes abgebrochen wurden, bevor es zu tatsächlichen Pod-Ersetzungen kam.

## Beobachtetes Self-Healing-Verhalten

Bei einem Verbindungsabbruch von `1min` wurden sichtbare Kubernetes-/KubeEdge-Reaktionen ausgelöst. Im Gegensatz zum `1s`-Szenario traten die `NodeNotReady`-Events nicht nur vereinzelt, sondern in allen zehn Läufen auf. Auch die Testapp-Pods waren von `NodeNotReady`-Warnungen betroffen.

Auf Anwendungsebene kam es jedoch nicht zu einer Unterbrechung. Die Request Success Rate blieb bei `100.00%`, und die Pods der Testanwendung blieben unverändert. Damit wurde zwar auf Cluster-Ebene ein Self-Healing-naher Mechanismus sichtbar, insbesondere durch Node-Zustandsänderungen, Tainting und TaintManager-Aktivität, aber es war keine vollständige Pod-Neuerstellung oder ein Rescheduling erforderlich.

Das beobachtete Verhalten lässt sich daher als kurzfristige Zustandsreaktion mit erfolgreicher Stabilisierung interpretieren, nicht als klassische Wiederherstellung nach einem Anwendungsausfall.

## Interpretation

Der `1min`-Verbindungsabbruch war technisch eindeutig vorhanden und wurde in allen Läufen dokumentiert. Im Unterschied zum `1s`-Szenario war die Störung lang genug, um in jedem Lauf `NodeNotReady`-Events für die Edge-Nodes auszulösen. Auch KubeEdge-Komponenten und die Testapp-Pods wurden zeitweise als von nicht bereiten Nodes betroffen gemeldet.

Trotzdem blieb die Anwendung erreichbar. Eine mögliche Erklärung ist, dass die Testanwendung während der Unterbrechung auf dem Edge-Node weiterlief und die Service-Erreichbarkeit über den NodePort weiterhin gegeben war. Gleichzeitig war die Störung kurz genug, dass eingeleitete Eviction- bzw. Löschprozesse nach Wiederherstellung des Nodes wieder abgebrochen wurden. Dies zeigt sich an den `Cancelling deletion`-Events.

Die Recovery Time ist auch in diesem Szenario nicht als klassische MTTR nach einem Serviceausfall zu interpretieren, da kein Anwendungsausfall beobachtet wurde. Sie beschreibt vielmehr den Zeitpunkt des ersten erfolgreichen Requests nach dokumentierter Wiederherstellung des Router-Interfaces.

## Vergleich zum 1s-Verbindungsabbruch

Im Vergleich zum `1s`-Szenario zeigt der `1min`-Test deutlich stärkere Cluster-Reaktionen. Während bei `1s` nur in den ersten vier Läufen `NodeNotReady`-Events beobachtet wurden, traten diese bei `1min` in allen zehn Läufen auf. Zusätzlich waren bei `1min` auch die Pods der Testanwendung in allen Läufen von `NodeNotReady`-Warnungen betroffen.

Die Anwendungserreichbarkeit blieb jedoch in beiden Szenarien vollständig erhalten. In beiden Fällen lag die Request Success Rate bei `100.00%`, und es traten keine Timeouts auf.

## Fazit

Ein Verbindungsabbruch von `1min` wurde in allen zehn Läufen erfolgreich erzeugt und dokumentiert. Die Anwendung blieb trotz der Störung vollständig erreichbar: Die Request Success Rate lag in allen Phasen bei `100.00%`, es traten keine Timeouts auf, und die Testapp-Pods blieben unverändert im Zustand `Running`.

Auf Cluster-Ebene waren die Auswirkungen jedoch deutlich sichtbar. In allen Läufen wurden `e1` und `e2` als `NodeNotReady` gemeldet, und auch die Pods der Testanwendung erhielten entsprechende Warnungen. Der TaintManager wurde aktiv, brach die Löschung der Pods nach Wiederherstellung des Nodes jedoch wieder ab.

Das Szenario zeigt damit, dass KubeEdge einen einminütigen Verbindungsabbruch auf Anwendungsebene vollständig tolerierte, während auf Cluster-/Edge-Ebene bereits deutliche Self-Healing-nahe Zustandsreaktionen sichtbar wurden.
