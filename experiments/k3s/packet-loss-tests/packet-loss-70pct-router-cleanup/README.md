# Ergebnisse – 70 % Paketverlust mit Router-gesteuertem Cleanup

## Versuchsaufbau

Zwischen den Control-Plane- und Worker-Knoten wurde mittels `tc netem` auf der Router-VM ein Paketverlust von 70 % simuliert.

Im Unterschied zu den vorherigen Paketverlusttests wurde die Störphase direkt auf der Router-VM gesteuert. Die Router-VM setzte die `tc netem`-Regel, wartete die konfigurierte Störphase lokal ab und entfernte die Regel anschließend selbstständig. Dadurch sollte verhindert werden, dass das Entfernen der Störung durch eine während der Fault-Phase beeinträchtigte SSH-Verbindung von `k3s-s1` zur Router-VM verzögert wird.

Für jeden Durchlauf waren 3 Minuten Vorlauf, 10 Minuten Störphase und 3 Minuten Nachlauf vorgesehen. Insgesamt wurden zehn Wiederholungen durchgeführt.

## Parameter

| Parameter | Wert |
|---|---:|
| Eingebrachter Paketverlust | 70 % |
| Vorlauf | 180 s |
| Störphase | 600 s |
| Nachlauf | 180 s |
| Wiederholungen | 10 |
| HTTP Timeout | 300 s |
| Request-Intervall | 1 s |
| Max. parallele Requests | 10 |
| Steuerung der Störung | lokal auf der Router-VM |

## Validierung

Der Paketverlust wurde in allen zehn Läufen erfolgreich aktiviert. In allen `tc_during.txt`-Dateien wurde eine aktive `netem`-Regel mit `loss 70%` dokumentiert. Nach Abschluss der Störung wurde in allen `tc_after.txt`-Dateien wieder die normale Queueing Discipline `fq_codel` dokumentiert.

Zusätzlich wurde für jeden Lauf ein `router_fault_job.log` erzeugt, das Start- und Endzeitpunkt der Router-seitig ausgeführten Störphase dokumentiert.

## Zeitliche Auffälligkeiten

Obwohl die Störphase lokal auf der Router-VM gesteuert wurde, traten erneut zeitliche Abweichungen auf. Die geplante Störphase von 600 Sekunden wurde in mehreren Läufen deutlich überschritten.

| Run | Bewertung der Fault-Dauer |
|---|---|
| run-01-router | verlängert |
| run-02-router | korrekt |
| run-03-router | korrekt |
| run-04-router | korrekt |
| run-05-router | korrekt |
| run-06-router | korrekt |
| run-07-router | verlängert |
| run-08-router | verlängert |
| run-09-router | verlängert |
| run-10-router | verlängert |

Für die quantitative Auswertung der HTTP-Metriken werden daher primär die methodisch sauberen Läufe `run-02` bis `run-06` berücksichtigt.

Die verlängerten Fault-Phasen werden nicht als Kubernetes-Self-Healing-Verhalten interpretiert, sondern als methodische Auffälligkeit der Experimentausführung. Da die Abweichungen im Router-seitigen `router_fault_job.log` sichtbar sind, liegt die Ursache vermutlich nicht mehr in der SSH-Steuerung von `k3s-s1`, sondern eher in Verzögerungen auf der Router-VM bzw. im lokalen Virtualisierungsumfeld.

## Zusammenfassung pro Run

| Run | Requests gesamt | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | Timeouts | Recovery [s] | Bewertung |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| run-01-router | 489 | 96.52 | 94.52 | 5.48 | 623.72 | 300729.44 | 17 | NA | verlängerte Fault-Phase |
| run-02-router | 687 | 97.67 | 95.15 | 4.85 | 630.24 | 55340.50 | 16 | 0.19 | auswertbar |
| run-03-router | 821 | 98.17 | 96.77 | 3.23 | 621.17 | 26653.57 | 15 | 0.73 | auswertbar |
| run-04-router | 577 | 96.88 | 92.86 | 7.14 | 635.84 | 300257.79 | 18 | 31.72 | auswertbar mit auffälliger Recovery |
| run-05-router | 746 | 97.72 | 95.63 | 4.37 | 624.88 | 52765.22 | 17 | 0.14 | auswertbar |
| run-06-router | 792 | 98.48 | 97.24 | 2.76 | 627.01 | 33355.96 | 12 | 0.05 | auswertbar |
| run-07-router | 402 | 98.26 | 96.86 | 3.14 | 626.48 | 503131.10 | 7 | NA | verlängerte Fault-Phase |
| run-08-router | 435 | 98.39 | 97.27 | 2.73 | 622.90 | 26899.05 | 7 | NA | verlängerte Fault-Phase |
| run-09-router | 426 | 97.65 | 95.93 | 4.07 | 624.17 | 66507.45 | 10 | NA | verlängerte Fault-Phase |
| run-10-router | 348 | 97.99 | 95.86 | 4.14 | 651.54 | 434946.16 | 7 | NA | verlängerte Fault-Phase |

