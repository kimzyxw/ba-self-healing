# Ergebnisse – 1s Verbindungsabbruch

## Ziel des Experiments

In diesem Experiment wurde ein sehr kurzer Verbindungsabbruch zwischen Server-Netz und Worker-Netz simuliert. Ziel war es zu untersuchen, ob ein einsekündiger harter Link-Ausfall bereits Auswirkungen auf die Anwendungserreichbarkeit oder auf Kubernetes-interne Self-Healing-Mechanismen zeigt.

Im Unterschied zu den Paketverlusttests wurde keine probabilistische Paketverlustrate mit `tc netem` gesetzt. Stattdessen wurde das Router-Interface `ens256` für die Dauer der Störung per `ip link set dev ens256 down` deaktiviert und anschließend wieder aktiviert. Dadurch wurde ein kurzer vollständiger Verbindungsabbruch zwischen den beiden internen Netzen erzeugt.

## Versuchsaufbau

Die Tests wurden auf dem bestehenden K3s-Testaufbau ausgeführt. Die Router-VM verbindet das Server-Netz mit dem Worker-Netz. Die Testanwendung läuft als NGINX-Deployment im Namespace `testapp` und wird über einen NodePort regelmäßig per HTTP-Request überwacht.

Der Request-Monitor sendet während des gesamten Durchlaufs Requests gegen die Testanwendung und protokolliert Status, Antwortzeit, Erfolg und Fehler. Zusätzlich werden vor und nach jedem Lauf Node-Zustände, Pod-Zustände, Kubernetes-Events und der Interface-Zustand auf dem Router dokumentiert.

## Parameter

| Parameter                   |                       Wert |
| --------------------------- | -------------------------: |
| Szenario                    |              `link-cut-1s` |
| Fault-Typ                   |          `ip link down/up` |
| Betroffenes Interface       | `ens256` auf der Router-VM |
| Fault-Dauer                 |                        1 s |
| Vorlauf                     |                      180 s |
| Nachlauf                    |                      180 s |
| Wiederholungen              |                         10 |
| Request-Intervall           |                        1 s |
| HTTP Timeout                |                      300 s |
| Max. parallele Requests     |                         10 |
| zusätzlicher Monitor-Puffer |                       60 s |

## Technische Validierung

Der Verbindungsabbruch wurde in allen zehn Läufen erfolgreich auf dem Router ausgeführt. In allen `router_fault_job.log`-Dateien wurde dokumentiert, dass das Interface `ens256` während der Störung in den Zustand `DOWN` versetzt und anschließend wieder in den Zustand `UP` zurückgesetzt wurde.

Auch die Dateien `interface_after_fault.txt` zeigen in allen Läufen, dass `ens256` nach dem Experiment wieder aktiv war:

```text
state UP
```

Damit ist die technische Durchführung des Link-Cuts erfolgreich validiert.

## Zeitliche Beobachtungen

Der Router-Job dokumentierte in allen Läufen einen kurzen Interface-Abbruch. In den meisten Läufen lag zwischen `fault_start` und `router_recovery_time` ungefähr eine Sekunde. In einem Lauf lag die dokumentierte Differenz bei etwa zwei Sekunden.

| Run           | Fault-Start | Router-Recovery | Bewertung                                    |
| ------------- | ----------- | --------------- | -------------------------------------------- |
| run-01-router | 08:40:26    | 08:40:27        | korrekt                                      |
| run-02-router | 08:48:30    | 08:48:31        | korrekt                                      |
| run-03-router | 09:15:44    | 09:15:45        | korrekt                                      |
| run-04-router | 09:36:11    | 09:36:12        | technisch korrekt, quantitativ eingeschränkt |
| run-05-router | 09:57:51    | 09:57:52        | korrekt                                      |
| run-06-router | 10:30:44    | 10:30:46        | leicht verlängert, quantitativ eingeschränkt |
| run-07-router | 10:58:11    | 10:58:12        | korrekt                                      |
| run-08-router | 11:26:51    | 11:26:52        | technisch korrekt, quantitativ eingeschränkt |
| run-09-router | 11:34:02    | 11:34:03        | korrekt, leicht verkürzte Nachlaufdaten      |
| run-10-router | 12:02:35    | 12:02:36        | technisch korrekt, quantitativ eingeschränkt |

In mehreren Läufen traten methodische Auffälligkeiten bei der zeitlichen Struktur der Messung auf. Besonders `run-04`, `run-06`, `run-08` und `run-10` enthalten kaum oder keine Fault- und After-Daten im Summary. Ursache ist, dass der Request-Monitor in diesen Läufen bereits weitgehend oder vollständig vor der eigentlichen Fault-Phase beendet war. Diese Läufe werden daher für die quantitative HTTP-Auswertung nur eingeschränkt berücksichtigt.

Für die inhaltliche Bewertung der technischen Durchführung bleiben sie dennoch relevant, da der Interface-Abbruch selbst in den Router-Logs eindeutig dokumentiert wurde.

## Zusammenfassung pro Run

