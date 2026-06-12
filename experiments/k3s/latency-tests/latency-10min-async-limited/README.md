# Latenztest 10min – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Test wurde das Verhalten der Testanwendung bei einer künstlich eingebrachten Netzwerklatenz von 10 Minuten untersucht. Im Unterschied zum synchronen Monitor wurde ein asynchroner Request-Monitor verwendet, der mehrere Requests parallel offen halten kann. Die Parallelität wurde durch `max-in-flight` begrenzt, um unkontrollierte Backlog-Effekte zu reduzieren.

## Parameter

| Parameter | Wert |
|---|---:|
| Eingebrachte Latenz | 600s |
| Erwartete Round-Trip-Zeit | ca. 1200s |
| Vorlauf | 180s |
| Störphase | 1800s |
| Nachlauf | 180s |
| Wiederholungen | 10 |
| HTTP Timeout | 1800s |
| Request-Intervall | 1s |
| Max. parallele Requests | 10 |

## Validierung

- Vorhandene Runs: 10/10
- Routerpfad validiert: 10/10
- `tc netem delay 600s` aktiv: 10/10
- Cleanup nach Störphase dokumentiert: 10/10

## Zusammenfassung pro Run

| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >60s | >120s | >300s | Recovery [s] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| run-01-router | 13.60 | 0.09 | 99.91 | 2049.56 | 301755.65 | 77 | 66 | 60 | NA |
| run-02-router | 16.74 | 0.17 | 99.83 | 2051.15 | 37292.66 | 72 | 23 | 2 | 1.00 |
| run-03-router | 29.82 | 0.47 | 99.53 | 1690.58 | 12082.73 | 4 | 4 | 4 | NA |
| run-04-router | 16.79 | 0.11 | 99.89 | 2051.12 | 38305.99 | 80 | 43 | 2 | 1.35 |
| run-05-router | 16.84 | 0.17 | 99.83 | 2050.74 | 37083.00 | 61 | 8 | 2 | 1.42 |
| run-06-router | 16.74 | 0.06 | 99.94 | 2055.70 | 68462.66 | 97 | 47 | 2 | 1.23 |
| run-07-router | 14.67 | 0.09 | 99.91 | 2066.66 | 132582.03 | 103 | 55 | 4 | NA |
| run-08-router | 16.84 | 0.17 | 99.83 | 2051.37 | 38266.86 | 82 | 27 | 2 | 1.07 |
| run-09-router | 16.79 | 0.22 | 99.78 | 2052.76 | 69150.39 | 107 | 41 | 2 | 0.98 |
| run-10-router | 16.79 | 0.11 | 99.89 | 2053.53 | 69426.37 | 117 | 61 | 2 | 1.09 |

## Aggregierte Metriken

- Overall Request Success Rate Mittelwert: 17.56 %
- Fault Success Rate Mittelwert: 0.17 %
- Fault Success Rate Minimum: 0.06 %
- Fault Success Rate Maximum: 0.47 %
- Fault Error Rate Mittelwert: 99.83 %
- Recovery Time Mittelwert: 1.16 s
- Recovery Time Minimum: 0.98 s
- Recovery Time Maximum: 1.42 s

## Interpretation

Die Messreihe zeigt, dass die Testanwendung während der 10min-Latenz aus Client-Sicht praktisch nicht nutzbar war. Zwar wurden vereinzelt Requests erfolgreich abgeschlossen, die durchschnittliche Fault Success Rate lag jedoch nur bei 0,17 %. Die künstlich eingebrachte Latenz führte damit nicht zu einem sichtbaren Ausfall der Kubernetes-Komponenten, aber zu einer nahezu vollständigen Degradation der Anwendungserreichbarkeit während der Störphase.
Die sehr niedrige Fault Success Rate ist vor dem Hintergrund der erwarteten Round-Trip-Zeit von ca. 1200s zu interpretieren. Bei einer Störphase von 1800s und einem HTTP-Timeout von 1800s können nur wenige Requests innerhalb des betrachteten Fensters vollständig abgeschlossen werden.
Die Fault Success Rate ist die zentrale Kennzahl für dieses Szenario, da sie ausschließlich Requests betrachtet, die während der aktiven Störung gestartet wurden. Die Overall Success Rate ist ergänzend zu betrachten, da sie auch die störungsfreien Vor- und Nachlaufphasen enthält.

Die begrenzte asynchrone Messung bildet ein kontrolliertes Kommunikationsmodell ab: Mehrere Requests dürfen parallel offen sein, gleichzeitig wird ein unkontrollierter Request-Backlog durch `max-in-flight` begrenzt. Die Ergebnisse hängen daher neben K3s auch von Timeout, Request-Intervall und maximaler Parallelität ab.
