# KubeEdge Paketverlusttest: 100 %

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem vollständigen Paketverlust von `100%` zwischen Cloud- und Edge-Netz verhält. Der Paketverlust wurde auf der Router-VM mit `tc/netem` auf dem Interface `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Paketverlusttests als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Das Szenario entspricht einer vollständigen Unterbrechung der Kommunikation über den gestörten Pfad. Ziel war es zu prüfen, wie stark die Anwendungserreichbarkeit einbricht, welche Self-Healing-Mechanismen ausgelöst werden und ob KubeEdge nach Entfernen der Störung automatisch wieder in einen stabilen Zustand zurückkehrt.

## Versuchsaufbau

| Parameter                   |                                Wert |
| --------------------------- | ----------------------------------: |
| System                      |                            KubeEdge |
| Szenario                    | `packet-loss-100pct-safety-cleanup` |
| Anzahl Läufe                |                                `10` |
| Paketverlust                |                              `100%` |
| Router-Interface            |                            `ens161` |
| Vorlaufphase                |                              `180s` |
| Störphase                   |                              `600s` |
| Nachlaufphase               |                              `180s` |
| HTTP-Timeout                |                              `300s` |
| Request-Intervall           |                                `1s` |
| Maximale parallele Requests |                                `10` |
| Ziel-URL                    |        `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Paketverlust wurde zentral auf der Router-VM eingebracht. Das Szenario wurde mit Router-gesteuertem Cleanup und zusätzlichem Safety-Cleanup durchgeführt.

## Validierung der Testdurchführung

| Validierung                       | Ergebnis |
| --------------------------------- | -------: |
| Ausgewertete Läufe                |  `10/10` |
| Routerpfad gültig                 |  `10/10` |
| Paketverlust aktiv                |  `10/10` |
| `tc/netem` nach dem Lauf entfernt |  `10/10` |
| After-Preflight erfolgreich       |  `10/10` |

Die Messreihe ist vollständig und methodisch sauber auswertbar. In allen zehn Läufen wurde der Paketverlust erfolgreich mit `tc/netem loss 100%` aktiviert und nach der Störphase wieder entfernt. Der Routerpfad war in allen Läufen gültig, das Cleanup wurde in allen Läufen dokumentiert, und der After-Preflight war in allen Läufen erfolgreich.

Der finale Clusterzustand war stabil: Alle Nodes waren `Ready`, die Testanwendung lief mit drei Pods im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                           |          Wert |
| -------------------------------- | ------------: |
| Overall Success Rate, Median     |      `67.48%` |
| Overall Success Rate, Mittelwert |      `67.42%` |
| Overall Error Rate, Median       |      `32.52%` |
| Overall Error Rate, Mittelwert   |      `32.58%` |
| Overall Median Latenz            |      `1.58ms` |
| Overall p95 Latenz               | `101928.50ms` |
| Overall p99 Latenz               | `135776.05ms` |
| Overall max. Latenz, Median      | `249281.65ms` |
| Overall Timeouts gesamt          |           `5` |
| Baseline Success Rate, Median    |     `100.00%` |
| Baseline Median Latenz           |      `1.40ms` |
| Baseline p95 Latenz              |      `2.56ms` |
| Fault Success Rate, Median       |       `3.83%` |
| Fault Success Rate, Mittelwert   |       `3.23%` |
| Fault Error Rate, Median         |      `96.17%` |
| Fault Error Rate, Mittelwert     |      `96.77%` |
| Fault Median Latenz              |   `4139.58ms` |
| Fault p95 Latenz                 | `135227.40ms` |
| Fault p99 Latenz                 | `136368.85ms` |
| Fault max. Latenz, Median        | `249281.65ms` |
| Fault Timeouts gesamt            |           `5` |
| After Success Rate, Median       |      `98.50%` |
| After Success Rate, Mittelwert   |      `97.98%` |
| After Error Rate, Median         |       `1.50%` |
| After Error Rate, Mittelwert     |       `2.02%` |
| After Median Latenz              |      `1.38ms` |
| Recovery Time, Median            |       `4.85s` |
| Recovery Time, Mittelwert        |       `6.38s` |
| Recovery Time, Maximum           |      `16.20s` |

## Beobachtungen zur Anwendungserreichbarkeit

