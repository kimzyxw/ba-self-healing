# KubeEdge Pod-Ausfälle

## Ziel des Experiments

In diesem Experiment wurde das Self-Healing-Verhalten der KubeEdge-Testumgebung bei Pod-Ausfällen untersucht. Ziel war es zu prüfen, ob ein manuell gelöschter Pod der dreifach replizierten NGINX-Testanwendung automatisch ersetzt wird und ob währenddessen die Anwendung über den eingerichteten Service-Endpunkt erreichbar bleibt.

Das Szenario entspricht methodisch dem Pod-Ausfall-Szenario der K3s-Experimente. Ein einzelner laufender Pod der Testanwendung wurde gelöscht, während ein Request-Monitor kontinuierlich HTTP-Anfragen gegen die Anwendung sendete.

## Versuchsaufbau

Die KubeEdge-Umgebung besteht aus drei Cloud-Knoten und zwei Edge-Knoten. Die NGINX-Testanwendung läuft im Namespace `testapp` als Deployment `nginx-testapp` mit drei Replikaten.

Da der NodePort-Service im initialen KubeEdge-Setup auf den Edge-Knoten nicht direkt erreichbar war, wurde EdgeMesh eingesetzt. Der Request-Monitor sendete die HTTP-Anfragen gegen folgenden Service-Endpunkt:

```text
http://10.10.20.131:30080
```

EdgeMesh dient in diesem Aufbau nur dazu, den Servicezugriff auf den Edge-Knoten bereitzustellen. Die eigentliche Self-Healing-Beobachtung bezieht sich weiterhin auf das Verhalten der Kubernetes/KubeEdge-Komponenten beim Verlust eines Pods.

## Skripte und Parameter

Für die Durchführung wurde das Skript

```text
experiments/kubeedge/scripts/run_pod_failure_test_async.sh
```

verwendet. Für die Wiederholung des Szenarios wurde zusätzlich ein Wrapper-Skript genutzt:

```text
experiments/kubeedge/scripts/run_pod_failure_scenario_async.sh
```

Pro Lauf wurden folgende Schritte durchgeführt:

1. Start des asynchronen Request-Monitors.
2. Dokumentation des Ausgangszustands von Nodes, Pods, KubeEdge-Pods und Events.
3. Vorlaufphase ohne Störung.
4. Löschen eines laufenden `nginx-testapp`-Pods.
5. Dokumentation des Fault-Zeitpunkts.
6. Warten auf Recovery zu drei ready, nicht-terminierenden Pods.
7. Dokumentation des Recovery-Zeitpunkts.
8. Fortsetzung des Request-Monitorings bis zum Ende der Messdauer.
9. Dokumentation des Endzustands von Nodes, Pods, KubeEdge-Pods und Events.

Die verwendeten Parameter waren:

| Parameter                   |                        Wert |
| --------------------------- | --------------------------: |
| Namespace                   |                   `testapp` |
| Deployment/App-Label        |             `nginx-testapp` |
| Service-Endpunkt            | `http://10.10.20.131:30080` |
| Vorlauf                     |                        60 s |
| Nachlauf                    |                       120 s |
| Gesamtdauer Request-Monitor |                       180 s |
| Request-Intervall           |                         1 s |
| HTTP-Timeout                |                         2 s |
| Max. parallele Requests     |                          10 |
| Reguläre Wiederholungen     |                          10 |

## Reproduzierbare Auswertung

Die Detail- und Aggregatwerte wurden mit folgendem Skript erzeugt:

