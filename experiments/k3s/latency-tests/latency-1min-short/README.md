# Latenztest 1min – verkürzte Messreihe

## Ziel

Untersuchung des Verhaltens des HA-K3s-Clusters bei erhöhter Netzwerklatenz zwischen Server- und Worker-Netz. Die Latenz wurde auf der Router-VM mittels `tc/netem` eingebracht.

## Parameter

| Parameter | Wert |
|---|---:|
| Eingebrachte Latenz | 60s |
| Erwartete Round-Trip-Zeit | ca. 120s |
| Vorlauf | 180s |
| Störphase | 600s |
| Nachlauf | 180s |
| Wiederholungen | 10 |
| HTTP Timeout | 180s |
| Request-Intervall | 1s |

## Validierung

Alle Runs valide: **ja**

Für jeden Durchlauf wurde geprüft, ob der Netzwerkpfad über die Router-VM `10.10.10.128` verläuft, ob `tc/netem delay 60s` aktiv war und ob nach der Störphase wieder `fq_codel` gesetzt war.

## Zusammenfassung pro Run

| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >60s | >120s |
|---|---:|---:|---:|---:|---:|---:|---:|
| run-01-router | 92.34 | 4.55 | 95.45 | 3071.59 | 182849.99 | 3 | 3 |
| run-02-router | 93.96 | 9.09 | 90.91 | 3071.93 | 233541.87 | 3 | 3 |
| run-03-router | 99.14 | 25.00 | 75.00 | 186277.06 | 243148.71 | 3 | 3 |
| run-04-router | 98.61 | 28.57 | 71.43 | 3072.69 | 292225.94 | 3 | 2 |
| run-05-router | 95.86 | 7.14 | 92.86 | 3072.09 | 342815.88 | 4 | 3 |
| run-06-router | 97.04 | 9.09 | 90.91 | 3071.97 | 1227176.88 | 3 | 3 |
| run-07-router | 95.43 | 6.25 | 93.75 | 3071.30 | 1636944.29 | 3 | 3 |
| run-08-router | 92.00 | 13.04 | 86.96 | 3071.74 | 125469.89 | 4 | 4 |
| run-09-router | 93.30 | 10.71 | 89.29 | 3071.66 | 122076.59 | 3 | 2 |
| run-10-router | 96.53 | 13.33 | 86.67 | 3071.87 | 240074.61 | 3 | 3 |

## Aggregierte Metriken

- Overall Request Success Rate: 95.42 % (mit Vor- und Nachlaufzeit)
- Fault Success Rate Mittelwert: 12.68 %
- Fault Error Rate Mittelwert: 87.32 %
- Recovery Time Mittelwert: 51.12 s
- Recovery Time Minimum: 1.17 s
- Recovery Time Maximum: 135.21 s

## Interpretation

Bei einer eingebrachten Latenz von 60s war die Anwendung nicht mehr zuverlässig nutzbar. Während die Baseline- und Nachlaufphase stabile Antwortzeiten im einstelligen Millisekundenbereich zeigten, kam es während der Störphase zu stark verzögerten Requests, Timeouts oder Verbindungsfehlern.

Die Ergebnisse unterscheiden sich deutlich vom 1s-Latenztest: Dort blieb die Anwendung bei erhöhter Antwortzeit vollständig erreichbar. Bei 60s Latenz treten dagegen bereits deutliche Nutzbarkeitsprobleme auf.

## Hinweise zur Auswertung

Für hohe Latenzen ist der Median aller Fault-Requests nur eingeschränkt aussagekräftig, da viele Requests während der Störung abbrechen oder über Phasengrenzen hinweg laufen. Deshalb werden erfolgreiche Requests, Fehlerquote, lange Requests (`>60s`, `>120s`) und Recovery Time gemeinsam betrachtet.

## Kubernetes-Verhalten

Die Dateien `nodes_before.txt`, `nodes_after.txt`, `pods_before.txt`, `pods_after.txt`, `events_before.txt` und `events_after.txt` wurden pro Run gespeichert. Sie dienen zur Prüfung von Node-Zuständen, Pod-Restarts und Kubernetes-Events.
