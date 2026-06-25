# KubeEdge Verbindungsabbruchtest: 1s

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem sehr kurzen Verbindungsabbruch von `1s` zwischen Cloud- und Edge-Netz verhält. Der Verbindungsabbruch wurde auf der Router-VM durch ein temporäres Deaktivieren des Interfaces `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Verbindungsabbrüchen als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein sehr kurzer Link-Cut bereits Auswirkungen auf die Erreichbarkeit der NGINX-Testanwendung, den Node-Status, Pod-Neuerstellungen oder KubeEdge-/Kubernetes-Self-Healing-Mechanismen hat.

## Versuchsaufbau

| Parameter                   |                         Wert |
| --------------------------- | ---------------------------: |
| System                      |                     KubeEdge |
| Szenario                    |                `link-cut-1s` |
| Anzahl Läufe                |                         `10` |
| Verbindungsabbruch          |                         `1s` |
| Fault-Typ                   |            `ip_link_down_up` |
| Router-Interface            |                     `ens161` |
| Vorlaufphase                |                       `180s` |
| Störphase                   |                         `1s` |
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
| Overall Median Latenz            |  `1.26ms` |
| Overall p95 Latenz               |  `1.83ms` |
| Overall p99 Latenz               |  `3.19ms` |
| Overall max. Latenz, Median      | `58.02ms` |
| Overall Timeouts gesamt          |       `0` |
| Baseline Success Rate, Median    | `100.00%` |
| Baseline Median Latenz           |  `1.27ms` |
| Baseline p95 Latenz              |  `1.83ms` |
| Fault Success Rate, Median       | `100.00%` |
| Fault Success Rate, Mittelwert   | `100.00%` |
| Fault Error Rate, Median         |   `0.00%` |
| Fault Error Rate, Mittelwert     |   `0.00%` |
| Fault Median Latenz              |  `2.01ms` |
| Fault p95 Latenz                 |  `3.19ms` |
| Fault p99 Latenz                 |  `3.19ms` |
| Fault max. Latenz, Median        |  `3.19ms` |
| Fault Timeouts gesamt            |       `0` |
| After Success Rate, Median       | `100.00%` |
| After Median Latenz              |  `1.19ms` |
| Recovery Time, Minimum           |   `0.10s` |
| Recovery Time, Median            |   `0.55s` |
| Recovery Time, Mittelwert        |   `0.49s` |
| Recovery Time, Maximum           |   `0.88s` |

## Beobachtungen zur Anwendungserreichbarkeit

Die NGINX-Testanwendung blieb während der gesamten Messreihe erreichbar. Sowohl insgesamt als auch in der Baseline-, Fault- und Nachlaufphase lag die Success Rate bei `100.00%`. Es wurden keine fehlgeschlagenen HTTP-Requests und keine Timeouts beobachtet.

Während der Störphase stieg die mediane Latenz leicht von `1.27ms` in der Baseline auf `2.01ms` während des Faults. Dieser Anstieg ist messbar, aber sehr klein. Auch die oberen Perzentile blieben niedrig: Der Fault-p95 und Fault-p99 lagen jeweils bei `3.19ms`.

Damit führte ein Verbindungsabbruch von `1s` in dieser Testumgebung nicht zu einer sichtbaren Beeinträchtigung der Anwendungserreichbarkeit.

## Kubernetes- und KubeEdge-Ereignisse

In den Event-Dateien wurden in den ersten vier Läufen auffällige Ereignisse beobachtet. Dabei wurde jeweils `e2` als `NodeNotReady` gemeldet. Zusätzlich wurden KubeEdge-nahe Komponenten auf `e2`, insbesondere `edge-eclipse-mosquitto` und `edgemesh-agent`, mit `NodeNotReady`-Warnungen erfasst.

In den Läufen `run-05` bis `run-10` wurden keine auffälligen Events gefunden.

Die beobachteten Events betrafen nicht die NGINX-Testanwendung. Die Testapp-Pods liefen während der gesamten Messreihe auf `e1` und blieben unverändert im Zustand `Running`.

## Pod-Verhalten

Die drei Pods der NGINX-Testanwendung blieben in allen zehn Läufen identisch. Es wurden keine Pod-Neuerstellungen, keine Pod-Restarts, keine Evictions und keine Scheduling-Vorgänge für die Testanwendung beobachtet.

Die Pods liefen durchgehend auf `e1`:

* `nginx-testapp-5c8f4cb9d7-dj67m`
* `nginx-testapp-5c8f4cb9d7-dnm2w`
* `nginx-testapp-5c8f4cb9d7-ww6hl`

Damit zeigte sich auf Anwendungsebene kein Self-Healing-Verhalten, weil kein fehlerhafter Anwendungszustand entstand, der eine Pod-Neuerstellung oder ein Rescheduling erforderlich gemacht hätte.

## Beobachtetes Self-Healing-Verhalten

Bei einem Verbindungsabbruch von `1s` wurden keine Self-Healing-Mechanismen auf Ebene der Testanwendung ausgelöst. Die Anwendung blieb erreichbar, die Pods blieben stabil, und es wurden keine Ersatz-Pods erzeugt.

Die `NodeNotReady`-Events in den ersten vier Läufen zeigen jedoch, dass die Control Plane bzw. KubeEdge den kurzen Verbindungsabbruch teilweise als Zustandsänderung auf Edge-Ebene wahrnahm. Diese Reaktion führte aber nicht zu einer Serviceunterbrechung und nicht zu Pod-Replacements der Testanwendung.

Das Szenario zeigt damit eher eine robuste Toleranz gegenüber sehr kurzen Verbindungsabbrüchen als eine aktive Wiederherstellung nach einem Anwendungsausfall.

## Interpretation

Der `1s`-Verbindungsabbruch war technisch eindeutig vorhanden, hatte aber keine messbare negative Auswirkung auf die Anwendungserreichbarkeit. Die Requests blieben in allen Phasen erfolgreich, und die Latenzen blieben sehr niedrig.

Die kurzzeitigen `NodeNotReady`-Events für `e2` sind dennoch relevant. Sie zeigen, dass bereits sehr kurze Netzwerkunterbrechungen im KubeEdge-Cluster sichtbar werden können. Da die Testanwendung jedoch vollständig auf `e1` lief und der Link-Cut nur sehr kurz dauerte, entstanden keine Scheduling-Probleme, keine Evictions und keine Pod-Neuerstellungen.

Die Recovery Time ist in diesem Szenario nicht als klassische MTTR nach einem Serviceausfall zu interpretieren, da kein Anwendungsausfall beobachtet wurde. Sie beschreibt vielmehr den Zeitpunkt des ersten erfolgreichen Requests nach dokumentierter Wiederherstellung des Router-Interfaces.

## Fazit

Ein Verbindungsabbruch von `1s` wurde in allen zehn Läufen erfolgreich erzeugt und dokumentiert, führte aber nicht zu einer Beeinträchtigung der NGINX-Testanwendung. Die Request Success Rate lag durchgehend bei `100.00%`, es traten keine Timeouts auf, und die Testapp-Pods blieben unverändert im Zustand `Running`.

Auffällig waren `NodeNotReady`-Events für `e2` in den ersten vier Läufen. Diese betrafen jedoch nicht die Testanwendung und führten nicht zu sichtbaren Self-Healing-Maßnahmen auf Anwendungsebene.

Das Szenario zeigt damit, dass KubeEdge einen sehr kurzen Verbindungsabbruch auf Anwendungsebene vollständig tolerierte, während auf Cluster-/Edge-Ebene bereits kurzzeitige Zustandsänderungen sichtbar werden konnten.
