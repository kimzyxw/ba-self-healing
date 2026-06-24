# KubeEdge Paketverlusttest: 1 %

## Ziel des Experiments

In diesem Experiment wurde untersucht, wie sich KubeEdge bei geringem Paketverlust zwischen Cloud- und Edge-Netz verhält. Dazu wurde auf der Router-VM ein Paketverlust von `1%` auf dem Interface `ens161` eingebracht. Dieses Interface liegt auf der Edge-Seite des Routers und wurde analog zu den K3s-Paketverlusttests als Störpunkt für den Verkehr zwischen Cloud- und Edge-Netz verwendet.

Ziel war es zu prüfen, ob ein geringer Paketverlust bereits Auswirkungen auf die Erreichbarkeit der Testanwendung oder auf Kubernetes-/KubeEdge-interne Self-Healing-Mechanismen hat. Insbesondere wurde betrachtet, ob Nodes als `NotReady` markiert werden, Pods neu gestartet oder Scheduling-/Eviction-Mechanismen ausgelöst werden.

## Versuchsaufbau

| Parameter                   |                             Wert |
| --------------------------- | -------------------------------: |
| System                      |                         KubeEdge |
| Szenario                    | `packet-loss-1pct-async-limited` |
| Anzahl Läufe                |                             `10` |
| Paketverlust                |                             `1%` |
| Router-Interface            |                         `ens161` |
| Vorlaufphase                |                           `180s` |
| Störphase                   |                           `600s` |
| Nachlaufphase               |                           `180s` |
| HTTP-Timeout                |                           `300s` |
| Request-Intervall           |                             `1s` |
| Maximale parallele Requests |                             `10` |
| Ziel-URL                    |     `http://10.10.20.131:30080/` |

Die Requests wurden von `c1` gegen den NodePort der NGINX-Testanwendung auf `e1` gesendet. Der Paketverlust wurde mittels `tc/netem` auf der Router-VM erzeugt. Dadurch wurde der Verkehr zwischen Cloud- und Edge-Netz gezielt beeinträchtigt.

## Validierung der Testdurchführung

| Validierung                       | Ergebnis |
| --------------------------------- | -------: |
| Ausgewertete Läufe                |  `10/10` |
| Routerpfad gültig                 |  `10/10` |
| Paketverlust aktiv                |  `10/10` |
| `tc/netem` nach dem Lauf entfernt |  `10/10` |
| After-Preflight erfolgreich       |  `10/10` |

Die Messreihe ist vollständig und methodisch sauber auswertbar. In allen zehn Läufen wurde der Routerpfad korrekt validiert, der Paketverlust mit `tc/netem loss 1%` erfolgreich gesetzt und nach der Störphase wieder entfernt. Auch der After-Preflight war in allen Läufen erfolgreich.

Der Cluster befand sich nach Abschluss der Messreihe wieder in einem stabilen Zustand. Alle Nodes waren `Ready`, die drei Pods der Testanwendung liefen weiterhin im Zustand `Running`, und der NodePort war auf `e1` und `e2` erreichbar.

## Aggregierte Ergebnisse

| Metrik                        |       Wert |
| ----------------------------- | ---------: |
| Overall Success Rate, Median  |  `100.00%` |
| Overall Error Rate, Median    |    `0.00%` |
| Overall Median Latenz         |   `1.09ms` |
| Overall p95 Latenz            |   `1.60ms` |
| Overall p99 Latenz            |   `3.35ms` |
| Overall max. Latenz, Median   | `209.30ms` |
| Baseline Success Rate, Median |  `100.00%` |
| Baseline Median Latenz        |   `1.05ms` |
| Fault Success Rate, Median    |  `100.00%` |
| Fault Error Rate, Median      |    `0.00%` |
| Fault Median Latenz           |   `1.10ms` |
| Fault p95 Latenz              |   `1.60ms` |
| Fault p99 Latenz              |  `32.35ms` |
| Fault max. Latenz, Median     | `209.30ms` |
| Fault Timeouts gesamt         |        `0` |
| After Success Rate, Median    |  `100.00%` |
| After Median Latenz           |   `1.07ms` |
| Recovery Time, Median         |    `0.56s` |
| Recovery Time, Maximum        |    `0.95s` |