## Aggregierte Metriken

Die folgenden Werte beziehen sich auf die methodisch saubersten Läufe `run-02` bis `run-06`.

- Auswertbare Läufe: 5/10
- Fault Success Rate: ca. 92.86 % bis 97.24 %
- Fault Error Rate: ca. 2.76 % bis 7.14 %
- Fault Median: ca. 621 ms bis 636 ms
- Fault p95: ca. 26.7 s bis 300.3 s
- Timeouts pro Lauf: 12 bis 18
- Recovery Time: überwiegend < 1 s, mit einem auffälligen Lauf bei ca. 31.7 s

## Kubernetes- und Self-Healing-Beobachtungen

Bei 70 % Paketverlust wurden in allen Läufen `NodeNotReady`-Events beobachtet. Betroffen waren sowohl `k3s-w1` als auch `k3s-w2`. Dies zeigt, dass die Kommunikation zwischen Control Plane und Worker-Knoten durch den Paketverlust so stark beeinträchtigt wurde, dass Kubernetes die Worker zeitweise als nicht erreichbar einstufte.

Gleichzeitig wurden keine Hinweise auf Pod-Neustarts, `BackOff`-, `Failed`- oder `Killing`-Events gefunden. Es wurden somit keine klassischen Self-Healing-Maßnahmen wie Pod-Neustarts oder Rescheduling-Vorgänge beobachtet.

Damit wurde zwar eine Kubernetes-interne Fehlererkennung ausgelöst, jedoch keine weitergehende automatische Wiederherstellung der Anwendung auf Pod-Ebene.

## Interpretation

Ein Paketverlust von 70 % stellt eine deutliche Störung der Anwendungskommunikation und der Clusterkommunikation dar. Im Vergleich zu 50 % Paketverlust steigen die Antwortzeiten und Fehlerraten deutlich an. Während die Baseline-Phasen stabil blieben, traten während der Fault-Phase regelmäßig Timeouts auf.

Die Anwendung blieb grundsätzlich erreichbar, erreichte jedoch keine vollständige Verfügbarkeit mehr. Die Erfolgsrate während der Fault-Phase lag in den auswertbaren Läufen ungefähr zwischen 93 % und 97 %.

Auf Cluster-Ebene wurden deutliche Auswirkungen sichtbar: Beide Worker-Knoten wurden zeitweise als `NodeNotReady` markiert. Dennoch wurden keine Pods neu gestartet oder auf andere Nodes verschoben. Dies zeigt, dass K3s die gestörte Node-Kommunikation erkennt, aber unter diesen Bedingungen nicht automatisch durch Rescheduling oder Pod-Neustarts reagiert.

## Methodische Einschränkung

Die zeitlichen Abweichungen in mehreren Läufen schränken die quantitative Vergleichbarkeit der vollständigen Messreihe ein. Für die Interpretation der HTTP-Metriken werden daher primär die zeitlich korrekten Läufe herangezogen.

Die qualitative Aussage bleibt dennoch belastbar: 70 % Paketverlust führt zu deutlichen Kommunikationsproblemen, regelmäßigen Timeouts und `NodeNotReady`-Events, ohne dass Pod-bezogene Self-Healing-Maßnahmen ausgelöst werden.

## Fazit

70 % Paketverlust überschreitet deutlich die Stabilitätsgrenze der untersuchten K3s-Testumgebung. Die Anwendung bleibt teilweise verfügbar, zeigt jedoch erhebliche Verzögerungen und Fehler. Kubernetes erkennt die gestörte Worker-Kommunikation und markiert Nodes als `NodeNotReady`, führt jedoch keine sichtbaren Self-Healing-Maßnahmen auf Anwendungsebene durch.
