# Ergebnisse – 1min Verbindungsabbruch

## Ziel des Experiments

In diesem Experiment wurde ein einminütiger Verbindungsabbruch zwischen Server-Netz und Worker-Netz simuliert. Ziel war es zu untersuchen, ob eine kurze, aber deutlich längere Unterbrechung als im 1s-Test bereits Auswirkungen auf die Anwendungserreichbarkeit oder auf Kubernetes-interne Self-Healing-Mechanismen zeigt.

Im Unterschied zu den Paketverlusttests wurde keine probabilistische Paketverlustrate mit `tc netem` gesetzt. Stattdessen wurde das Router-Interface `ens256` für die Dauer der Störung per `ip link set dev ens256 down` deaktiviert und anschließend wieder aktiviert. Dadurch wurde ein vollständiger temporärer Verbindungsabbruch zwischen den beiden internen Netzen erzeugt.

## Versuchsaufbau

Die Tests wurden auf dem bestehenden K3s-Testaufbau ausgeführt. Die Router-VM verbindet das Server-Netz mit dem Worker-Netz. Die Testanwendung läuft als NGINX-Deployment im Namespace `testapp` und wird über einen NodePort regelmäßig per HTTP-Request überwacht.

Der Request-Monitor sendet während des gesamten Durchlaufs Requests gegen die Testanwendung und protokolliert Status, Antwortzeit, Erfolg und Fehler. Zusätzlich werden vor und nach jedem Lauf Node-Zustände, Pod-Zustände, Kubernetes-Events und der Interface-Zustand auf dem Router dokumentiert.

Vor diesem Szenario wurde der Request-Monitor robuster konfiguriert: Er erhält einen größeren Zeitpuffer, wird aber am geplanten Testende aktiv beendet. Dadurch soll verhindert werden, dass der Monitor bei verzögerter Fault-Auslösung bereits vor der eigentlichen Störphase endet.

## Parameter

| Parameter               |                       Wert |
| ----------------------- | -------------------------: |
| Szenario                |            `link-cut-1min` |
| Fault-Typ               |          `ip link down/up` |
| Betroffenes Interface   | `ens256` auf der Router-VM |
| Geplante Fault-Dauer    |                       60 s |
| Vorlauf                 |                      180 s |
| Nachlauf                |                      180 s |
| Wiederholungen          |                         10 |
| Request-Intervall       |                        1 s |
| HTTP Timeout            |                      300 s |
| Max. parallele Requests |                         10 |
| Monitor-Puffer          |                     1800 s |
| Monitor-Beendigung      |          aktiv am Testende |

## Technische Validierung

Der Verbindungsabbruch wurde in allen zehn Läufen erfolgreich auf dem Router ausgeführt. In allen `router_fault_job.log`-Dateien wurde dokumentiert, dass das Interface `ens256` während der Störung in den Zustand `DOWN` versetzt und anschließend wieder in den Zustand `UP` zurückgesetzt wurde.

Auch die Dateien `interface_after_fault.txt` zeigen in allen Läufen, dass `ens256` nach dem Experiment wieder aktiv war:

```text
state UP
```

Damit ist die technische Durchführung des Link-Cuts grundsätzlich erfolgreich validiert.

## Zeitliche Beobachtungen

In den meisten Läufen lag die dokumentierte Fault-Dauer ungefähr bei einer Minute. Auffällig sind `run-02` und `run-08`: In `run-02` blieb der Link deutlich länger unterbrochen als geplant. In `run-08` war die Unterbrechung ebenfalls länger als 60 Sekunden, aber deutlich weniger stark als in `run-02`.

| Run           | Fault-Start | Router-Recovery | Bewertung                        |
| ------------- | ----------- | --------------- | -------------------------------- |
| run-01-router | 13:10:28    | 13:11:28        | korrekt                          |
| run-02-router | 13:18:38    | 13:34:59        | deutlich verlängerte Fault-Phase |
| run-03-router | 13:57:58    | 13:58:58        | korrekt                          |
| run-04-router | 14:06:08    | 14:07:08        | korrekt                          |
| run-05-router | 14:14:18    | 14:15:18        | korrekt                          |
| run-06-router | 14:22:28    | 14:23:28        | korrekt                          |
| run-07-router | 14:30:38    | 14:31:39        | nahezu korrekt                   |
| run-08-router | 15:09:15    | 15:10:35        | leicht verlängerte Fault-Phase   |
| run-09-router | 15:43:38    | 15:44:38        | korrekt                          |
| run-10-router | 15:55:59    | 15:56:59        | korrekt                          |