```text
experiments/kubeedge/scripts/aggregate_kubeedge_pod_failure.py

## Smoke-Tests

Vor den regulären Läufen wurden zwei Smoke-Tests durchgeführt. Der erste Smoke-Test zeigte, dass die grundsätzliche Durchführung funktionierte. Dabei wurde jedoch sichtbar, dass terminierende Pods bei der Recovery-Erkennung noch mitzählen konnten.

Daraufhin wurde die Recovery-Erkennung angepasst. Seitdem werden nur Pods gezählt, die keinen `deletionTimestamp` besitzen und deren Container als ready gemeldet ist. Der zweite Smoke-Test bestätigte diese Anpassung.

## Durchführung der regulären Läufe

Zunächst wurden zehn Läufe `run-01` bis `run-10` durchgeführt. Dabei zeigte `run-06` eine Timing-Anomalie: Der Lauf wurde formal abgeschlossen, enthielt aber nur 62 statt der erwarteten 180 Requests. Der Fault wurde in diesem Lauf verspätet innerhalb der Messphase ausgelöst. Da dadurch keine vollständige und methodisch vergleichbare Messung vorliegt, wurde `run-06` nicht in die reguläre quantitative Auswertung aufgenommen.

Als Ersatz wurde ein zusätzlicher Lauf `run-11` durchgeführt. Dieser Lauf war vollständig und methodisch konsistent mit den übrigen vollständigen Läufen.

Die reguläre quantitative Auswertung basiert daher auf folgenden zehn Läufen:

```text
run-01
run-02
run-03
run-04
run-05
run-07
run-08
run-09
run-10
run-11
```

`run-06` bleibt als dokumentierte Timing-Anomalie im Ergebnisverzeichnis erhalten, wird aber nicht als regulärer Lauf bewertet.

## Ergebnisse pro Lauf

| Run    | Requests | Success [%] | Fehler | Median [ms] | p95 [ms] | Max [ms] | Recovery [s] | 3 Pods nach Lauf |
| ------ | -------: | ----------: | -----: | ----------: | -------: | -------: | -----------: | ---------------- |
| run-01 |      180 |      100.00 |      0 |        2.81 |     6.07 |    23.80 |          3.0 | ja               |
| run-02 |      180 |      100.00 |      0 |        2.21 |     5.55 |    58.16 |          2.0 | ja               |
| run-03 |      180 |      100.00 |      0 |        2.10 |     4.27 |    53.76 |          6.0 | ja               |
| run-04 |      180 |      100.00 |      0 |        2.25 |     5.37 |    59.57 |          1.0 | ja               |
| run-05 |      180 |      100.00 |      0 |        2.56 |     6.50 |    54.94 |          5.0 | ja               |
| run-07 |      180 |      100.00 |      0 |        2.52 |     5.86 |    62.26 |          6.0 | ja               |
| run-08 |      180 |      100.00 |      0 |        2.72 |     4.67 |    44.16 |          1.0 | ja               |
| run-09 |      180 |      100.00 |      0 |        2.46 |     4.37 |    40.48 |          4.0 | ja               |
| run-10 |      180 |      100.00 |      0 |        2.33 |     5.44 |    36.19 |          4.0 | ja               |
| run-11 |      180 |      100.00 |      0 |        2.75 |     7.03 |    92.92 |          2.0 | ja               |

## Aggregierte Ergebnisse

Über die zehn regulär ausgewerteten Läufe ergaben sich folgende Werte:

| Metrik                   |     Wert |
| ------------------------ | -------: |
| Ausgewertete Läufe       |       10 |
| Requests gesamt          |     1800 |
| Erfolgreiche Requests    |     1800 |
| Fehlgeschlagene Requests |        0 |
| Success Rate             | 100.00 % |
| Error Rate               |   0.00 % |
| Median Antwortzeit       |  2.47 ms |
| p95 Antwortzeit          |  5.99 ms |
| Minimale Antwortzeit     |  0.78 ms |
| Maximale Antwortzeit     | 92.92 ms |
| Recovery min             |    1.0 s |
| Recovery median          |    3.5 s |
| Recovery mean            |    3.4 s |
| Recovery max             |    6.0 s |

## Beobachtungen

In allen regulär ausgewerteten Läufen wurde der gelöschte Pod automatisch ersetzt. Nach Abschluss jedes Laufs befanden sich wieder drei Pods der Testanwendung im Zustand `1/1 Running`.

Während der Pod-Ausfälle traten keine fehlgeschlagenen HTTP-Requests auf. Alle 1800 Requests der regulären Läufe wurden erfolgreich beantwortet. Die Antwortzeiten blieben überwiegend niedrig. Einzelne Maximalwerte lagen höher, beeinflussten aber weder die Erfolgsrate noch den finalen Zustand der Anwendung.

Die gemessene Recovery-Zeit bezeichnet die Zeit zwischen dem dokumentierten Löschen des Pods und dem Zeitpunkt, an dem wieder drei ready, nicht-terminierende Pods erkannt wurden. Diese Zeit lag in den regulären Läufen zwischen 1 und 6 Sekunden.

## Interpretation

Das Experiment zeigt, dass die KubeEdge-Testumgebung Pod-Ausfälle der NGINX-Testanwendung zuverlässig kompensiert. Der ReplicaSet-/Deployment-Mechanismus stellte nach dem manuellen Löschen eines Pods automatisch wieder die gewünschte Anzahl von drei Replikaten her.

Aus Anwendungssicht blieb der Servicezugriff über EdgeMesh während der regulären Läufe stabil. Es wurden keine Request-Fehler beobachtet. Damit konnte für dieses Szenario keine sichtbare Serviceunterbrechung auf HTTP-Ebene festgestellt werden.

Die Ergebnisse sprechen dafür, dass einfache Pod-Ausfälle in diesem Aufbau zuverlässig durch die nativen Kubernetes/KubeEdge-Mechanismen behandelt werden. EdgeMesh stellte dabei den Servicezugriff auf den Edge-Knoten bereit, während die eigentliche Wiederherstellung der Replikatanzahl durch die Kubernetes-Mechanismen erfolgte.

## Methodische Einschränkungen

`run-06` zeigte eine Timing-Anomalie und wurde deshalb nicht in die reguläre quantitative Auswertung aufgenommen. Der Lauf enthielt nur 62 statt 180 Requests. Da die Messdauer dadurch nicht mit den übrigen Läufen vergleichbar war, wurde ein zusätzlicher Ersatzlauf `run-11` durchgeführt.

Die Recovery-Zeit basiert auf der skriptseitigen Erkennung von drei ready, nicht-terminierenden Pods. Sie beschreibt damit die beobachtete Wiederherstellung der gewünschten Pod-Anzahl im Clusterzustand, nicht zwingend den exakten internen Zeitpunkt der Kubernetes-Entscheidung.

Da der Servicezugriff in KubeEdge über EdgeMesh realisiert wurde, ist die Anwendungserreichbarkeit in diesem Szenario nicht ausschließlich vom Deployment-Recovery-Verhalten abhängig. Für die Interpretation ist daher zu unterscheiden zwischen der Servicebereitstellung über EdgeMesh und der Wiederherstellung der gewünschten Replikatanzahl durch Kubernetes/KubeEdge.

## Fazit

Die KubeEdge-Testumgebung stellte nach manuellen Pod-Ausfällen zuverlässig wieder drei laufende Replikate der NGINX-Testanwendung her. In den zehn regulär ausgewerteten Läufen traten keine fehlgeschlagenen HTTP-Requests auf. Die Success Rate lag bei 100.00 %, und die Recovery-Zeit lag zwischen 1 und 6 Sekunden.

Damit zeigte KubeEdge im Pod-Ausfall-Szenario ein stabiles Self-Healing-Verhalten auf Pod-Ebene. Die Anwendung blieb über den EdgeMesh-Service-Endpunkt während der regulären Messläufe erreichbar.
