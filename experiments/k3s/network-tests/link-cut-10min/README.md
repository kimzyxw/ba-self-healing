# Ergebnisse – 10min Verbindungsabbruch

## Ziel des Experiments

In diesem Experiment wurde ein zehnminütiger Verbindungsabbruch zwischen Server-Netz und Worker-Netz simuliert. Ziel war es zu untersuchen, wie sich ein längerer vollständiger Link-Ausfall auf die Anwendungserreichbarkeit und auf Kubernetes-interne Self-Healing-Mechanismen auswirkt.

Im Unterschied zu den Paketverlusttests wurde keine probabilistische Paketverlustrate mit `tc netem` gesetzt. Stattdessen wurde das Router-Interface `ens256` für die Dauer der Störung per `ip link set dev ens256 down` deaktiviert und anschließend wieder aktiviert. Dadurch wurde ein vollständiger temporärer Verbindungsabbruch zwischen den internen Netzen erzeugt.

## Versuchsaufbau

Die Tests wurden auf dem bestehenden K3s-Testaufbau ausgeführt. Die Router-VM verbindet das Server-Netz mit dem Worker-Netz. Die Testanwendung läuft als NGINX-Deployment im Namespace `testapp` und wird über einen NodePort regelmäßig per HTTP-Request überwacht.

Der Request-Monitor sendet während des gesamten Durchlaufs Requests gegen die Testanwendung und protokolliert Status, Antwortzeit, Erfolg und Fehler. Zusätzlich werden vor und nach jedem Lauf Node-Zustände, Pod-Zustände, Kubernetes-Events und der Interface-Zustand auf dem Router dokumentiert.

Der Request-Monitor wurde vor den Link-Cut-Experimenten robuster konfiguriert: Er erhält einen größeren Zeitpuffer und wird am geplanten Testende aktiv beendet. Dadurch soll verhindert werden, dass der Monitor bei verzögerter Fault-Auslösung bereits vor der eigentlichen Störphase endet.

## Parameter

| Parameter               |                       Wert |
| ----------------------- | -------------------------: |
| Szenario                |           `link-cut-10min` |
| Fault-Typ               |          `ip link down/up` |
| Betroffenes Interface   | `ens256` auf der Router-VM |
| Geplante Fault-Dauer    |                      600 s |
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

In den meisten Läufen lag die dokumentierte Fault-Dauer ungefähr bei zehn Minuten. Auffällig sind `run-01` und `run-10`, bei denen die Fault-Phase länger als geplant war.

| Run           | Fault-Start | Router-Recovery | Bewertung                                                |
| ------------- | ----------- | --------------- | -------------------------------------------------------- |
| run-01-router | 18:00:53    | 18:13:33        | verlängerte Fault-Phase                                  |
| run-02-router | 18:41:26    | 18:51:26        | korrekt                                                  |
| run-03-router | 18:58:36    | 19:08:36        | korrekt                                                  |
| run-04-router | 19:15:47    | 19:25:47        | korrekt                                                  |
| run-05-router | 19:32:57    | 19:42:57        | korrekt                                                  |
| run-06-router | 19:50:07    | 20:00:07        | korrekt                                                  |
| run-07-router | 20:07:17    | 20:17:17        | korrekt                                                  |
| run-08-router | 20:24:27    | 20:34:27        | korrekt                                                  |
| run-09-router | 20:41:37    | 20:51:37        | korrekt                                                  |
| run-10-router | 21:03:06    | 21:13:06        | Router-Log korrekt, Skriptzeit zeigt verlängerten Ablauf |

Für die quantitative Interpretation werden vor allem die Läufe `run-02` bis `run-09` betrachtet. `run-01` wird wegen der verlängerten Fault-Dauer als methodisch auffällig markiert. `run-10` enthält ebenfalls eine zeitliche Auffälligkeit zwischen Skriptzeit und Router-Log und wird daher vorsichtig interpretiert.

## Zusammenfassung pro Run