Für die quantitative Bewertung wird `run-02` wegen der stark verlängerten Fault-Dauer nur eingeschränkt betrachtet. `run-08` wird als methodisch auffällig markiert, kann aber qualitativ weiterhin einbezogen werden.

## Zusammenfassung pro Run

| Run           | Requests gesamt | Overall Success [%] | Fault Requests | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | Timeouts | Recovery [s] | Bewertung                      |
| ------------- | --------------: | ------------------: | -------------: | ----------------: | --------------: | ----------------: | -------------: | -------: | -----------: | ------------------------------ |
| run-01-router |             374 |              100.00 |             12 |            100.00 |            0.00 |          68021.50 |       68142.41 |        0 |         3.14 | auswertbar                     |
| run-02-router |             296 |              100.00 |             12 |            100.00 |            0.00 |         989048.56 |      989165.33 |        0 |         3.08 | verlängerte Fault-Phase        |
| run-03-router |             392 |               96.17 |             26 |             42.31 |           57.69 |           3071.45 |       68026.37 |        0 |         0.27 | auswertbar                     |
| run-04-router |             374 |              100.00 |             11 |            100.00 |            0.00 |          67961.91 |       68380.12 |        0 |         2.63 | auswertbar                     |
| run-05-router |             374 |              100.00 |             11 |            100.00 |            0.00 |          68276.65 |       68393.51 |        0 |         2.72 | auswertbar                     |
| run-06-router |             395 |               94.68 |             30 |             30.00 |           70.00 |           2114.64 |       68009.61 |        0 |         0.76 | auswertbar                     |
| run-07-router |             374 |              100.00 |             11 |            100.00 |            0.00 |          67965.21 |       68386.51 |        0 |         3.04 | auswertbar                     |
| run-08-router |             374 |              100.00 |             12 |            100.00 |            0.00 |          95045.84 |       95168.85 |        0 |         3.14 | leicht verlängerte Fault-Phase |
| run-09-router |             374 |              100.00 |             10 |            100.00 |            0.00 |          68110.06 |       68207.96 |        0 |         1.86 | auswertbar                     |
| run-10-router |             374 |              100.00 |             10 |            100.00 |            0.00 |          67965.59 |       68058.52 |        0 |         1.80 | auswertbar                     |

## Aggregierte Beobachtung der auswertbaren Läufe

Für die quantitative Interpretation werden vor allem die Läufe `run-01`, `run-03`, `run-04`, `run-05`, `run-06`, `run-07`, `run-09` und `run-10` betrachtet. `run-02` wird wegen der deutlich verlängerten Fault-Dauer ausgeschlossen. `run-08` wird wegen der leicht verlängerten Fault-Dauer als methodisch auffällig markiert.

In den auswertbaren Läufen zeigte sich:

* Baseline Success Rate: 100 % in allen Läufen
* Nachlauf Success Rate: 100 % in allen Läufen
* Keine Timeouts
* Keine Kubernetes-Events vom Typ `NodeNotReady`
* Keine `Killing`-, `BackOff`- oder `Failed`-Events
* Recovery Time nach dokumentierter Wiederherstellung: ca. 0.27 s bis 3.14 s
* Während der Fault-Phase traten sehr hohe Antwortzeiten auf, häufig um ca. 68 s

Die hohe Fault Success Rate in mehreren Läufen ist dabei vorsichtig zu interpretieren. Viele Requests, die während der Fault-Phase gestartet wurden, wurden nicht sofort beantwortet, sondern blieben während der Unterbrechung offen und wurden erst nach Wiederherstellung des Links erfolgreich abgeschlossen. Das zeigt sich an Fault-Median-Werten von ungefähr 68 Sekunden. Die Anwendung war während der Unterbrechung also nicht unbedingt unmittelbar erreichbar; vielmehr konnten einige Requests nach der Wiederherstellung erfolgreich beendet werden.

## Kubernetes-Events

In den Kubernetes-Events wurden keine `NodeNotReady`-Events beobachtet. Ebenso traten keine Hinweise auf `Killing`, `BackOff` oder `Failed` auf.

Damit wurden keine Self-Healing-Aktivitäten auf Node- oder Pod-Ebene ausgelöst. Insbesondere wurden keine Pods neu gestartet, keine Pods verschoben und keine Worker-Knoten als nicht erreichbar markiert.

