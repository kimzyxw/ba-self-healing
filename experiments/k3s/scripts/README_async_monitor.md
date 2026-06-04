# Asynchroner Request Monitor

Der bisherige Request-Monitor arbeitet synchron: Er sendet einen HTTP-Request, wartet auf Antwort oder Timeout und startet erst danach den nächsten Request. Bei sehr hohen Latenzen blockiert dadurch ein einzelner Request den gesamten Monitor.

Für Latenztests ab 60s wird zusätzlich ein asynchroner Request-Monitor verwendet. Dieser startet in festen Intervallen neue Requests und sammelt Antworten unabhängig voneinander ein. Dadurch kann untersucht werden, ob Requests trotz hoher Latenz verzögert, aber erfolgreich beantwortet werden.

Die asynchrone Messung bildet ein anderes Kommunikationsmodell ab als die synchrone Messung. Sie ist daher separat zu dokumentieren und nicht direkt mit den bisherigen synchronen Läufen gleichzusetzen.
