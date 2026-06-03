# K3s Latenztest 1s (Pilotversuch)

## Ziel

Validierung des automatisierten Testframeworks zur Untersuchung des Verhaltens eines hochverfügbaren K3s-Clusters unter erhöhter Netzwerklatenz.

## Versuchsaufbau

* K3s-Cluster mit 3 Control-Plane-Nodes und 2 Worker-Nodes
* Testanwendung: nginx Deployment mit 3 Replikaten
* Erreichbarkeit über Kubernetes Service
* Netzwerktopologie mit separater Router-VM
* Latenzsimulation mittels Linux tc/netem auf der Router-VM

## Parameter

| Parameter      | Wert   |
| -------------- | ------ |
| Latenz         | 1 s    |
| Wiederholungen | 10     |
| Vorlauf        | 300 s  |
| Stördauer      | 2100 s |
| Nachlauf       | 300 s  |

## Validierung des Versuchs

Für jeden Durchlauf wurde vor Beginn mittels Traceroute geprüft, dass der Datenverkehr über die Router-VM (10.10.10.128) geleitet wird.

Während der Störphase wurde auf der Router-VM eine NetEm-Regel mit einer Verzögerung von 1 s aktiviert. Nach Ende der Störung wurde die Regel wieder entfernt und der ursprüngliche Queue-Disziplin-Zustand wiederhergestellt.

Die aufgezeichneten Antwortzeiten bestätigen die erfolgreiche Einbringung der Störung. Während der Störphase lagen die Medianwerte aller Durchläufe bei ca. 2009 ms. Dies entspricht der erwarteten Round-Trip-Latenz von etwa 2 s (1 s pro Richtung).

## Messergebnisse

### Verfügbarkeit

* Request Success Rate: 100 %
* Fehlerrate: 0 %

### Antwortzeiten während der Störphase

| Run | Median [ms] | p95 [ms] | p99 [ms] |
| --- | ----------: | -------: | -------: |
| 1   |      2008.5 |   2013.9 |   2019.5 |
| 2   |      2008.6 |   2013.8 |   2017.4 |
| 3   |      2009.4 |   2015.0 |   2018.5 |
| 4   |      2009.7 |   2014.0 |   2016.0 |
| 5   |      2009.7 |   2013.9 |   2015.7 |
| 6   |      2009.7 |   2014.0 |   2015.4 |
| 7   |      2009.7 |   2014.0 |   2015.8 |
| 8   |      2008.4 |   2012.2 |   2015.2 |
| 9   |      2009.3 |   2014.9 |   2095.7 |
| 10  |      2009.7 |   2013.9 |   2016.0 |

### Recovery Time

Nach Entfernen der NetEm-Regel normalisierten sich die Antwortzeiten innerhalb von ca. 11–16 Sekunden.

### Kubernetes-Verhalten

* Alle Nodes blieben im Zustand Ready.
* Keine Pod-Restarts.
* Keine Kubernetes-Events während der Versuche.
* Keine Ausfälle der Control Plane.

## Beobachtete Ausreißer

In einzelnen Durchläufen wurden sehr hohe Einzelwerte beobachtet (> 10 s bis mehrere Minuten). Diese Ausreißer traten nur vereinzelt auf und beeinflussten Median, p95 und p99 praktisch nicht.

Da die zentrale Fragestellung die Reaktion des Clusters auf die künstlich eingebrachte Netzwerklatenz betrifft, werden die robusteren Kennzahlen Median und Perzentile für die weitere Auswertung verwendet.

## Methodische Anpassung

Der Pilotversuch zeigte, dass eine Versuchsdauer von 35 Minuten Störzeit bei 10 Wiederholungen pro Szenario zu einem sehr hohen Gesamtzeitaufwand führt.

Da die korrekte Einbringung und Messung der Latenz erfolgreich nachgewiesen werden konnte, wird für die weiteren Latenzszenarien eine verkürzte Versuchsdauer verwendet.

Die weiteren Messungen werden mit reduziertem Vor- und Nachlauf durchgeführt, um die Anzahl der Wiederholungen beibehalten zu können und gleichzeitig eine praktikable Gesamtdauer der Versuchsreihe sicherzustellen.
