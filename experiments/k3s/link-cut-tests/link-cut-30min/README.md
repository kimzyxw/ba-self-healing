# Ergebnisse – 30min Verbindungsabbruch

## Ziel des Experiments

In diesem Experiment wurde ein 30-minütiger vollständiger Verbindungsabbruch zwischen Server-Netz und Worker-Netz simuliert. Ziel war es zu untersuchen, wie sich ein längerer Link-Ausfall auf die Anwendungserreichbarkeit sowie auf Kubernetes-interne Self-Healing-Mechanismen auswirkt.

Im Unterschied zu den Paketverlusttests wurde keine probabilistische Paketverlustrate mit `tc netem` gesetzt. Stattdessen wurde das Router-Interface `ens256` für die Dauer der Störung per `ip link set dev ens256 down` deaktiviert und anschließend wieder aktiviert. Dadurch wurde ein vollständiger temporärer Verbindungsabbruch zwischen den internen Netzen erzeugt.

## Versuchsaufbau

Die Tests wurden auf dem bestehenden K3s-Testaufbau ausgeführt. Die Router-VM verbindet das Server-Netz mit dem Worker-Netz. Die Testanwendung läuft als NGINX-Deployment im Namespace `testapp` und wird über einen NodePort regelmäßig per HTTP-Request überwacht.

Der Request-Monitor sendet während des gesamten Durchlaufs Requests gegen die Testanwendung und protokolliert Status, Antwortzeit, Erfolg und Fehler. Zusätzlich werden vor und nach jedem Lauf Node-Zustände, Pod-Zustände, Kubernetes-Events und der Interface-Zustand auf dem Router dokumentiert.

Vor dem erfolgreichen Durchlauf wurde ein abgebrochener 30min-Versuch aufgrund deutlicher Timing-Anomalien archiviert. Für den finalen Lauf wurde der Host aktiv wachgehalten und der Netzwerkzustand vorab erneut geprüft. Danach konnte das Szenario mit zehn Wiederholungen erfolgreich durchgeführt werden.

## Parameter

| Parameter               |                       Wert |
| ----------------------- | -------------------------: |
| Szenario                |           `link-cut-30min` |
| Fault-Typ               |          `ip link down/up` |
| Betroffenes Interface   | `ens256` auf der Router-VM |
| Geplante Fault-Dauer    |                     1800 s |
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

Der Clusterzustand nach Abschluss des Szenarios war ebenfalls stabil. Alle fünf Knoten waren `Ready`, die Pods der Testanwendung liefen weiterhin im Zustand `Running`, und beide Router-Interfaces waren wieder aktiv.

## Zeitliche Beobachtungen

Die dokumentierten Fault-Zeiten zeigen, dass die geplante Fault-Dauer von 30 Minuten in allen zehn Läufen eingehalten wurde. Die Wiederherstellung wurde jeweils wenige Sekunden nach dem Router-Recovery-Zeitpunkt dokumentiert.

| Run           | Fault-Start | Router-Recovery | Bewertung |
| ------------- | ----------- | --------------- | --------- |
| run-01-router | 18:24:28    | 18:54:29        | korrekt   |
| run-02-router | 19:01:39    | 19:31:39        | korrekt   |
| run-03-router | 19:38:49    | 20:08:49        | korrekt   |
| run-04-router | 20:15:59    | 20:45:59        | korrekt   |
| run-05-router | 20:53:09    | 21:23:09        | korrekt   |
| run-06-router | 21:30:19    | 22:00:19        | korrekt   |
| run-07-router | 22:07:30    | 22:37:30        | korrekt   |
| run-08-router | 22:44:40    | 23:14:40        | korrekt   |
| run-09-router | 23:21:50    | 23:51:50        | korrekt   |
| run-10-router | 23:59:00    | 00:29:00        | korrekt   |

Damit sind alle zehn Läufe für die quantitative Auswertung nutzbar.

## Zusammenfassung pro Run

