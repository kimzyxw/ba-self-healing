# KubeEdge Verbindungsabbruchtest: 30min

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem langen Verbindungsabbruch von `30min` zwischen Cloud- und Edge-Netz verhält. Der Verbindungsabbruch wurde auf der Router-VM durch ein temporäres Deaktivieren des Interfaces `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Verbindungsabbrüchen als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein längerer Link-Cut Auswirkungen auf die Erreichbarkeit der NGINX-Testanwendung, den Node-Status, Pod-Neuerstellungen, Scheduling-Verhalten, Evictions und KubeEdge-/Kubernetes-Self-Healing-Mechanismen hat.

## Versuchsaufbau

| Parameter                   |                         Wert |
| --------------------------- | ---------------------------: |
| System                      |                     KubeEdge |
| Szenario                    |             `link-cut-30min` |
| Anzahl Läufe                |                         `10` |
| Verbindungsabbruch          |                      `1800s` |
| Fault-Typ                   |            `ip_link_down_up` |
| Router-Interface            |                     `ens161` |
| Vorlaufphase                |                       `180s` |
| Störphase                   |                      `1800s` |
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
| Overall Success Rate, Median     |  `99.50%` |
| Overall Success Rate, Mittelwert |  `99.17%` |
| Overall Error Rate, Median       |   `0.51%` |
| Overall Error Rate, Mittelwert   |   `0.83%` |
| Overall Median Latenz            |  `1.83ms` |
| Overall p95 Latenz               |  `3.92ms` |
| Overall p99 Latenz               |  `5.53ms` |
| Overall max. Latenz, Median      | `68.69ms` |
| Overall Timeouts gesamt          |       `0` |
| Baseline Success Rate, Median    | `100.00%` |
| Baseline Median Latenz           |  `1.21ms` |
| Baseline p95 Latenz              |  `1.86ms` |
| Fault Success Rate, Median       | `100.00%` |
| Fault Success Rate, Mittelwert   | `100.00%` |
| Fault Error Rate, Median         |   `0.00%` |
| Fault Error Rate, Mittelwert     |   `0.00%` |
| Fault Median Latenz              |  `1.90ms` |
| Fault p95 Latenz                 |  `3.99ms` |
| Fault p99 Latenz                 |  `5.53ms` |
| Fault max. Latenz, Median        | `68.69ms` |
| Fault Timeouts gesamt            |       `0` |
| After Success Rate, Median       |  `94.25%` |
| After Success Rate, Mittelwert   |  `90.65%` |
| After Error Rate, Median         |   `5.75%` |
| After Error Rate, Mittelwert     |   `9.35%` |
| After Median Latenz              |  `1.42ms` |
| After p95 Latenz                 |  `3.29ms` |
| After p99 Latenz                 |  `6.88ms` |
| After Timeouts gesamt            |       `0` |
| Recovery Time, Minimum           |   `0.21s` |
| Recovery Time, Median            |   `0.81s` |
| Recovery Time, Mittelwert        |   `2.60s` |
| Recovery Time, Maximum           |  `12.70s` |

## Beobachtungen zur Anwendungserreichbarkeit

Die NGINX-Testanwendung blieb während der Störphase erreichbar. In der Fault-Phase lag die Success Rate im Median und im Mittel bei `100.00%`, und es wurden keine Timeouts beobachtet. Die Latenzen blieben während der Störphase ebenfalls niedrig: Der Fault-Median lag bei `1.90ms`, der Fault-p95 bei `3.99ms` und der Fault-p99 bei `5.53ms`.

Die sichtbaren HTTP-Fehler traten vor allem in der Nachlaufphase auf. Nach Wiederherstellung des Router-Interfaces sank die Success Rate im Median auf `94.25%` und im Mittel auf `90.65%`. Die Fehlerrate lag in der Nachlaufphase entsprechend bei `5.75%` im Median und `9.35%` im Mittel. Als Fehlerarten wurden insbesondere `ServerDisconnectedError` und `ClientOSError` beobachtet. Timeouts traten nicht auf.

Damit zeigt das Szenario keine Unterbrechung der Anwendungserreichbarkeit während des eigentlichen Link-Cuts, aber eine deutliche Beeinträchtigung während der nachgelagerten Wiederherstellungs- und Reorganisationsphase.

## Kubernetes- und KubeEdge-Ereignisse

In allen zehn Läufen wurden deutliche Kubernetes-/KubeEdge-Ereignisse beobachtet. Die Edge-Nodes `e1` und `e2` wurden als `NodeNotReady` gemeldet. Zusätzlich erhielten KubeEdge-nahe Komponenten wie `edge-eclipse-mosquitto` und `edgemesh-agent` entsprechende `NodeNotReady`-Warnungen.

Auch die Pods der NGINX-Testanwendung waren betroffen. In den Events wurden wiederholt `NodeNotReady`-Warnungen für die Testapp-Pods dokumentiert. Darüber hinaus trat `TaintManagerEviction` auf: Pods der Testanwendung wurden zur Löschung markiert, Ersatz-Pods wurden erzeugt, und der Scheduler versuchte, diese neu zu platzieren.

Während beide Edge-Nodes mit Taints belegt waren, scheiterte das Scheduling zunächst. Die Events zeigen wiederholt `FailedScheduling` mit der Begründung, dass zwei Nodes wegen nicht tolerierter Taints nicht verfügbar waren und drei Cloud-Nodes wegen der Node-Affinity bzw. Node-Selector-Regeln der Testanwendung nicht infrage kamen. Nach Wiederherstellung der Edge-Knoten wurden neue Pods erfolgreich auf `e1` eingeplant.

## Pod-Verhalten

Die Pods der NGINX-Testanwendung wurden in allen zehn Läufen ersetzt. Vor und nach jedem Lauf waren unterschiedliche Pod-Namen und Pod-IPs sichtbar. Die neuen Pods wurden jeweils wieder auf `e1` geplant und liefen am Ende im Zustand `Running`.

Beispielhaft waren vor `run-01` folgende Pods aktiv:

* `nginx-testapp-5c8f4cb9d7-5qs8s`
* `nginx-testapp-5c8f4cb9d7-tc8m9`
* `nginx-testapp-5c8f4cb9d7-zlpp8`

Nach `run-01` liefen neue Pods:

* `nginx-testapp-5c8f4cb9d7-8vnsd`
* `nginx-testapp-5c8f4cb9d7-jnr4d`
* `nginx-testapp-5c8f4cb9d7-wpn2j`

Dieses Muster setzte sich über alle zehn Läufe fort. Damit wurde bei `30min` ein klar sichtbares Self-Healing-Verhalten auf Pod-Ebene beobachtet.

## Beobachtetes Self-Healing-Verhalten

Bei einem Verbindungsabbruch von `30min` wurden deutliche Self-Healing-Mechanismen sichtbar. Die Control Plane erkannte die Edge-Nodes zeitweise als `NodeNotReady`. Dadurch wurden Taints gesetzt, der TaintManager wurde aktiv, Pods der Testanwendung wurden zur Löschung markiert, Ersatz-Pods wurden erzeugt, und der Scheduler versuchte, diese neu zu platzieren.

Das Scheduling war während der Störung zeitweise nicht möglich, weil beide Edge-Nodes durch Taints blockiert waren und die drei Cloud-Nodes wegen der Platzierungsregeln der Testanwendung nicht genutzt werden konnten. Nach Wiederherstellung der Edge-Knoten wurden die Ersatz-Pods erfolgreich auf `e1` eingeplant.

Das Self-Healing war damit klar sichtbar, führte aber nicht zu einer vollständigen Serviceunterbrechung während der Fault-Phase. Die messbaren HTTP-Fehler traten vor allem in der Nachlaufphase auf, während die Pod-Ersetzungen und die Reorganisation des stabilen Anwendungszustands sichtbar wurden.

## Interpretation

Der `30min`-Verbindungsabbruch bestätigt das Muster aus dem `10min`-Szenario. Die Anwendung blieb während der eigentlichen Störphase auf HTTP-Ebene erreichbar, obwohl die Control Plane die Edge-Nodes als problematisch bewertete. Die Auswirkungen zeigten sich vor allem nach Wiederherstellung des Router-Interfaces.

Die Nachlaufphase war stärker beeinträchtigt als beim `10min`-Szenario. Während die After-Success-Rate bei `10min` im Median bei `96.69%` lag, sank sie bei `30min` auf `94.25%`. Auch der Mittelwert der After-Success-Rate lag mit `90.65%` niedriger. Damit führte der längere Verbindungsabbruch nicht zu einem schlechteren Verhalten während der Fault-Phase, aber zu einer stärkeren nachgelagerten Reorganisation mit mehr HTTP-Fehlern in der Nachlaufphase.

Die Recovery Time ist auch hier nur eingeschränkt als klassische MTTR zu interpretieren, da während der Fault-Phase kein vollständiger Anwendungsausfall gemessen wurde. Sie beschreibt den Zeitpunkt des ersten erfolgreichen Requests nach dokumentierter Wiederherstellung des Router-Interfaces. Für das Self-Healing auf Pod-Ebene sind zusätzlich die Kubernetes-Events und die Pod-Wechsel vor/nach den Läufen entscheidend.

## Vergleich zu 10min

Sowohl bei `10min` als auch bei `30min` wurden die Testapp-Pods in allen zehn Läufen ersetzt. In beiden Szenarien traten `NodeNotReady`, `TaintManagerEviction`, `FailedScheduling`, `Scheduled` und `Cancelling deletion` auf. Damit zeigen beide Szenarien klares Self-Healing-Verhalten auf Cluster- und Pod-Ebene.

Der Unterschied liegt vor allem in der Nachlaufphase. Bei `10min` lag die After-Success-Rate im Median bei `96.69%`, bei `30min` nur noch bei `94.25%`. Der Mittelwert sank von `95.55%` auf `90.65%`. Damit war die Nachlaufphase bei `30min` stärker beeinträchtigt.

Die Fault-Phase blieb in beiden Szenarien auf HTTP-Ebene stabil: Sowohl bei `10min` als auch bei `30min` lag die Fault-Success-Rate bei `100.00%`.

## Fazit

Ein Verbindungsabbruch von `30min` wurde in allen zehn Läufen erfolgreich erzeugt und dokumentiert. Die Fault-Phase selbst zeigte auf HTTP-Ebene weiterhin eine Success Rate von `100.00%` ohne Timeouts. In der Nachlaufphase traten jedoch messbare Fehler auf, wodurch die After-Success-Rate auf `94.25%` im Median und `90.65%` im Mittel sank.

Auf Cluster-Ebene waren die Auswirkungen deutlich: Beide Edge-Nodes wurden als `NodeNotReady` gemeldet, Pods der Testanwendung wurden zur Löschung markiert, Ersatz-Pods erzeugt und zunächst teilweise wegen Taints und Node-Affinity-Regeln nicht planbar. Nach Wiederherstellung wurden neue Pods erfolgreich auf `e1` eingeplant.

Das Szenario zeigt damit klares Self-Healing-Verhalten: KubeEdge bzw. Kubernetes reagierte auf den langen Verbindungsabbruch mit Node-Statusänderungen, TaintManager-Aktivität, Pod-Neuerstellung und Scheduling. Gleichzeitig zeigte sich, dass die Anwendung während des Link-Cuts zunächst weiter erreichbar blieb und die sichtbaren HTTP-Fehler vor allem in der nachgelagerten Wiederherstellungsphase auftraten.
