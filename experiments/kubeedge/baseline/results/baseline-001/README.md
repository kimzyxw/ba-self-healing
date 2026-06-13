# KubeEdge Baseline 001

Dieser Lauf validiert den stabilen Servicezugriff auf die NGINX-Testanwendung im KubeEdge-Setup nach der Installation von EdgeMesh.

## Ziel

Ziel des Baseline-Laufs war es zu prüfen, ob der Request-Monitor zuverlässig gegen den KubeEdge-Service-Endpunkt messen kann, bevor die eigentlichen Fehlerszenarien gestartet werden.

## Setup

Die NGINX-Testanwendung läuft im Namespace `testapp` mit drei Replikaten auf den Edge-Knoten `e1` und `e2`.

Der Servicezugriff erfolgt über EdgeMesh auf dem NodePort 30080.

Verwendeter Messendpunkt:

`http://10.10.20.131:30080`

## Messparameter

- Dauer: 180 Sekunden
- Intervall: 1 Sekunde
- Timeout: 2 Sekunden
- Maximal gleichzeitige Requests: 10
- Request-Monitor: `experiments/kubeedge/scripts/request_monitor_async.py`

## Ergebnis

Der Lauf erzeugte 180 Requests. Alle Requests wurden erfolgreich mit `HTTP 200 OK` beantwortet.

Die Erfolgsrate beträgt 100,00 %. Die mediane Antwortzeit lag bei 1,31 ms, der p95-Wert bei 2,74 ms. Es traten keine Fehler auf.

Der Baseline-Lauf bestätigt damit, dass der Servicezugriff über EdgeMesh stabil funktioniert und für die weiteren KubeEdge-Experimente verwendet werden kann.