| Run           | Requests gesamt | Overall Success [%] | Overall Error [%] | Fault Requests | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | Timeouts | Recovery [s] |
| ------------- | --------------: | ------------------: | ----------------: | -------------: | ----------------: | --------------: | ----------------: | -------------: | -------: | -----------: |
| run-01-router |            2100 |               17.52 |             82.48 |           1735 |              0.17 |           99.83 |           1129.05 |        3099.48 |        1 |         0.67 |
| run-02-router |            2103 |               17.64 |             82.36 |           1738 |              0.35 |           99.65 |           1131.78 |        3098.50 |        1 |         0.62 |
| run-03-router |            2038 |               17.96 |             82.04 |           1673 |              0.06 |           99.94 |           1130.79 |        3098.91 |        1 |         0.15 |
| run-04-router |            2119 |               17.32 |             82.68 |           1753 |              0.06 |           99.94 |           1195.07 |        3098.02 |        1 |         0.41 |
| run-05-router |            2039 |               18.05 |             81.95 |           1674 |              0.18 |           99.82 |           1129.25 |        3099.12 |        1 |         0.71 |
| run-06-router |            2039 |               18.00 |             82.00 |           1674 |              0.12 |           99.88 |           1127.43 |        3099.34 |        1 |         0.86 |
| run-07-router |            2103 |               17.64 |             82.36 |           1738 |              0.35 |           99.65 |           1154.80 |        3101.31 |        1 |         0.30 |
| run-08-router |            2039 |               18.15 |             81.85 |           1674 |              0.30 |           99.70 |           1128.58 |        3100.87 |        1 |         0.38 |
| run-09-router |            2102 |               17.51 |             82.49 |           1736 |              0.12 |           99.88 |           1151.05 |        3097.81 |        1 |         0.34 |
| run-10-router |            2103 |               17.64 |             82.36 |           1738 |              0.35 |           99.65 |           1129.57 |        3097.54 |        1 |         0.15 |

## Aggregierte Beobachtung

Die Ergebnisse sind über alle zehn Läufe sehr konsistent. In allen Läufen war die Anwendung während der Baseline stabil erreichbar. Die Baseline Success Rate lag jeweils bei 100 %. Auch nach Wiederherstellung des Links war die Anwendung wieder vollständig erreichbar; die Nachlaufphasen zeigten ebenfalls 100 % Success Rate.

Während der Fault-Phase änderte sich das Verhalten deutlich:

* Fault Success Rate: ca. 0.06 % bis 0.35 %
* Fault Error Rate: ca. 99.65 % bis 99.94 %
* Pro Lauf trat mindestens ein Timeout auf
* Fault Median: ca. 1.13 s bis 1.20 s
* Fault p95: ca. 3.10 s
* Recovery nach Link-Wiederherstellung: ca. 0.15 s bis 0.86 s

Damit war die Anwendung während des 30-minütigen Verbindungsabbruchs praktisch nicht erreichbar. Nach Wiederherstellung der Netzwerkverbindung normalisierte sich das Verhalten jedoch sehr schnell.

## Kubernetes-Events und Self-Healing-Verhalten

In den gespeicherten Kubernetes-Events wurden keine passenden `NodeNotReady`-, `Killing`-, `BackOff`-, `Failed`-, `Unhealthy`- oder `unreachable`-Events gefunden.

Auch nach Abschluss des Experiments waren alle Knoten im Zustand `Ready`. Die Pods der Testanwendung waren weiterhin `Running`. Es wurden keine Pod-Neustarts, keine BackOff-Zustände und kein Rescheduling beobachtet.

Damit wurden während des 30min-Link-Cuts keine sichtbaren Kubernetes-Self-Healing-Mechanismen auf Pod-Ebene ausgelöst. Die Anwendung war während der Störung zwar praktisch nicht erreichbar, Kubernetes reagierte aber nicht durch Neustart oder Verschiebung der Pods. Das liegt in diesem Setup auch daran, dass die Testpods auf den Server-Nodes liefen, während der Link-Cut den Zugriffspfad über das Worker-Netz unterbrach.