Bei `100%` Paketverlust brach die Anwendungserreichbarkeit während der Störphase nahezu vollständig ein. Während die Baseline-Phase in allen Läufen stabil war und eine Success Rate von `100.00%` zeigte, lag die mediane Fault Success Rate nur noch bei `3.83%`. Die Fault Error Rate lag entsprechend bei `96.17%`.

Die wenigen erfolgreichen Requests während der Störphase sind nicht als stabile Erreichbarkeit zu interpretieren. Sie entstanden vermutlich durch Requests an den Rändern der Störphase oder durch noch laufende Verbindungs-/Retry-Effekte. Die überwiegende Mehrheit der Requests schlug während der aktiven Störung fehl.

Die Latenzwerte zeigen ebenfalls eine massive Beeinträchtigung. Der Fault-Median lag bei `4139.58ms`, der Fault-p95 bei `135227.40ms` und der Fault-p99 bei `136368.85ms`. Zusätzlich wurden insgesamt `5` Timeouts gemessen.

Nach Ende der Störung erholte sich die Anwendung deutlich. In der Nachlaufphase lag die mediane Success Rate wieder bei `98.50%`, die mediane Latenz bei `1.38ms`. Damit zeigt sich eine weitgehende automatische Wiederherstellung der Anwendungserreichbarkeit nach Entfernen des Paketverlusts.

## Fehlerarten

Die Fehler während der Störphase bestanden überwiegend aus `ClientConnectorError`. Zusätzlich traten vereinzelt `ServerDisconnectedError`, `ClientOSError` und `TimeoutError` auf. Die Dominanz von `ClientConnectorError` passt zum Szenario, da bei `100%` Paketverlust neue Verbindungen während der Störphase in der Regel nicht aufgebaut werden konnten.

In den einzelnen Läufen lagen die Fault Success Rates überwiegend zwischen etwa `0.47%` und `5.18%`. Die Fault Error Rates lagen entsprechend meist oberhalb von `94%`. Damit ist das Szenario klar als nahezu vollständige Serviceunterbrechung während der Störphase einzuordnen.

## Kubernetes- und KubeEdge-Ereignisse

In den Events wurden in allen Läufen deutliche Self-Healing- und Recovery-Aktivitäten beobachtet. Beide Edge-Nodes wurden wiederholt als `NodeNotReady` gemeldet. Zusätzlich waren sowohl Pods der Testanwendung als auch KubeEdge-nahe Komponenten wie `edgemesh-agent` und `edge-eclipse-mosquitto` von `NodeNotReady`-Warnungen betroffen.

Folgende Ereignistypen wurden beobachtet:

* `NodeNotReady` für `e1` und `e2`
* `NodeNotReady`-Warnungen für Testapp-Pods und KubeEdge-Komponenten
* `TaintManagerEviction`
* `Marking for deletion` für Pods der Testanwendung
* `FailedScheduling`
* `Successfully assigned` für neu geplante Pods
* `Cancelling deletion` nach Wiederherstellung

Die Events zeigen, dass Kubernetes/KubeEdge die vollständige Kommunikationsunterbrechung als schwerwiegende Störung erkannte. Die betroffenen Edge-Nodes wurden getaintet, Pods wurden zur Löschung markiert und Ersatz-Pods erzeugt. Solange beide Edge-Nodes als nicht geeignet galten, konnten Ersatz-Pods aufgrund der Node-Affinity bzw. Node-Selector-Regeln nicht auf Cloud-Nodes ausweichen. Dadurch entstanden wiederholt `FailedScheduling`-Events.

## Pod-Verhalten

In allen zehn Läufen wurden die Pods der Testanwendung während bzw. nach der Störung ersetzt. Vor jedem Lauf waren drei Pods der Testanwendung im Zustand `Running`. Nach den Läufen waren erneut drei Pods im Zustand `Running`, jedoch mit neuen Pod-Namen und neuen Pod-IPs.

Die Pods wurden überwiegend wieder auf `e1` eingeplant. Es wurden keine Pod-Restarts innerhalb derselben Pod-Instanz beobachtet; stattdessen erfolgte die Wiederherstellung über Pod-Ersetzungen und Neuzuweisungen. Dies zeigt, dass die Reconciliation über Kubernetes-Mechanismen auf Deployment-Ebene erfolgte.

## Beobachtetes Self-Healing-Verhalten