| Run           | Requests gesamt | Overall Success [%] | Overall Error [%] | Fault Requests | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | Timeouts | Recovery [s] | Bewertung               |
| ------------- | --------------: | ------------------: | ----------------: | -------------: | ----------------: | --------------: | ----------------: | -------------: | -------: | -----------: | ----------------------- |
| run-01-router |             842 |               43.82 |             56.18 |            478 |              1.05 |           98.95 |           1127.16 |        3102.72 |        1 |         0.71 | verlängerte Fault-Phase |
| run-02-router |             905 |               40.99 |             59.01 |            540 |              1.11 |           98.89 |           1661.88 |        3084.24 |        1 |         0.83 | auswertbar              |
| run-03-router |             842 |               43.71 |             56.29 |            477 |              0.63 |           99.37 |           1266.36 |        3102.22 |        1 |         0.75 | auswertbar              |
| run-04-router |             840 |               43.93 |             56.07 |            476 |              1.05 |           98.95 |           1384.74 |        3100.80 |        1 |         0.57 | auswertbar              |
| run-05-router |             938 |               39.45 |             60.55 |            573 |              0.87 |           99.13 |           1560.54 |        3093.84 |        1 |         0.65 | auswertbar              |
| run-06-router |             905 |               40.66 |             59.34 |            540 |              0.56 |           99.44 |           1301.72 |        3101.51 |        1 |         0.03 | auswertbar              |
| run-07-router |             906 |               40.95 |             59.05 |            541 |              1.11 |           98.89 |           1570.52 |        3019.85 |        1 |         0.60 | auswertbar              |
| run-08-router |             841 |               44.11 |             55.89 |            475 |              1.05 |           98.95 |           1132.02 |        3102.74 |        1 |         0.15 | auswertbar              |
| run-09-router |             841 |               43.64 |             56.36 |            476 |              0.42 |           99.58 |           1162.35 |        3106.07 |        1 |         0.31 | auswertbar              |
| run-10-router |             840 |               44.17 |             55.83 |            475 |              1.26 |           98.74 |           1369.60 |        3101.67 |        1 |         0.35 | zeitlich auffällig      |

## Aggregierte Beobachtung der auswertbaren Läufe

Für die quantitative Bewertung werden primär `run-02` bis `run-09` betrachtet. Diese Läufe zeigen ein sehr konsistentes Verhalten.

In den auswertbaren Läufen zeigte sich:

* Baseline Success Rate: 100 % in allen Läufen
* Nachlauf Success Rate: 100 % in allen Läufen
* Fault Success Rate: ca. 0.42 % bis 1.11 %
* Fault Error Rate: ca. 98.89 % bis 99.58 %
* Während der Fault-Phase trat pro Lauf mindestens ein Timeout auf
* Recovery Time nach dokumentierter Wiederherstellung: meist unter 1 s
* Keine Kubernetes-Events vom Typ `NodeNotReady` in den gespeicherten Event-Dateien
* Keine `Killing`-, `BackOff`- oder `Failed`-Events in den gespeicherten Event-Dateien

Damit unterscheidet sich das 10min-Szenario deutlich vom 1s- und 1min-Szenario. Während beim 1s-Test praktisch keine Anwendungsausfälle sichtbar waren und beim 1min-Test viele Requests blockierten und später erfolgreich beendet wurden, führte der 10min-Link-Cut während der Fault-Phase fast vollständig zu fehlerhaften Requests.

## Kubernetes-Events und Clusterzustand

In den gespeicherten Kubernetes-Events wurden keine `NodeNotReady`-Events gefunden. Ebenso traten keine Hinweise auf `Killing`, `BackOff` oder `Failed` auf.

Damit wurden in den Event-Logs keine sichtbaren Self-Healing-Aktivitäten auf Pod-Ebene dokumentiert. Insbesondere wurden keine Pods neu gestartet und keine Pods verschoben.

Nach Abschluss des Experiments war das Router-Interface `ens256` wieder aktiv. Der Clusterzustand zeigte jedoch, dass `k3s-w1` nach den Tests im Zustand `NotReady` war, während die Control-Plane-Nodes und `k3s-w2` `Ready` waren. Die NGINX-Pods liefen weiterhin auf den Server-Nodes und befanden sich im Zustand `Running`.

Dieses Ergebnis ist methodisch relevant: Obwohl die gespeicherten Events keine passenden `NotReady`-Einträge enthielten, war nach Abschluss des Szenarios ein Worker-Knoten nicht vollständig wiederhergestellt. Für die Interpretation bedeutet das, dass der 10min-Verbindungsabbruch nicht nur auf Anwendungsebene, sondern möglicherweise auch auf Node-Ebene Nachwirkungen hatte. Da die Testpods in diesem Setup auf den Server-Nodes liefen, führte der `NotReady`-Zustand von `k3s-w1` nicht zu einem sichtbaren Pod-Ausfall der Testanwendung.

## Anwendungsverhalten