## Anwendungsverhalten

Aus Anwendungssicht führte der 30-minütige Verbindungsabbruch zu einer nahezu vollständigen Nichtverfügbarkeit während der Fault-Phase. Während Baseline und Nachlauf stabil waren, schlugen während des Link-Cuts fast alle Requests fehl.

Die niedrige Fault Success Rate von maximal 0.35 % zeigt, dass die Anwendung in dieser Phase für Clients über den getesteten NodePort-Pfad praktisch nicht erreichbar war. Die wenigen erfolgreichen Requests sind als Grenzfälle im Übergangsbereich oder als Timing-Effekte zu interpretieren.

Nach Wiederherstellung des Router-Interfaces war die Anwendung sehr schnell wieder erreichbar. Die Recovery-Zeit lag in allen Läufen unter einer Sekunde. Die Nachlaufphasen zeigen wieder stabile Antwortzeiten im Millisekundenbereich und 100 % Success Rate.

## Interpretation

Das 30min-Szenario bestätigt und verstärkt die Beobachtungen aus dem 10min-Link-Cut. Bereits beim 10min-Szenario war die Anwendung während der Fault-Phase nahezu vollständig nicht erreichbar. Der 30min-Test zeigt, dass sich dieses Verhalten bei längeren vollständigen Verbindungsabbrüchen konsistent fortsetzt.

Wichtig ist dabei die Trennung zwischen Anwendungsebene und Kubernetes-Ebene:

Auf Anwendungsebene ist die Störung massiv. Der getestete Zugriffspfad fällt während der Fault-Phase nahezu vollständig aus.

Auf Kubernetes-Ebene werden jedoch keine sichtbaren Self-Healing-Maßnahmen ausgelöst. Die Pods laufen weiter, werden nicht neu gestartet und nicht verschoben. Kubernetes behandelt den Zustand in diesem Experiment nicht als Pod-Ausfall, sondern die Anwendung bleibt lediglich über den gestörten Netzwerkpfad unerreichbar.

Die schnelle Recovery nach Wiederherstellung des Links zeigt, dass keine längere manuelle Reparatur notwendig war. Sobald die Netzwerkverbindung wiederhergestellt war, war auch die Anwendung wieder stabil erreichbar.

## Methodische Einordnung

Ein erster Versuch des 30min-Szenarios wurde aufgrund deutlicher Timing-Anomalien abgebrochen und separat archiviert. Im finalen Durchlauf wurden alle zehn Wiederholungen erfolgreich abgeschlossen. Die dokumentierten Fault-Zeiten zeigen, dass die geplante Fault-Dauer von 30 Minuten im finalen Durchlauf eingehalten wurde.

Für die Bewertung des 30min-Szenarios werden daher ausschließlich die finalen zehn Läufe verwendet.

## Fazit

Der 30-minütige Verbindungsabbruch führte in allen zehn Läufen zu einer nahezu vollständigen Nichtverfügbarkeit der Anwendung während der Fault-Phase. Die Fault Error Rate lag durchgehend bei ungefähr 99.65 % bis 99.94 %. Baseline und Nachlauf blieben dagegen stabil bei 100 % Success Rate.

Kubernetes zeigte keine sichtbaren Pod-bezogenen Self-Healing-Reaktionen. Es wurden keine Pod-Neustarts, keine BackOff-Zustände und kein Rescheduling beobachtet. Nach Wiederherstellung des Links normalisierte sich die Anwendungserreichbarkeit innerhalb von weniger als einer Sekunde.

Damit zeigt das 30min-Szenario: Lange vollständige Netzwerkunterbrechungen führen in diesem Aufbau zu massiver Nichtverfügbarkeit auf Anwendungsebene, ohne dass Kubernetes automatisch durch Pod-Neustart oder Rescheduling reagiert.
