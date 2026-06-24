# KubeEdge Paketverlusttest: 50 %

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem Paketverlust von `50%` zwischen Cloud- und Edge-Netz verhält. Der Paketverlust wurde auf der Router-VM mit `tc/netem` auf dem Interface `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Paketverlusttests als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ab welcher Störintensität KubeEdge sichtbare Self-Healing-Mechanismen aktiviert. Im Fokus standen die Erreichbarkeit der NGINX-Testanwendung, Änderungen im Node-Status, Pod-Neuerstellungen, Evictions, Scheduling-Verhalten und die Wiederherstellung eines stabilen Clusterzustands nach Ende der Störung.

## Versuchsaufbau

| Parameter                   |                              Wert |
| --------------------------- | --------------------------------: |
| System                      |                          KubeEdge |
| Szenario                    | `packet-loss-50pct-async-limited` |
| Anzahl Läufe                |                              `10` |
| Paketverlust                |                             `50%` |
| Router-Interface            |                          `ens161` |
| Vorlaufphase                |                            `180s` |
| Störphase                   |                            `600s` |
| Nachlaufphase               |                            `180s` |
| HTTP-Timeout                |                            `300s` |
| Request-Intervall           |                              `1s` |
| Maximale parallele Requests |                              `10` |
| Ziel-URL                    |      `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Paketverlust wurde zentral auf der Router-VM eingebracht, sodass der Verkehr zwischen Cloud- und Edge-Netz über den gestörten Routerpfad lief.

## Validierung der Testdurchführung

| Validierung                       | Ergebnis |
| --------------------------------- | -------: |
| Ausgewertete Läufe                |  `10/10` |
| Routerpfad gültig                 |  `10/10` |
| Paketverlust aktiv                |  `10/10` |
| `tc/netem` nach dem Lauf entfernt |  `10/10` |
| After-Preflight erfolgreich       |   `6/10` |

Die Messreihe ist vollständig und auswertbar. In allen zehn Läufen wurde der Paketverlust erfolgreich mit `tc/netem loss 50%` aktiviert und nach der Störphase wieder entfernt. Der Routerpfad war in allen Läufen gültig, und das Cleanup wurde in allen Läufen dokumentiert.

Auffällig ist, dass der After-Preflight nur in `6/10` Läufen erfolgreich war. Dies weist darauf hin, dass der Cluster unmittelbar nach der Störphase nicht in allen Läufen sofort vollständig stabil war. Der abschließende Clusterzustand war jedoch wieder stabil: Alle Nodes waren `Ready`, die Testanwendung lief mit drei Pods im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                           |         Wert |
| -------------------------------- | -----------: |
| Overall Success Rate, Median     |    `100.00%` |
| Overall Success Rate, Mittelwert |     `97.76%` |
| Overall Error Rate, Median       |      `0.00%` |
| Overall Error Rate, Mittelwert   |      `2.24%` |
| Overall Median Latenz            |     `1.82ms` |
| Overall p95 Latenz               |  `1137.15ms` |
| Overall p99 Latenz               |  `6561.34ms` |
| Overall max. Latenz, Median      | `61657.86ms` |
| Baseline Success Rate, Median    |    `100.00%` |
| Baseline Median Latenz           |     `1.41ms` |
| Baseline p95 Latenz              |     `2.02ms` |
| Fault Success Rate, Median       |    `100.00%` |
| Fault Success Rate, Mittelwert   |     `99.23%` |
| Fault Error Rate, Median         |      `0.00%` |
| Fault Error Rate, Mittelwert     |      `0.77%` |
| Fault Median Latenz              |   `203.30ms` |
| Fault p95 Latenz                 |  `1689.60ms` |
| Fault p99 Latenz                 |  `6651.35ms` |
| Fault max. Latenz, Median        | `61657.86ms` |
| Fault Timeouts gesamt            |          `0` |
| After Success Rate, Median       |    `100.00%` |
| After Success Rate, Mittelwert   |     `92.35%` |
| After Median Latenz              |     `1.50ms` |
| Recovery Time, Median            |      `0.42s` |
| Recovery Time, Maximum           |      `1.00s` |

## Beobachtungen zur Anwendungserreichbarkeit

Bei `50%` Paketverlust blieb die Testanwendung im Median weiterhin erreichbar. Die mediane Success Rate lag sowohl insgesamt als auch während der Störphase bei `100.00%`. Gleichzeitig zeigt der Mittelwert der Success Rate, dass nicht alle Läufe vollständig fehlerfrei waren. Insgesamt lag die mittlere Success Rate bei `97.76%`, während sie in der Fault-Phase bei `99.23%` lag.

Die Störung wirkte sich vor allem deutlich auf die Latenzen aus. Während die Baseline-Latenz mit einem Median von `1.41ms` sehr niedrig blieb, stieg die mediane Fault-Latenz auf `203.30ms`. Besonders auffällig sind die oberen Perzentile: Der Fault-p95 lag bei `1689.60ms`, der Fault-p99 bei `6651.35ms`, und die maximale Fault-Latenz lag im Median bei `61657.86ms`.

Damit unterscheidet sich das `50%`-Szenario deutlich von den `1%`- und `10%`-Tests. Der Paketverlust wird nicht nur als einzelne Latenzspitze sichtbar, sondern führt zu regelmäßigen und teilweise sehr langen Verzögerungen.

## Kubernetes- und KubeEdge-Ereignisse

