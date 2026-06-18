# Verworfene explorative KubeEdge-Testreihe

Dieser Ordner enthält den vollständigen früheren KubeEdge-Stand:
Testläufe, Smoke-Tests, Auswertungen, Skripte, Baseline-Artefakte und
EdgeMesh-bezogene Zwischenstände.

## Status

Die Inhalte dieses Ordners sind nicht Bestandteil der finalen
Ergebnisbasis der Bachelorarbeit. Sie werden nicht für Tabellen,
Diagramme oder quantitative Vergleiche verwendet.

## Grund der Verwerfung

Die frühen KubeEdge-Pod- und Komponenten-/Node-Ausfälle verwendeten
einen asynchronen Request-Monitor. Die finalen K3s-Pod- und Node-Ausfälle
wurden dagegen synchron gemessen.

Dadurch sind insbesondere Request Success Rate, Fehlerrate und
Latenzkennzahlen nicht direkt vergleichbar. Die finale KubeEdge-Testreihe
wird daher vollständig mit einem methodisch an K3s angeglichenen,
konsistenten Vorgehen wiederholt.

## Finale Methodik

- Pod- und Komponenten-/Node-Ausfälle: synchroner Request-Monitor
- Latenz, Paketverlust und Verbindungsabbrüche: asynchroner
  Request-Monitor mit derselben Begrenzung paralleler Requests wie K3s
- zehn vollständige Wiederholungen pro finalem Szenario
- einheitliche Artefakte pro Run: Requests, Zeitstempel, Zustände,
  Events, Fault-Nachweis und Zusammenfassung