Während der Baseline-Phasen war die Anwendung stabil erreichbar. Die Baseline Success Rate lag in allen Läufen bei 100 %. Auch nach der Wiederherstellung des Links war die Anwendung wieder stabil erreichbar; die Nachlaufphasen zeigten ebenfalls 100 % Success Rate.

Während der Fault-Phase änderte sich das Verhalten deutlich. In den auswertbaren Läufen lag die Fault Success Rate nur noch bei ungefähr 0.42 % bis 1.11 %. Der überwiegende Teil der Requests schlug also während des zehnminütigen Link-Cuts fehl.

Die Fault-Median-Werte lagen meist im Bereich von ungefähr 1.1 s bis 1.7 s, während die p95-Werte um ca. 3.0 s lagen. Zusätzlich traten pro Lauf einzelne sehr lange Ausreißer und mindestens ein Timeout auf. Dieses Verhalten zeigt, dass die Anwendung während der Unterbrechung praktisch nicht erreichbar war. Nach Wiederherstellung des Links normalisierten sich die Antwortzeiten wieder auf wenige Millisekunden.

## Interpretation

Ein zehnminütiger Verbindungsabbruch führte in diesem Setup zu einer klaren und reproduzierbaren Nichtverfügbarkeit der Anwendung während der Fault-Phase. Die Anwendung war in der Baseline und im Nachlauf stabil erreichbar, während der Störung jedoch fast vollständig nicht erreichbar.

Auf Kubernetes-Ebene wurden in den gespeicherten Event-Dateien keine Pod-bezogenen Self-Healing-Reaktionen sichtbar. Es gab keine dokumentierten Pod-Neustarts und kein Rescheduling. Gleichzeitig zeigte der Clusterzustand nach Abschluss des Szenarios, dass `k3s-w1` im Zustand `NotReady` war. Das deutet darauf hin, dass längere vollständige Verbindungsabbrüche Node-Zustände beeinflussen können, auch wenn die gespeicherten Events diesen Zustand nicht vollständig abbilden.

Im Vergleich zum 1min-Szenario ist der Unterschied deutlich: Beim 1min-Link-Cut blockierten viele Requests und wurden nach Wiederherstellung des Links noch erfolgreich abgeschlossen. Beim 10min-Link-Cut war die Störung so lang, dass fast alle Requests während der Fault-Phase fehlschlugen. Die Wiederherstellung der Anwendung nach Link-Recovery erfolgte jedoch schnell.

## Methodische Einschränkungen

`run-01` zeigte eine verlängerte Fault-Dauer und wird daher nur eingeschränkt als regulärer 10min-Lauf interpretiert. Auch `run-10` weist eine zeitliche Auffälligkeit zwischen Skriptzeit und Router-Log auf. Die übrigen Läufe zeigen jedoch ein sehr konsistentes Verhalten.

Zusätzlich ist zu beachten, dass die Testpods zum Zeitpunkt der Abschlussprüfung auf den Server-Nodes liefen. Dadurch führte der `NotReady`-Zustand von `k3s-w1` nicht direkt zu einem sichtbaren Pod-Ausfall der Testanwendung. Für eine isolierte Bewertung von Worker-Ausfällen müsste die Testanwendung gezielt auf Worker-Knoten platziert werden. Für diese Arbeit bleibt dennoch relevant, dass der getestete Zugriffspfad über das Worker-Netz durch den Router-Link-Cut stark beeinträchtigt wurde.

Die gespeicherten Events enthielten keine `NotReady`-Einträge, obwohl der abschließende Clusterzustand `k3s-w1` als `NotReady` zeigte. Daher sollte dieser Punkt als Beobachtung dokumentiert und vor dem nächsten Szenario separat geprüft werden.

## Fazit

Der zehnminütige Verbindungsabbruch führte zu einer deutlichen Nichtverfügbarkeit der Anwendung während der Fault-Phase. Die Fault Success Rate lag in den auswertbaren Läufen nur noch bei ungefähr 0.42 % bis 1.11 %, während Baseline und Nachlauf jeweils stabil bei 100 % lagen.

Kubernetes zeigte in den gespeicherten Event-Dateien keine Pod-bezogenen Self-Healing-Maßnahmen wie Neustarts oder Rescheduling. Nach Abschluss des Experiments war jedoch `k3s-w1` im Zustand `NotReady`, obwohl das Router-Interface wieder aktiv war. Damit zeigt das 10min-Szenario eine deutlich stärkere Wirkung als die kürzeren Link-Cuts: Die Anwendung fällt während der Unterbrechung nahezu vollständig aus, und es können Nachwirkungen auf Node-Ebene auftreten.
