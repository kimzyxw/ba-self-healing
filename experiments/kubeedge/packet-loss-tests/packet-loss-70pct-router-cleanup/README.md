# KubeEdge Paketverlusttest: 70 %

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei einem Paketverlust von `70%` zwischen Cloud- und Edge-Netz verhält. Der Paketverlust wurde auf der Router-VM mit `tc/netem` auf dem Interface `ens161` erzeugt. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Paketverlusttests als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, wie KubeEdge bei stark gestörter Netzwerkkommunikation reagiert und ob native Self-Healing-Mechanismen die Anwendungserreichbarkeit stabilisieren können. Im Fokus standen HTTP-Verfügbarkeit, Latenzverhalten, Node-Zustände, Pod-Evictions, Scheduling-Verhalten und die Wiederherstellung eines stabilen Clusterzustands nach Ende der Störung.

## Versuchsaufbau

| Parameter                   |                               Wert |
| --------------------------- | ---------------------------------: |
| System                      |                           KubeEdge |
| Szenario                    | `packet-loss-70pct-router-cleanup` |
| Anzahl Läufe                |                               `10` |
| Paketverlust                |                              `70%` |
| Router-Interface            |                           `ens161` |
| Vorlaufphase                |                             `180s` |
| Störphase                   |                             `600s` |
| Nachlaufphase               |                             `180s` |
| HTTP-Timeout                |                             `300s` |
| Request-Intervall           |                               `1s` |
| Maximale parallele Requests |                               `10` |
| Ziel-URL                    |       `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Paketverlust wurde zentral auf der Router-VM eingebracht. Die Tests wurden mit Router-gesteuertem Cleanup und zusätzlichem Safety-Cleanup durchgeführt.

## Validierung der Testdurchführung

| Validierung                       | Ergebnis |
| --------------------------------- | -------: |
| Ausgewertete Läufe                |  `10/10` |
| Routerpfad gültig                 |  `10/10` |
| Paketverlust aktiv                |  `10/10` |
| `tc/netem` nach dem Lauf entfernt |  `10/10` |
| After-Preflight erfolgreich       |   `3/10` |

Die Messreihe ist vollständig und grundsätzlich auswertbar. In allen zehn Läufen wurde der Paketverlust erfolgreich mit `tc/netem loss 70%` aktiviert und nach der Störphase wieder entfernt. Der Routerpfad war in allen Läufen gültig, und das Cleanup wurde in allen Läufen dokumentiert.

Auffällig ist, dass der After-Preflight nur in `3/10` Läufen erfolgreich war. Dies zeigt, dass der Cluster unmittelbar nach der Störphase häufig noch nicht vollständig stabil war. Der finale Endzustand nach Abschluss der Messreihe war jedoch stabil: Alle Nodes waren `Ready`, die Testanwendung lief wieder mit drei Pods im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                           |          Wert |
| -------------------------------- | ------------: |
| Overall Success Rate, Median     |      `85.03%` |
| Overall Success Rate, Mittelwert |      `77.97%` |
| Overall Error Rate, Median       |      `14.96%` |
| Overall Error Rate, Mittelwert   |      `22.03%` |
| Overall Median Latenz            |      `2.27ms` |
| Overall p95 Latenz               |  `15578.89ms` |
| Overall p99 Latenz               |  `67169.27ms` |
| Overall max. Latenz, Median      | `253483.20ms` |
| Overall Timeouts gesamt          |           `4` |
| Baseline Success Rate, Median    |     `100.00%` |
| Baseline Median Latenz           |      `1.44ms` |
| Baseline p95 Latenz              |      `2.15ms` |
| Fault Success Rate, Median       |      `88.48%` |
| Fault Success Rate, Mittelwert   |      `79.27%` |
| Fault Error Rate, Median         |      `11.52%` |
| Fault Error Rate, Mittelwert     |      `20.73%` |
| Fault Median Latenz              |    `518.08ms` |
| Fault p95 Latenz                 |  `46041.81ms` |
| Fault p99 Latenz                 | `100598.29ms` |
| Fault max. Latenz, Median        | `253483.20ms` |
| Fault Timeouts gesamt            |           `4` |
| After Success Rate, Median       |      `70.91%` |
| After Success Rate, Mittelwert   |      `57.92%` |
| After Error Rate, Median         |      `29.09%` |
| After Error Rate, Mittelwert     |      `42.08%` |
| After Median Latenz              |      `1.66ms` |
| Recovery Time, Median            |       `0.90s` |
| Recovery Time, Mittelwert        |      `20.43s` |
| Recovery Time, Maximum           |     `117.99s` |

## Beobachtungen zur Anwendungserreichbarkeit

Bei `70%` Paketverlust war die Testanwendung nicht mehr durchgehend zuverlässig erreichbar. Während die Baseline-Phase weiterhin stabil war und eine mediane Success Rate von `100.00%` zeigte, sank die Success Rate während der Störphase deutlich. In der Fault-Phase lag die mediane Success Rate bei `88.48%`, der Mittelwert nur bei `79.27%`.

Auch die Latenzen stiegen massiv an. Der Fault-Median lag bei `518.08ms`, der Fault-p95 bei `46041.81ms` und der Fault-p99 bei `100598.29ms`. Einzelne Requests erreichten maximale Laufzeiten im Bereich mehrerer Minuten. Zusätzlich traten insgesamt `4` Timeouts auf.

Auffällig ist auch die Nachlaufphase. Obwohl der Paketverlust zu diesem Zeitpunkt bereits entfernt war, lag die After Success Rate im Median nur bei `70.91%` und im Mittel bei `57.92%`. Dies deutet darauf hin, dass der Cluster nach Ende der Netzstörung häufig noch mit Pod-Ersetzungen, Scheduling und Stabilisierung beschäftigt war.

## Kubernetes- und KubeEdge-Ereignisse

In den Events wurden in allen Läufen deutliche Hinweise auf Self-Healing- und Recovery-Aktivität beobachtet. Wiederholt wurden die Edge-Nodes `e1` und `e2` als `NodeNotReady` gemeldet. Auch Pods der Testanwendung sowie KubeEdge-nahe Komponenten wie `edgemesh-agent` und `edge-eclipse-mosquitto` waren von `NodeNotReady`-Warnungen betroffen.

Zusätzlich traten folgende Ereignistypen auf:

* `NodeNotReady` für `e1` und `e2`
* `NodeNotReady`-Warnungen für Testapp-Pods und KubeEdge-Komponenten
* `TaintManagerEviction`
* `Marking for deletion` für Pods der Testanwendung
* `Cancelling deletion` nach Wiederherstellung
* `FailedScheduling`
* `Successfully assigned` für neu geplante Pods
* Pods in Zuständen wie `Pending`, `ContainerCreating`, `Terminating` und teilweise `Completed`

Der Scheduler konnte Ersatz-Pods zeitweise nicht sofort platzieren, da beide Edge-Nodes während der Störung mit Taints belegt waren und die Cloud-Nodes wegen Node-Affinity bzw. Node-Selector nicht als Ziel infrage kamen. Sobald wieder ein Edge-Node nutzbar war, wurden Pods erneut auf `e1` oder `e2` eingeplant.

## Beobachtetes Self-Healing-Verhalten

Bei `70%` Paketverlust wurden native Self-Healing-Mechanismen deutlich sichtbar. KubeEdge bzw. die Kubernetes-Control-Plane erkannten die gestörte Kommunikation zu den Edge-Nodes und markierten diese wiederholt als `NodeNotReady`. Daraufhin wurden Taints gesetzt, Pod-Evictions eingeleitet und Ersatz-Pods erzeugt.

In mehreren Läufen wurden bestehende Pods zur Löschung markiert und neue Pods auf dem jeweils wieder verfügbaren Edge-Node eingeplant. Gleichzeitig zeigten die `FailedScheduling`-Events eine klare Grenze des Self-Healing-Verhaltens: Da die Anwendung nur auf Edge-Nodes laufen sollte, konnten Ersatz-Pods nicht auf Cloud-Nodes ausweichen. Wenn beide Edge-Nodes zeitweise als ungeeignet galten, blieb Scheduling vorübergehend blockiert.

Die Recovery war dadurch nicht mehr konstant kurz. Einige Läufe erreichten sehr schnelle Recovery-Zeiten unter einer Sekunde, während andere deutlich länger benötigten. In mehreren Läufen konnte keine Recovery Time bestimmt werden, da im Nachlauf kein erfolgreicher Request unterhalb des definierten Recovery-Schwellenwertes beobachtet wurde. Die maximale gemessene Recovery Time lag bei `117.99s`.

## Interpretation

Der Paketverlust von `70%` stellt eine schwere Netzwerkstörung dar. Im Unterschied zu `50%` Paketverlust ist nicht nur die Latenz massiv erhöht, sondern auch die Anwendungserreichbarkeit deutlich reduziert. Die Success Rate fällt während der Störung sichtbar ab, und selbst nach Ende der Störung bleibt der Cluster in mehreren Läufen zunächst instabil.

Das beobachtete Self-Healing ist aktiv, aber nicht vollständig ausreichend, um die Anwendung während der Störung stabil verfügbar zu halten. KubeEdge erkennt die gestörten Edge-Nodes, markiert sie als `NodeNotReady`, stößt Evictions und Scheduling-Prozesse an und stellt am Ende wieder einen stabilen Zustand her. Gleichzeitig führt die starke Beeinträchtigung beider Edge-Nodes dazu, dass Self-Healing während der Störung nur begrenzt greifen kann.

Die Ergebnisse zeigen damit eine wichtige Grenze der Architektur: Wenn alle zulässigen Edge-Zielknoten gleichzeitig gestört sind und Cloud-Nodes aufgrund der Platzierungsregeln ausgeschlossen sind, kann Kubernetes zwar Recovery-Prozesse starten, aber nicht immer sofort erfolgreich neue lauffähige Pods bereitstellen.

## Vergleichbare Einordnung

Im Vergleich zu den Szenarien mit `1%`, `10%` und `50%` Paketverlust zeigt `70%` erstmals eine deutlich reduzierte Anwendungserreichbarkeit. Während `1%` und `10%` vor allem Latenzspitzen verursachten und `50%` bereits Self-Healing-Mechanismen sichtbar machte, führt `70%` zu massiven Latenzen, HTTP-Fehlern, Timeouts, instabiler Nachlaufphase und häufigen Pod-Ersetzungen.

Damit liegt `70%` Paketverlust in dieser Testumgebung oberhalb der Schwelle, bei der KubeEdge zwar aktiv reagiert, die Störung aber nicht mehr vollständig transparent kompensieren kann.

## Fazit

Ein Paketverlust von `70%` beeinträchtigt KubeEdge stark. Die Anwendung bleibt nicht mehr durchgehend zuverlässig verfügbar, die Latenzen steigen massiv an, und es treten Timeouts sowie deutliche Fehleranteile auf.

KubeEdge zeigt klares Self-Healing-Verhalten: Edge-Nodes werden als `NodeNotReady` erkannt, Pods werden zur Löschung markiert, Ersatz-Pods werden erzeugt und nach Wiederherstellung wieder auf Edge-Nodes eingeplant. Gleichzeitig zeigen die Ergebnisse die Grenzen dieser Mechanismen. Wenn beide Edge-Nodes gleichzeitig beeinträchtigt sind und die Anwendung nicht auf Cloud-Nodes ausweichen darf, kann die Control Plane zwar reagieren, aber die Verfügbarkeit während der Störung nur eingeschränkt sichern.

Nach Ende der Störung stellte sich der Cluster wieder stabil dar. Das Szenario zeigt damit sowohl aktive Self-Healing-Reaktionen als auch eine deutliche Belastungsgrenze von KubeEdge bei starkem Paketverlust.
<
