# Latenztest 60s – asynchroner Monitor mit begrenzter Parallelität

## Ziel

In diesem Test wurde das Verhalten der Testanwendung bei einer künstlich eingebrachten Netzwerklatenz von 60 Sekunden untersucht. Im Unterschied zum synchronen Monitor wurde ein asynchroner Request-Monitor verwendet, der mehrere Requests parallel offen halten kann. Die Parallelität wurde durch `max-in-flight` begrenzt, um unkontrollierte Backlog-Effekte zu reduzieren.

## Parameter

| Parameter | Wert |
|---|---:|
| Eingebrachte Latenz | 60s |
| Erwartete Round-Trip-Zeit | ca. 120s |
| Vorlauf | 180s |
| Störphase | 600s |
| Nachlauf | 180s |
| Wiederholungen | 10 |
| HTTP Timeout | 300s |
| Request-Intervall | 1s |
| Max. parallele Requests | 10 |

## Validierung

- Vorhandene Runs: 10/10
- Routerpfad validiert: 10/10
- `tc netem delay 60s` aktiv: 10/10
- Cleanup nach Störphase dokumentiert: 10/10

## Zusammenfassung pro Run

| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >60s | >120s | >300s | Recovery [s] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| run-01-router | 42.15 | 24.44 | 75.56 | 149035.19 | 562718.77 | 425 | 351 | 258 | NA |
| run-02-router | 52.85 | 31.00 | 69.00 | 180054.53 | 300489.94 | 468 | 408 | 155 | 1.17 |
| run-03-router | 45.36 | 12.67 | 87.33 | 99931.43 | 300187.31 | 373 | 270 | 77 | 1.14 |
| run-04-router | 53.86 | 39.44 | 60.56 | 427446.62 | 1388684.93 | 494 | 464 | 360 | NA |
| run-05-router | 41.20 | 1.86 | 98.14 | 1022081.67 | 1510904.69 | 203 | 202 | 183 | NA |
| run-06-router | 67.29 | 2.22 | 97.78 | 2941.81 | 38990.31 | 3 | 3 | 1 | NA |
| run-07-router | 41.92 | 14.62 | 85.38 | 2619240.93 | 2683748.36 | 333 | 324 | 286 | NA |
| run-08-router | 48.42 | 2.49 | 97.51 | 849522.66 | 1010124.97 | 143 | 142 | 142 | NA |
| run-09-router | 100.00 | NA | NA | NA | NA | 0 | 0 | 0 | NA |
| run-10-router | 30.56 | 7.96 | 92.04 | 135124.66 | 1043031.96 | 392 | 320 | 160 | NA |

## Aggregierte Metriken

- Overall Request Success Rate Mittelwert: 52.36 %
- Fault Success Rate Mittelwert: 15.19 %
- Fault Success Rate Minimum: 1.86 %
- Fault Success Rate Maximum: 39.44 %
- Fault Error Rate Mittelwert: 84.81 %
- Recovery Time Mittelwert: 1.15 s
- Recovery Time Minimum: 1.14 s
- Recovery Time Maximum: 1.17 s

Die aggregierten Fault-Metriken wurden nur über Runs mit auswertbarer Fault-Phase berechnet. Run 09 wurde dabei aufgrund fehlender Fault-Requests nicht in die Fault-Aggregation einbezogen.

## Interpretation

Die Messreihe zeigt, dass die Testanwendung während der 60s-Latenz weiterhin teilweise erreichbar blieb, jedoch mit deutlich reduzierter Erfolgsrate und stark erhöhten Antwortzeiten. Die Baseline-Phase war in den Runs stabil, und die Nachlaufphase erreichte, sofern Requests nach dem Recovery-Zeitpunkt erfasst wurden, wieder erfolgreiche Antworten.

Die Fault Success Rate ist die zentrale Kennzahl für dieses Szenario, da sie ausschließlich Requests betrachtet, die während der aktiven Störung gestartet wurden. Die Overall Success Rate ist ergänzend zu betrachten, da sie auch die störungsfreien Vor- und Nachlaufphasen enthält.

Die begrenzte asynchrone Messung bildet ein kontrolliertes Kommunikationsmodell ab: Mehrere Requests dürfen parallel offen sein, gleichzeitig wird ein unkontrollierter Request-Backlog durch `max-in-flight` begrenzt. Die Ergebnisse hängen daher neben K3s auch von Timeout, Request-Intervall und maximaler Parallelität ab.

## Auffälligkeiten und Einschränkungen

Die Messreihe wurde technisch erfolgreich durchgeführt, da für alle zehn Runs der Routerpfad validiert, die 60s-Latenz mittels `tc netem` gesetzt und nach der Störphase wieder entfernt wurde.

Bei der Auswertung zeigen sich jedoch Unterschiede zwischen den einzelnen Runs. Insbesondere Run 09 enthält keine auswertbaren Requests innerhalb der Fault-Phase (`Fault Success Rate = NA`). Dieser Lauf wird daher bei der Interpretation der Fault-bezogenen Kennzahlen als Sonderfall betrachtet.

Außerdem konnte die Recovery Time nur in einem Teil der Runs bestimmt werden. Ursache ist, dass bei hoher Latenz und einem Timeout von 300s auch nach Entfernen der Störung noch Requests aus der Fault-Phase aktiv sein können. Dadurch enthält die Nachlaufphase teilweise keine oder nur wenige neu gestartete Requests, die für die Recovery-Bestimmung verwendet werden können.

Die Fault Success Rate ist deshalb die wichtigste Kennzahl für die Bewertung der Nutzbarkeit während der Störung. Die Overall Success Rate ist nur ergänzend aussagekräftig, da sie auch die störungsfreien Vor- und Nachlaufphasen enthält.
