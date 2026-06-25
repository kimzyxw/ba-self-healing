# KubeEdge Verbindungsabbruchtest: 10min

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem Verbindungsabbruch von `10min` zwischen Cloud- und Edge-Netz verhält. Der Verbindungsabbruch wurde auf der Router-VM durch ein temporäres Deaktivieren des Interfaces `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Verbindungsabbrüchen als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein längerer Link-Cut Auswirkungen auf die Erreichbarkeit der NGINX-Testanwendung, den Node-Status, Pod-Neuerstellungen, Scheduling-Verhalten, Evictions und KubeEdge-/Kubernetes-Self-Healing-Mechanismen hat.

## Versuchsaufbau

| Parameter                   |                         Wert |
| --------------------------- | ---------------------------: |
| System                      |                     KubeEdge |
| Szenario                    |             `link-cut-10min` |
| Anzahl Läufe                |                         `10` |
| Verbindungsabbruch          |                       `600s` |
| Fault-Typ                   |            `ip_link_down_up` |
| Router-Interface            |                     `ens161` |
| Vorlaufphase                |                       `180s` |
| Störphase                   |                       `600s` |
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

Der finale Clusterzustand war stabil: Alle Nodes waren `Ready`, die Testanwendung lief wieder mit drei Pods im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                           |      Wert |
| -------------------------------- | --------: |
| Overall Success Rate, Median     |  `99.34%` |
| Overall Success Rate, Mittelwert |  `99.12%` |
| Overall Error Rate, Median       |   `0.67%` |
| Overall Error Rate, Mittelwert   |   `0.88%` |
| Overall Median Latenz            |  `1.63ms` |
| Overall p95 Latenz               |  `3.66ms` |
| Overall p99 Latenz               |  `5.64ms` |
| Overall max. Latenz, Median      | `64.55ms` |
| Overall Timeouts gesamt          |       `0` |
| Baseline Success Rate, Median    | `100.00%` |
| Baseline Median Latenz           |  `1.21ms` |
| Baseline p95 Latenz              |  `1.85ms` |
| Fault Success Rate, Median       | `100.00%` |
| Fault Success Rate, Mittelwert   | `100.00%` |
| Fault Error Rate, Median         |   `0.00%` |
| Fault Error Rate, Mittelwert     |   `0.00%` |
| Fault Median Latenz              |  `1.86ms` |
| Fault p95 Latenz                 |  `3.91ms` |
| Fault p99 Latenz                 |  `5.70ms` |
| Fault max. Latenz, Median        | `56.67ms` |
| Fault Timeouts gesamt            |       `0` |
| After Success Rate, Median       |  `96.69%` |
| After Success Rate, Mittelwert   |  `95.55%` |
| After Error Rate, Median         |   `3.30%` |
| After Error Rate, Mittelwert     |   `4.45%` |
| After Median Latenz              |  `1.32ms` |
| After p95 Latenz                 |  `2.89ms` |
| After p99 Latenz                 |  `4.75ms` |
| After Timeouts gesamt            |       `0` |
| Recovery Time, Minimum           |   `0.39s` |
| Recovery Time, Median            |   `0.77s` |
| Recovery Time, Mittelwert        |   `1.51s` |
| Recovery Time, Maximum           |   `8.53s` |

## Beobachtungen zur Anwendungserreichbarkeit

Die NGINX-Testanwendung blieb während der Störphase erreichbar. In der Fault-Phase lag die Success Rate im Median und im Mittel bei `100.00%`, und es wurden keine Timeouts beobachtet. Auch die Latenzen blieben während der Störphase niedrig: Der Fault-Median lag bei `1.86ms`, der Fault-p95 bei `3.91ms` und der Fault-p99 bei `5.70ms`.

Auffällig ist jedoch die Nachlaufphase. Nach Wiederherstellung des Router-Interfaces sank die Success Rate im Median auf `96.69%` und im Mittel auf `95.55%`. Die Fehlerrate lag in der Nachlaufphase entsprechend bei `3.30%` im Median und `4.45%` im Mittel. Als Fehlerarten wurden insbesondere `ServerDisconnectedError` und `ClientOSError` beobachtet. Timeouts traten weiterhin nicht auf.

Damit zeigt das Szenario keine ausgeprägte Störung während des eigentlichen Link-Cuts auf HTTP-Ebene, aber eine messbare Beeinträchtigung während der anschließenden Wiederherstellungs- und Reorganisationsphase.

## Kubernetes- und KubeEdge-Ereignisse

In allen zehn Läufen wurden deutliche Kubernetes-/KubeEdge-Ereignisse beobachtet. Dabei wurden die Edge-Nodes `e1` und `e2` als `NodeNotReady` gemeldet. Zusätzlich erhielten KubeEdge-nahe Komponenten wie `edge-eclipse-mosquitto` und `edgemesh-agent` entsprechende `NodeNotReady`-Warnungen.

Auch die Pods der NGINX-Testanwendung waren betroffen. In den Events wurden wiederholt `NodeNotReady`-Warnungen für die Testapp-Pods dokumentiert. Darüber hinaus trat `TaintManagerEviction` auf. Anders als beim `1min`-Szenario blieb es nicht nur bei abgebrochenen Löschprozessen: In allen Läufen wurden Pods der Testanwendung zur Löschung markiert, neue Pods erzeugt und anschließend wieder auf `e1` eingeplant.

Zusätzlich traten `FailedScheduling`-Events auf. Diese wurden dadurch verursacht, dass die beiden Edge-Nodes zeitweise mit Taints belegt waren und die drei Cloud-Nodes aufgrund der Node-Affinity bzw. Node-Selector-Regeln der Testanwendung nicht als Zielknoten infrage kamen. Sobald die Edge-Nodes wieder nutzbar waren, wurden neue Pods erfolgreich auf `e1` eingeplant.

## Pod-Verhalten

Im Gegensatz zu den kürzeren Verbindungsabbrüchen wurden die Pods der NGINX-Testanwendung bei `10min` in allen zehn Läufen ersetzt. Vor und nach den Läufen waren jeweils unterschiedliche Pod-Namen und Pod-IPs sichtbar. Die neuen Pods wurden in allen Läufen wieder auf `e1` geplant und liefen am Ende im Zustand `Running`.

Beispielhaft waren vor `run-01` die ursprünglichen Pods aktiv:

* `nginx-testapp-5c8f4cb9d7-dj67m`
* `nginx-testapp-5c8f4cb9d7-dnm2w`
* `nginx-testapp-5c8f4cb9d7-ww6hl`

Nach `run-01` liefen dagegen neue Pods:

* `nginx-testapp-5c8f4cb9d7-gggcl`
* `nginx-testapp-5c8f4cb9d7-rm27h`
* `nginx-testapp-5c8f4cb9d7-slx67`

Dieses Muster setzte sich über alle zehn Läufe fort. Damit wurde bei `10min` ein klar sichtbares Self-Healing-Verhalten auf Pod-Ebene beobachtet.

## Beobachtetes Self-Healing-Verhalten

Bei einem Verbindungsabbruch von `10min` wurden deutliche Self-Healing-Mechanismen sichtbar. Die Control Plane erkannte die Edge-Nodes zeitweise als `NodeNotReady`. Dadurch wurden Taints gesetzt und der TaintManager wurde aktiv. Pods der Testanwendung wurden zur Löschung markiert, Ersatz-Pods wurden erzeugt, und der Scheduler versuchte, diese neu zu platzieren.

Während beide Edge-Nodes als ungeeignet galten, scheiterte das Scheduling zunächst. Die Fehlermeldungen zeigen, dass zwei Nodes wegen nicht tolerierter Taints nicht verfügbar waren und drei Nodes wegen der Node-Affinity bzw. Node-Selector-Regeln nicht genutzt werden konnten. Nach Wiederherstellung der Edge-Knoten wurden die Ersatz-Pods erfolgreich auf `e1` eingeplant.

Das Self-Healing war damit klar sichtbar, führte aber nicht zu einer vollständigen Serviceunterbrechung während der Störphase. Die messbaren HTTP-Fehler traten vor allem in der Nachlaufphase auf, also während der Reorganisation und Wiederherstellung des stabilen Pod-Zustands.

## Interpretation

Der `10min`-Verbindungsabbruch stellt einen deutlichen Übergang gegenüber den kürzeren Szenarien dar. Während bei `1s` und `1min` keine tatsächlichen Pod-Ersetzungen beobachtet wurden, führte `10min` in allen Läufen zu Pod-Neuerstellungen und Scheduling-Aktivität.

Interessant ist, dass die Anwendung während der Fault-Phase weiterhin erfolgreich erreichbar blieb. Die Auswirkungen zeigten sich stattdessen vor allem nach Ende der Störung. Dies deutet darauf hin, dass die Anwendung auf dem Edge-Knoten während der Unterbrechung zunächst weiterlief, während die Control Plane im Hintergrund den Node-Zustand als problematisch bewertete und nach Ablauf entsprechender Mechanismen Pod-Löschungen bzw. Ersatz-Pods auslöste. Die daraus resultierende Reorganisation führte dann in der Nachlaufphase zu einzelnen Verbindungsabbrüchen.

Die Recovery Time ist auch hier nur eingeschränkt als klassische MTTR zu interpretieren, da während der Fault-Phase kein vollständiger Anwendungsausfall gemessen wurde. Sie beschreibt den Zeitpunkt des ersten erfolgreichen Requests nach dokumentierter Wiederherstellung des Router-Interfaces. Für das Self-Healing auf Pod-Ebene sind zusätzlich die Kubernetes-Events und die Pod-Wechsel vor/nach den Läufen entscheidend.

## Vergleich zu 1s und 1min

Im Vergleich zu `1s` und `1min` zeigt `10min` deutlich stärkere Auswirkungen auf Cluster- und Pod-Ebene.

Beim `1s`-Szenario waren nur begrenzte `NodeNotReady`-Events sichtbar, und die Testapp-Pods blieben unverändert. Beim `1min`-Szenario traten `NodeNotReady`-Events in allen Läufen auf, und der TaintManager wurde aktiv, die Löschung der Pods wurde jedoch jeweils abgebrochen. Beim `10min`-Szenario wurden die Pods hingegen in allen Läufen tatsächlich ersetzt.

Die Anwendungserreichbarkeit blieb während der Fault-Phase dennoch hoch. Der wesentliche Unterschied liegt daher nicht in einer sofortigen HTTP-Unterbrechung während des Link-Cuts, sondern in der stärkeren nachgelagerten Reaktion der Control Plane und des Schedulers.

## Fazit

Ein Verbindungsabbruch von `10min` wurde in allen zehn Läufen erfolgreich erzeugt und dokumentiert. Die Fault-Phase selbst zeigte auf HTTP-Ebene weiterhin eine Success Rate von `100.00%` ohne Timeouts. In der Nachlaufphase traten jedoch messbare Fehler auf, wodurch die After-Success-Rate auf `96.69%` im Median sank.

Auf Cluster-Ebene waren die Auswirkungen deutlich: Beide Edge-Nodes wurden als `NodeNotReady` gemeldet, Pods der Testanwendung wurden zur Löschung markiert, Ersatz-Pods erzeugt und zunächst teilweise wegen Taints und Node-Affinity-Regeln nicht planbar. Nach Wiederherstellung wurden neue Pods erfolgreich auf `e1` eingeplant.

Das Szenario zeigt damit klares Self-Healing-Verhalten: KubeEdge bzw. Kubernetes reagierte auf den längeren Verbindungsabbruch mit Node-Statusänderungen, TaintManager-Aktivität, Pod-Neuerstellung und Scheduling. Gleichzeitig zeigte sich, dass die Anwendung während des Link-Cuts zunächst weiter erreichbar blieb und die sichtbaren HTTP-Fehler vor allem in der nachgelagerten Wiederherstellungsphase auftraten.