In den Event-Dateien wurden in allen Läufen auffällige Ereignisse beobachtet. Insbesondere traten wiederholt `NodeNotReady`-Meldungen für die Edge-Nodes `e1` und `e2` auf. Auch Pods der Testanwendung sowie KubeEdge-nahe Komponenten wie `edgemesh-agent` und `edge-eclipse-mosquitto` wurden zeitweise als von `NodeNotReady` betroffen gemeldet.

Zusätzlich wurden folgende Ereignistypen beobachtet:

* `NodeNotReady` für `e1` und `e2`
* `NodeNotReady`-Warnungen für Pods der Testanwendung
* `TaintManagerEviction`
* `Marking for deletion` für Pods der Testanwendung
* `Cancelling deletion` von Pods nach Wiederherstellung
* `FailedScheduling`, weil Edge-Nodes zeitweise getaintet waren und Cloud-Nodes nicht zur Node-Affinity der Testanwendung passten
* `Successfully assigned` für neu geplante Pods der Testanwendung

Der Scheduler konnte Ersatz-Pods zeitweise nicht platzieren, weil die beiden Edge-Nodes aufgrund der Störung mit Taints belegt waren und die drei Cloud-Nodes wegen Node-Affinity bzw. Node-Selector nicht als Ziel infrage kamen. Nach der Wiederherstellung wurden Pods wieder erfolgreich auf Edge-Nodes eingeplant.

## Beobachtetes Self-Healing-Verhalten

Im Gegensatz zu den `1%`- und `10%`-Szenarien wurden bei `50%` Paketverlust sichtbare Self-Healing-Mechanismen ausgelöst. Die Control Plane erkannte die gestörte Verbindung zu den Edge-Nodes und markierte diese zeitweise als `NodeNotReady`. Dadurch wurden Taints gesetzt, und der TaintManager begann mit Eviction- bzw. Löschprozessen für betroffene Pods.

In mehreren Läufen wurden Pods der Testanwendung zur Löschung markiert und Ersatz-Pods erzeugt. Teilweise scheiterte das Scheduling zunächst, weil beide Edge-Nodes gleichzeitig als nicht geeignet galten und die Cloud-Nodes aufgrund der Platzierungsregeln nicht genutzt werden konnten. Nach Ende der Störung und Rückkehr der Edge-Nodes in einen nutzbaren Zustand wurden Pods erfolgreich neu zugewiesen oder laufende Löschungen abgebrochen.

Dieses Verhalten zeigt, dass KubeEdge bei `50%` Paketverlust nicht nur auf Transportebene betroffen ist, sondern dass die Störung stark genug ist, um Kubernetes-/KubeEdge-Zustandsänderungen auszulösen. Self-Healing wurde sichtbar, führte aber nicht zu einem vollständigen Ausfall der Anwendung über alle Läufe hinweg.

## Interpretation

Der Paketverlust von `50%` stellt in der untersuchten Umgebung eine deutliche Störung dar. Die Anwendung blieb zwar im Median verfügbar, aber die Latenzen stiegen massiv an, und es traten sichtbare Zustandsänderungen im Cluster auf.

Besonders relevant ist, dass KubeEdge die Edge-Nodes zeitweise als `NodeNotReady` einstufte. Dadurch wurden Kubernetes-Mechanismen wie Tainting, Eviction und Scheduling aktiviert. Die Testanwendung war wegen ihrer Platzierungsregeln jedoch auf Edge-Nodes beschränkt. Wenn beide Edge-Nodes gleichzeitig getaintet waren, konnten Ersatz-Pods vorübergehend nicht auf Cloud-Nodes ausweichen. Dies erklärt die beobachteten `FailedScheduling`-Events.

Die Wiederherstellung erfolgte nach Entfernen der Netzstörung automatisch: Der finale Clusterzustand war wieder stabil, alle Nodes waren `Ready`, und die Testanwendung lief wieder mit drei Pods. Damit zeigt das Szenario sowohl die Aktivierung nativer Self-Healing-Mechanismen als auch deren Grenzen bei gleichzeitiger Beeinträchtigung aller Edge-Zielknoten.

## Vergleichbare Einordnung

Im Vergleich zu `1%` und `10%` Paketverlust markiert `50%` Paketverlust den Übergang von reiner Latenzbeeinträchtigung zu sichtbarem Self-Healing-Verhalten. Während bei geringeren Paketverlustraten keine auffälligen Events beobachtet wurden, führte `50%` zu `NodeNotReady`, TaintManager-Aktivität, temporären Scheduling-Problemen und teilweise Pod-Neuzuweisungen.

Damit liegt `50%` Paketverlust in dieser Testumgebung im Bereich, in dem KubeEdge den gestörten Netzwerkzustand als clusterrelevantes Problem behandelt.

## Fazit

Ein Paketverlust von `50%` beeinträchtigt KubeEdge deutlich. Die Anwendung blieb zwar im Median erreichbar, aber die Latenz stieg massiv an, und erstmals wurden klare Self-Healing-Mechanismen sichtbar.

KubeEdge erkannte die Edge-Nodes zeitweise als `NodeNotReady`, löste TaintManager- und Scheduling-Prozesse aus und stellte nach Ende der Störung wieder einen stabilen Clusterzustand her. Gleichzeitig zeigten die `FailedScheduling`-Events, dass die Wiederherstellung durch die Platzierungsregeln der Testanwendung begrenzt war, da Ersatz-Pods nicht auf Cloud-Nodes ausweichen konnten.

Das Szenario zeigt damit ein relevantes Self-Healing-Verhalten: Die Plattform reagiert auf die Störung und stellt am Ende Stabilität wieder her, kann aber während der Störung nur eingeschränkt kompensieren, wenn alle zulässigen Edge-Knoten gleichzeitig betroffen sind.
