# Archivierte Vorläufe: KubeEdge Node-Failure

Dieser Ordner enthält verworfene Vorläufe der KubeEdge-Node-Failure-Experimente. Die Daten werden aus Gründen der Nachvollziehbarkeit aufbewahrt, aber **nicht für die finale Auswertung verwendet**.

## Hintergrund

Die Experimente wurden im Rahmen der Untersuchung des Self-Healing-Verhaltens von KubeEdge durchgeführt. Ziel des Szenarios war es, den Ausfall eines Edge-Knotens zu simulieren, indem der Dienst `edgecore.service` auf einem Edge-Knoten gestoppt und nach einer definierten Fehlerdauer wieder gestartet wurde.

Die reguläre Testreihe sollte aus zehn Läufen bestehen. Dabei wurden die Zielknoten abwechselnd getestet:

* `e1` mit der IP-Adresse `10.10.20.131`
* `e2` mit der IP-Adresse `10.10.20.132`

Als Testanwendung wurde die dreifach replizierte NGINX-Testanwendung im Namespace `testapp` verwendet. Die HTTP-Anfragen wurden über den NodePort der KubeEdge-/EdgeMesh-Umgebung gemessen.

## Grund für die Archivierung

Die ursprünglichen Läufe werden nicht für die finale Bewertung verwendet, da während der Durchführung Timing-Anomalien aufgetreten sind.

Insbesondere ab `run-07` wich die tatsächliche Laufzeit deutlich von der geplanten Versuchsdauer ab. Mehrere Läufe enthielten wesentlich weniger Requests als erwartet. Zusätzlich lagen die gemessenen Recovery-Zeiten teilweise im Bereich von über einer Stunde. Dadurch ist davon auszugehen, dass die Messung durch externe Faktoren beeinflusst wurde, beispielsweise durch eine pausierte VM, Energiesparverhalten des Hostsystems oder ein blockierendes Skriptverhalten.

Auch wenn in den aufgezeichneten Requests keine Fehler auftraten und die Knoten am Ende wieder als `Ready` angezeigt wurden, sind diese Läufe aufgrund der ungleichmäßigen und teilweise stark abweichenden Messdauer methodisch nicht sauber genug für die finale Auswertung.

## Archivierte Inhalte

Dieser Ordner enthält unter anderem:

* die ursprünglichen Läufe `run-01-*` bis `run-10-*`
* den ursprünglichen Smoke-Test
* die zugehörige `scenario-run.log`

Die Daten bleiben erhalten, um die Entwicklung der Versuchsdurchführung nachvollziehen zu können. Für die finale Auswertung werden jedoch neue, methodisch bereinigte Läufe durchgeführt.

## Geplante Wiederholung

Die Node-Failure-Experimente werden mit einem verbesserten Skript erneut durchgeführt. Dabei werden insbesondere folgende Punkte angepasst:

* Der Request-Monitor erhält eine zusätzliche Pufferzeit.
* Der Monitor wird nach der geplanten Nachlaufphase aktiv beendet.
* SSH- und `systemctl`-Befehle erhalten Timeouts.
* Recovery-Zeiten werden getrennt dokumentiert:

  * ab Beginn des Fehlers
  * ab Start des Recovery-Befehls
* Der Host-Rechner wird während der Messung am Schlafmodus gehindert.

Die finalen Läufe werden anschließend erneut unter `experiments/kubeedge/node-failure/edge/` abgelegt und für die eigentliche Auswertung verwendet.