## Beobachtungen

Während der gesamten Messreihe blieb die Testanwendung vollständig erreichbar. Sowohl in der Baseline-Phase als auch während der aktiven Paketverlustphase und in der Nachlaufphase lag die mediane Erfolgsrate bei `100.00%`. Es traten keine HTTP-Fehler und keine Timeouts auf.

Der Paketverlust von `1%` hatte nur geringe Auswirkungen auf einzelne Antwortzeiten. Der Median der Fault-Latenz blieb mit `1.10ms` praktisch auf Baseline-Niveau. Auffällig ist lediglich der Anstieg des Fault-p99 auf `32.35ms` sowie einzelner maximaler Antwortzeiten bis in den Bereich von etwa `209ms`. Diese Werte deuten auf einzelne TCP-Neuübertragungen oder kurzfristige Verzögerungen hin, ohne die Anwendungserreichbarkeit sichtbar zu beeinträchtigen.

## Beobachtetes Self-Healing-Verhalten

Bei `1%` Paketverlust wurden keine sichtbaren Self-Healing-Mechanismen ausgelöst. Die Edge-Nodes blieben erreichbar, und es wurden keine relevanten Zustandsänderungen der Testanwendung beobachtet.

Insbesondere wurden keine Hinweise auf folgende Mechanismen gefunden:

* keine `NodeNotReady`-Zustände
* keine Pod-Neustarts
* keine `BackOff`-, `Failed`- oder `Killing`-Events
* keine Evictions
* kein Rescheduling der Testanwendung
* keine sichtbare Reaktion der Control Plane auf Anwendungsebene

Dieses Verhalten ist plausibel, da ein Paketverlust von `1%` auf TCP-Ebene weitgehend kompensiert werden kann. Aus Sicht von Kubernetes und KubeEdge blieb der Clusterzustand stabil, sodass keine Self-Healing-Maßnahmen erforderlich waren.

## Interpretation

Der Test zeigt, dass KubeEdge bei geringem Paketverlust stabil bleibt. Die Anwendung war in allen zehn Läufen vollständig verfügbar, und die gemessenen Latenzen blieben überwiegend im niedrigen Millisekundenbereich. Einzelne Ausreißer in der Fault-Phase hatten keinen Einfluss auf die Erfolgsrate.

Im Hinblick auf Self-Healing ist das Ergebnis vor allem als Negativbefund relevant: Es mussten keine Wiederherstellungsmechanismen greifen, weil der Paketverlust nicht stark genug war, um einen Pod-, Node- oder Kommunikationsfehler auf Kubernetes-Ebene auszulösen. Die Stabilität des Systems beruht in diesem Szenario daher nicht auf aktiver Kubernetes-Reparatur, sondern darauf, dass die Störung durch die Transportebene und die vorhandene Netzwerkstabilität kompensiert werden konnte.

## Vergleichbare Einordnung

Das Verhalten entspricht der Erwartung aus den K3s-Paketverlusttests: Auch dort führte ein Paketverlust von `1%` nicht zu sichtbaren Self-Healing-Reaktionen und beeinträchtigte die Anwendungserreichbarkeit nicht relevant. Für beide Systeme stellt `1%` Paketverlust damit keine ausreichend starke Störung dar, um native Self-Healing-Mechanismen zu aktivieren.

## Fazit

Ein Paketverlust von `1%` hat in der untersuchten KubeEdge-Testumgebung keine relevante Auswirkung auf die Anwendungserreichbarkeit. Die HTTP Success Rate blieb in allen Phasen bei `100%`, es traten keine Timeouts auf, und der Cluster blieb stabil.

Self-Healing-Mechanismen wurden nicht sichtbar ausgelöst. Dies ist nicht als Schwäche zu interpretieren, sondern als Hinweis darauf, dass die Störung unterhalb der Schwelle lag, ab der Kubernetes oder KubeEdge den Zustand als fehlerhaft behandeln.
