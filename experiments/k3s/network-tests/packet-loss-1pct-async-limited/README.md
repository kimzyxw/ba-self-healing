# Paketverlusttest 1% – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Test wurde das Verhalten der K3s-Testumgebung bei einem künstlich eingebrachten Paketverlust von 1% untersucht. Der Paketverlust wurde auf der Router-VM zwischen Server- und Worker-Netz mittels `tc netem` erzeugt. Dadurch wurde die Netzwerkkommunikation zwischen Control-Plane- und Worker-Netz gezielt gestört.

Untersucht wurde, ob bereits ein geringer Paketverlust Auswirkungen auf die Erreichbarkeit der Testanwendung oder auf Kubernetes-interne Self-Healing-Mechanismen hat.

## Parameter

| Parameter                  | Wert |
| -------------------------- | ---: |
| Eingebrachter Paketverlust |   1% |
| Vorlauf                    | 180s |
| Störphase                  | 600s |
| Nachlauf                   | 180s |
| Wiederholungen             |   10 |
| HTTP Timeout               | 300s |
| Request-Intervall          |   1s |
| Max. parallele Requests    |   10 |

## Validierung

* Vorhandene Runs: 10/10
* Routerpfad validiert: 10/10
* `tc netem loss 1%` aktiv: 10/10
* Cleanup nach Störphase dokumentiert: 10/10
* Keine `NotReady`-Events beobachtet
* Keine Pod-Fehlerereignisse (`Killing`, `BackOff`, `Failed`) beobachtet

Der Paketverlust wurde in allen Läufen erfolgreich auf dem Router-Interface aktiviert. Dies ist in den jeweiligen Dateien `tc_during.txt` dokumentiert.

## Zusammenfassung der HTTP-Messung

| Run           | Requests gesamt | Overall Success [%] | Fault Success [%] | Fault Error [%] | Recovery [s] | Bewertung            |
| ------------- | --------------: | ------------------: | ----------------: | --------------: | -----------: | -------------------- |
| run-01-router |             831 |              100.00 |            100.00 |            0.00 |         0.39 | auswertbar           |
| run-02-router |             959 |              100.00 |            100.00 |            0.00 |         0.46 | auswertbar           |
| run-03-router |             959 |              100.00 |            100.00 |            0.00 |         0.64 | auswertbar           |
| run-04-router |             959 |              100.00 |            100.00 |            0.00 |         0.58 | auswertbar           |
| run-05-router |             959 |              100.00 |            100.00 |            0.00 |         0.34 | auswertbar           |
| run-06-router |             959 |              100.00 |            100.00 |            0.00 |         0.21 | auswertbar           |
| run-07-router |             959 |              100.00 |            100.00 |            0.00 |         0.12 | auswertbar           |
| run-08-router |             155 |              100.00 |                NA |              NA |           NA | unvollständig        |
| run-09-router |             561 |              100.00 |            100.00 |            0.00 |           NA | teilweise auswertbar |
| run-10-router |              89 |              100.00 |                NA |              NA |           NA | unvollständig        |

Hinweis: Die Anzahl der Requests entspricht der Anzahl der Datenzeilen in `requests.csv`. Die Kopfzeile wurde dabei nicht mitgezählt.

## Aggregierte Metriken

Die Fault-bezogenen Metriken wurden nur über vollständig bzw. sinnvoll auswertbare Runs berechnet.

* Auswertbare Runs für die Fault-Phase: 7/10
* Fault Success Rate Mittelwert: 100.00%
* Fault Error Rate Mittelwert: 0.00%
* Recovery Time Mittelwert: 0.39s
* Recovery Time Minimum: 0.12s
* Recovery Time Maximum: 0.64s

## Interpretation

Ein Paketverlust von 1% hatte in den auswertbaren Läufen keine negativen Auswirkungen auf die Erreichbarkeit der Testanwendung. Während der Fault-Phase wurden alle HTTP-Requests erfolgreich beantwortet. Die Erfolgsrate lag damit sowohl insgesamt als auch während der aktiven Störung bei 100%.

Auch auf Cluster-Ebene wurden keine negativen Auswirkungen beobachtet. Alle Nodes blieben im Zustand `Ready`, es traten keine Pod-Ausfälle auf und es wurden keine relevanten Kubernetes-Fehlerereignisse dokumentiert. Insbesondere wurden keine Pod-Neustarts, keine `BackOff`-Zustände, keine `Failed`-Events und keine Rescheduling-Vorgänge beobachtet.

Damit wurden bei 1% Paketverlust keine Self-Healing-Mechanismen ausgelöst. Dies ist plausibel, da ein geringer Paketverlust auf TCP-Ebene in der Regel durch erneute Übertragungen kompensiert werden kann und daher nicht zwingend zu sichtbaren Fehlern auf Anwendungsebene oder Kubernetes-Ebene führt.

## Auffälligkeiten und Einschränkungen

Die Runs 08 bis 10 weisen eine deutlich geringere Anzahl aufgezeichneter Requests auf als erwartet. In Run 10 wurden beispielsweise nur Requests in der Baseline-Phase erfasst; während der Fault- und Nachlaufphase enthält die Messung keine Requests. Das äußere Testskript lief jedoch vollständig weiter, und der Paketverlust wurde auch in diesen Runs korrekt mittels `tc netem loss 1%` gesetzt und anschließend wieder entfernt.

Diese Auffälligkeit wird daher als Einschränkung der HTTP-Messung bzw. des Request-Monitors betrachtet, nicht als Effekt des simulierten Paketverlusts oder als Self-Healing-Verhalten des Clusters.

Für die Interpretation der Anwendungserreichbarkeit während der Fault-Phase werden deshalb primär die vollständig auswertbaren Runs 01 bis 07 herangezogen. Die Cluster-bezogenen Beobachtungen bleiben dennoch für alle zehn Runs relevant, da Nodes, Pods und Events vor und nach jedem Lauf dokumentiert wurden.

## Fazit

Der Test zeigt, dass ein Paketverlust von 1% in der untersuchten K3s-Testumgebung keine beobachtbaren Self-Healing-Reaktionen auslöst. Die Testanwendung blieb in den auswertbaren Läufen vollständig erreichbar, und der Clusterzustand blieb stabil. Ein Paketverlust dieser Größenordnung stellt für das getestete Setup daher keine ausreichend starke Störung dar, um Kubernetes-interne Wiederherstellungsmechanismen zu aktivieren.