| Run           | Requests gesamt | Overall Success [%] | Fault Requests | Fault Success [%] | Fault p95 [ms] | Timeouts | Recovery [s] | Bewertung                 |
| ------------- | --------------: | ------------------: | -------------: | ----------------: | -------------: | -------: | -----------: | ------------------------- |
| run-01-router |             421 |              100.00 |              3 |            100.00 |         209.11 |        0 |         0.60 | auswertbar                |
| run-02-router |             296 |              100.00 |              3 |            100.00 |         204.94 |        0 |         0.51 | teilweise auswertbar      |
| run-03-router |             421 |              100.00 |              4 |            100.00 |         209.93 |        0 |         0.02 | auswertbar                |
| run-04-router |             107 |              100.00 |              0 |                NA |             NA |        0 |           NA | quantitativ eingeschränkt |
| run-05-router |             421 |              100.00 |              3 |            100.00 |         212.21 |        0 |         0.47 | auswertbar                |
| run-06-router |              26 |              100.00 |              0 |                NA |             NA |        0 |           NA | quantitativ eingeschränkt |
| run-07-router |             421 |              100.00 |              4 |            100.00 |         206.20 |        0 |         0.02 | auswertbar                |
| run-08-router |             131 |              100.00 |              0 |                NA |             NA |        0 |           NA | quantitativ eingeschränkt |
| run-09-router |             360 |              100.00 |              4 |            100.00 |         206.44 |        0 |         0.74 | teilweise auswertbar      |
| run-10-router |              49 |              100.00 |              0 |                NA |             NA |        0 |           NA | quantitativ eingeschränkt |

## Aggregierte Beobachtung der auswertbaren Läufe

Für die quantitative Bewertung werden vor allem `run-01`, `run-03`, `run-05` und `run-07` betrachtet, da diese vollständige Vorlauf-, Fault- und Nachlaufdaten enthalten. `run-02` und `run-09` zeigen ebenfalls verwertbare Fault-Daten, enthalten aber verkürzte Nachlaufdaten.

In den auswertbaren Läufen zeigte sich:

* Overall Success Rate: 100 %
* Baseline Success Rate: 100 %
* Fault Success Rate: 100 %
* After Success Rate: 100 %
* Timeouts: 0
* Keine HTTP-Fehler während der Störung
* Recovery Time: unter 1 Sekunde
* Fault p95: ungefähr 205 ms bis 212 ms

Damit führte ein einsekündiger Verbindungsabbruch in diesem Setup nicht zu einer messbaren Nichtverfügbarkeit der Anwendung. Die Anwendung blieb während aller quantitativ auswertbaren Fault-Phasen erreichbar.

## Kubernetes-Events

In den Kubernetes-Events wurden keine `NodeNotReady`-Events beobachtet. Ebenso traten keine Hinweise auf `Killing`, `BackOff` oder `Failed` auf.

Damit wurden keine Self-Healing-Aktivitäten auf Node- oder Pod-Ebene ausgelöst. Insbesondere wurden keine Pods neu gestartet, keine Pods verschoben und keine Worker-Knoten als nicht erreichbar markiert.

Der Clusterzustand nach Abschluss der Experimente war stabil. Alle Nodes waren `Ready`, und alle Pods der Testanwendung befanden sich im Zustand `Running`.

## Interpretation

Ein Verbindungsabbruch von einer Sekunde war in diesem lokalen K3s-Setup zu kurz, um eine sichtbare Störung auf Kubernetes-Ebene auszulösen. Die Control Plane markierte die Worker-Knoten nicht als `NotReady`, und es wurden keine Pod-bezogenen Self-Healing-Maßnahmen beobachtet.

Auf Anwendungsebene blieb die Testanwendung vollständig erreichbar. Einzelne Requests während der Fault-Phase zeigten zwar erhöhte Antwortzeiten im Bereich von ungefähr 200 ms, es kam jedoch zu keinen Timeouts und zu keinen HTTP-Fehlern.

Die Ergebnisse sprechen dafür, dass sehr kurze Link-Unterbrechungen durch TCP, Routing-Verhalten und die kurze Dauer der Störung abgefangen werden können, ohne dass Kubernetes eingreifen muss. Aus Sicht der Self-Healing-Bewertung bedeutet das: Für einen einsekündigen Verbindungsabbruch ist keine aktive Recovery durch Kubernetes sichtbar, weil der Fehlerzustand zu kurz ist, um als Node- oder Pod-Fehler behandelt zu werden.

## Methodische Einschränkung

Mehrere Läufe enthalten unvollständige quantitative Messdaten, da der Request-Monitor teilweise nicht mehr während der eigentlichen Fault- und Nachlaufphase aktiv war. Diese Läufe werden deshalb nicht für die quantitative Bewertung der HTTP-Metriken herangezogen.

Die technische Durchführung des Link-Cuts ist davon getrennt zu betrachten: Der Interface-Zustand wurde in allen Läufen korrekt dokumentiert, und das Interface wurde nach der Störung wiederhergestellt.

Für die weiteren Verbindungsabbruchtests mit längeren Fault-Dauern sollte besonders darauf geachtet werden, ob Monitor-Laufzeit und tatsächliche Fault-Zeit sauber überlappen. Gegebenenfalls sollte das Skript angepasst werden, sodass der Monitor erst unmittelbar vor der geplanten Vorlaufphase startet und Verzögerungen vor der Fault-Phase stärker erkannt oder markiert werden.

## Fazit

Der einsekündige Verbindungsabbruch führte in den auswertbaren Läufen zu keiner Nichtverfügbarkeit der Anwendung. Die Erfolgsrate blieb in Baseline, Fault und Nachlauf bei 100 %. Kubernetes erkannte keinen Node-Ausfall und löste keine Self-Healing-Maßnahmen aus.

Damit bildet das 1s-Szenario den niedrigsten Schweregrad der Verbindungsabbruchtests. Es zeigt, dass sehr kurze Netzwerkunterbrechungen in diesem Setup toleriert werden, ohne dass die Anwendung ausfällt oder Kubernetes sichtbar reagiert.