Bei `100%` Paketverlust wurden native Self-Healing-Mechanismen eindeutig sichtbar. KubeEdge bzw. die Kubernetes-Control-Plane erkannten den Verlust der Kommunikation zu den Edge-Nodes, markierten diese als `NodeNotReady` und lösten daraufhin Tainting-, Eviction- und Scheduling-Prozesse aus.

Die eigentliche Anwendung war während der Störphase jedoch nur sehr eingeschränkt verfügbar. Das Self-Healing konnte den vollständigen Paketverlust nicht kompensieren, solange die Netzwerkkommunikation aktiv unterbrochen war. Dies ist erwartbar, da beide Edge-Nodes aus Sicht der Control Plane zeitweise nicht zuverlässig erreichbar waren und die Testanwendung nicht auf Cloud-Nodes ausweichen durfte.

Nach Entfernen der Störung stellte sich der Cluster jedoch automatisch wieder her. Die Nodes kehrten in den Zustand `Ready` zurück, neue Pods wurden erfolgreich auf Edge-Nodes eingeplant, und die Anwendung war wieder über den NodePort erreichbar. Die Recovery Time lag im Median bei `4.85s`, maximal bei `16.20s`.

## Interpretation

Der Test mit `100%` Paketverlust zeigt die Belastungsgrenze der untersuchten KubeEdge-Umgebung. Während geringere Paketverlustraten noch teilweise durch TCP-Retransmissions und Kubernetes-/KubeEdge-Recovery abgefedert werden konnten, führt ein vollständiger Paketverlust zu einer nahezu vollständigen Unterbrechung der Anwendungserreichbarkeit während der Störphase.

Die Ergebnisse zeigen aber auch eine robuste Wiederherstellung nach Ende der Störung. Anders als im `70%`-Szenario war der After-Preflight in allen zehn Läufen erfolgreich, und die After Success Rate lag im Median bei `98.50%`. Dies deutet darauf hin, dass der vollständige, klar abgegrenzte Ausfall nach Cleanup konsistenter wiederhergestellt wurde als die stark schwankende, aber nicht vollständig unterbrochene Kommunikation bei `70%`.

Das Self-Healing reagierte deutlich sichtbar, konnte die Anwendung während der aktiven Kommunikationsunterbrechung aber nicht verfügbar halten. Die Mechanismen dienten daher vor allem der Erkennung der Störung und der Wiederherstellung nach Entfernen des Fehlers.

## Vergleichbare Einordnung

Im Vergleich zu `70%` Paketverlust ist `100%` Paketverlust weniger ambivalent: Während bei `70%` noch viele Requests sehr verspätet erfolgreich waren, fällt die Anwendung bei `100%` während der Fault-Phase fast vollständig aus. Die Fault Success Rate sinkt von `88.48%` im Median bei `70%` auf `3.83%` bei `100%`.

Gleichzeitig ist die Nachlaufphase bei `100%` stabiler als bei `70%`. Bei `70%` lag die After Success Rate nur bei `70.91%` im Median, während sie bei `100%` wieder `98.50%` erreichte. Dies spricht dafür, dass der vollständige Paketverlust nach Cleanup klarer und schneller in einen stabilen Zustand zurückgeführt werden konnte, während der starke, aber teilweise noch durchlässige Paketverlust bei `70%` länger zu instabilen Zwischenzuständen führte.

## Fazit

Ein Paketverlust von `100%` führt in der untersuchten KubeEdge-Testumgebung während der Störphase zu einer nahezu vollständigen Serviceunterbrechung. Die Fault Success Rate lag im Median nur bei `3.83%`, die Fault Error Rate bei `96.17%`.

KubeEdge zeigte dabei eindeutige Self-Healing-Reaktionen: Edge-Nodes wurden als `NodeNotReady` erkannt, Pods wurden zur Löschung markiert, Ersatz-Pods wurden erzeugt und nach Wiederherstellung wieder erfolgreich auf Edge-Nodes eingeplant. Während des vollständigen Verbindungsverlusts konnte die Anwendung jedoch nicht stabil verfügbar gehalten werden.

Nach Entfernen der Störung stellte sich der Cluster automatisch wieder her. Alle Nodes waren am Ende `Ready`, die Testanwendung lief wieder mit drei Pods, und der NodePort war erreichbar. Das Szenario zeigt damit die Grenze der Verfügbarkeit während einer vollständigen Kommunikationsunterbrechung, aber zugleich eine erfolgreiche automatische Wiederherstellung nach Ende der Störung.