Der Clusterzustand nach Abschluss der Experimente war stabil. Alle Nodes waren `Ready`, und alle Pods der Testanwendung befanden sich im Zustand `Running`.

## Anwendungsverhalten

Während der Baseline-Phasen war die Anwendung stabil erreichbar. In den meisten Läufen blieb die Erfolgsrate auch insgesamt bei 100 %. Allerdings zeigen die Messwerte während der Fault-Phase deutlich erhöhte Antwortzeiten. Viele Requests, die während der Unterbrechung gestartet wurden, hatten Antwortzeiten im Bereich von etwa 68 Sekunden.

Dieses Verhalten deutet darauf hin, dass die Requests während des Verbindungsabbruchs nicht unmittelbar fehlschlugen, sondern blockierten und nach Wiederherstellung der Verbindung erfolgreich abgeschlossen wurden. Aus Anwendungssicht bedeutet dies: Es kam nicht zwingend zu HTTP-Fehlern, aber zu deutlichen Verzögerungen. Für Nutzerinnen und Nutzer wäre diese Phase trotzdem als temporäre Nichtreaktion oder Hängen der Anwendung wahrnehmbar.

In zwei Läufen, `run-03` und `run-06`, sank die Fault Success Rate deutlich. In `run-03` lag sie bei 42.31 %, in `run-06` bei 30.00 %. Diese Läufe zeigen, dass ein einminütiger harter Link-Ausfall abhängig vom genauen Request-Timing auch zu fehlgeschlagenen Requests führen kann.

## Interpretation

Ein einminütiger Verbindungsabbruch war lang genug, um deutliche Auswirkungen auf die HTTP-Antwortzeiten zu erzeugen, aber nicht lang genug, um im Cluster sichtbare Node- oder Pod-bezogene Self-Healing-Mechanismen auszulösen.

Kubernetes markierte die Worker-Knoten während der Störung nicht als `NodeNotReady`. Es wurden keine Pods neu gestartet und keine Pods verschoben. Die Wiederherstellung der normalen Anwendungserreichbarkeit erfolgte nach Wiederherstellung des Router-Interfaces.

Im Vergleich zum 1s-Szenario zeigt der 1min-Test eine stärkere Wirkung auf die Anwendungsebene: Während beim 1s-Test nur kurze Latenzspitzen sichtbar waren, erzeugt der 1min-Abbruch sehr lange blockierende Requests. Gleichzeitig bleibt die Kubernetes-Ebene weiterhin unauffällig.

## Methodische Einschränkungen

`run-02` zeigte eine deutlich verlängerte Fault-Dauer und wird deshalb nicht als regulärer 1min-Lauf bewertet. `run-08` zeigte ebenfalls eine verlängerte Fault-Dauer, allerdings in geringerem Ausmaß.

Zusätzlich ist die Interpretation der Fault Success Rate eingeschränkt: Ein erfolgreicher Request während der Fault-Phase bedeutet nicht zwingend, dass die Anwendung während der Unterbrechung direkt erreichbar war. Da die Requests mit langem HTTP-Timeout laufen, können sie während des Link-Cuts blockieren und erst nach der Wiederherstellung erfolgreich abgeschlossen werden.

Für die Auswertung ist daher neben der Erfolgsrate insbesondere die Antwortzeit relevant. Die hohen Fault-Latenzen zeigen, dass der Verbindungsabbruch auf Anwendungsebene spürbar war, auch wenn viele Requests letztlich erfolgreich beendet wurden.

## Fazit

Der einminütige Verbindungsabbruch führte nicht zu sichtbaren Kubernetes-Self-Healing-Maßnahmen. Es wurden keine `NodeNotReady`-Events, keine Pod-Neustarts und kein Rescheduling beobachtet.

Auf Anwendungsebene war die Störung jedoch deutlich sichtbar. Viele Requests während der Fault-Phase blockierten und wurden erst nach Wiederherstellung des Links erfolgreich abgeschlossen. Dadurch blieb die Erfolgsrate in vielen Läufen hoch, während die Antwortzeiten massiv anstiegen.

Damit zeigt das 1min-Szenario eine wichtige Zwischenstufe: Die Störung ist länger und deutlich spürbarer als der 1s-Abbruch, aber noch nicht ausreichend, um eine sichtbare Kubernetes-Reaktion auf Node- oder Pod-Ebene auszulösen.
