# Latenztest 30min – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Test wurde das Verhalten des K3s-Clusters und der Testanwendung bei einer künstlich eingebrachten Netzwerklatenz von 30 Minuten untersucht. Aufgrund der erwarteten Round-Trip-Zeit von etwa 60 Minuten dient dieser Test vor allem als Extremfall zur Bewertung der Clusterstabilität und der Self-Healing-Mechanismen.

## Parameter

| Parameter | Wert |
|---|---:|
| Eingebrachte Latenz | 1800s |
| Erwartete Round-Trip-Zeit | ca. 3600s |
| Vorlauf | 180s |
| Störphase | 5400s |
| Nachlauf | 180s |
| Wiederholungen | 10 |
| HTTP Timeout | 3600s |
| Request-Intervall | 1s |
| Max. parallele Requests | 10 |

## Validierung

- Vorhandene Runs: 10/10
- Routerpfad validiert: 10/10
- `tc netem delay 1800s` aktiv: 10/10
- Cleanup nach Störphase dokumentiert: 10/10

## Zusammenfassung pro Run

| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >1800s | >3600s | Recovery [s] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run-01-router | 13.06 | 0.00 | 100.00 | 1596.64 | 3113.00 | 1 | 0 | NA |
| run-02-router | 6.24 | 0.00 | 100.00 | 1385.00 | 3110.59 | 0 | 0 | 1.61 |
| run-03-router | 5.28 | 0.00 | 100.00 | 1646.09 | 5110.21 | 2 | 0 | NA |
| run-04-router | 6.26 | 0.02 | 99.98 | 1377.14 | 3111.05 | 0 | 0 | 1.30 |
| run-05-router | 8.89 | 0.05 | 99.95 | 1531.70 | 3111.92 | 0 | 0 | NA |
| run-06-router | 7.56 | 0.05 | 99.95 | 1807.21 | 38917.33 | 6 | 0 | NA |
| run-07-router | 6.30 | 0.06 | 99.94 | 1525.09 | 3112.59 | 0 | 0 | 1.21 |
| run-08-router | 11.27 | 0.07 | 99.93 | 1605.35 | 5240.00 | 3 | 0 | NA |
| run-09-router | 9.38 | 0.06 | 99.94 | 1235.68 | 3107.05 | 1 | 0 | NA |
| run-10-router | 16.20 | 0.11 | 99.89 | 1630.62 | 10090.53 | 1 | 1 | NA |

## Aggregierte HTTP-Metriken

- Overall Request Success Rate Mittelwert: 9.05 %
- Fault Success Rate Mittelwert: 0.04 %
- Fault Error Rate Mittelwert: 99.96 %
- Recovery Time Mittelwert: 1.37 s
- Recovery Time Minimum: 1.21 s
- Recovery Time Maximum: 1.61 s

## Self-Healing- und Cluster-Stabilität

| Run | Nodes stabil | Pods stabil | Pod-Rescheduling | Zusätzliche Restarts | Kritische Events |
|---|---:|---:|---:|---:|---:|
| run-01-router | ja | ja | nein | nein | nein |
| run-02-router | ja | ja | nein | nein | nein |
| run-03-router | ja | ja | nein | nein | nein |
| run-04-router | ja | ja | nein | nein | nein |
| run-05-router | ja | ja | nein | nein | nein |
| run-06-router | ja | ja | nein | nein | nein |
| run-07-router | ja | ja | nein | nein | nein |
| run-08-router | ja | ja | nein | nein | nein |
| run-09-router | ja | ja | nein | nein | nein |
| run-10-router | ja | ja | nein | nein | nein |

## Interpretation

Die Messreihe zeigt, dass eine künstliche Netzwerklatenz von 30 Minuten die Anwendungskommunikation praktisch vollständig beeinträchtigt. Während der Störphase konnten nahezu keine HTTP-Requests erfolgreich abgeschlossen werden. Die Anwendung ist aus Client-Sicht unter diesen Bedingungen nicht sinnvoll nutzbar.

Gleichzeitig blieb das K3s-Cluster auf Infrastruktur-Ebene stabil. Die gespeicherten Node- und Pod-Zustände zeigen keine Hinweise auf Node-Ausfälle, Pod-Neuplanung oder zusätzliche Container-Restarts. Auch die aufgezeichneten Kubernetes-Events enthalten keine Hinweise auf kritische Ereignisse wie NotReady, BackOff, Evicted oder Killing.

Damit wurden durch die extreme Latenz keine klassischen Kubernetes-Self-Healing-Mechanismen ausgelöst. K3s erkennt in diesem Szenario keinen Pod- oder Node-Ausfall, obwohl die Anwendung aus Sicht des Clients faktisch nicht erreichbar ist. Die Störung betrifft somit primär die Anwendungskommunikation und nicht die Stabilität der Cluster-Komponenten.
