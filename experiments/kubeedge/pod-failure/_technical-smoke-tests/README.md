# Technische Smoke-Tests

Dieser Ordner enthält technische Vorversuche zur Validierung des finalen
KubeEdge-Pod-Ausfallskripts. Die hier enthaltenen Läufe sind keine Bestandteile
der quantitativen Endauswertung.

## smoke-test-sync

Validierung der Pod-Löschung, Recovery-Erkennung und Artefakterzeugung mit
den finalen Parametern:

- synchroner Request-Monitor
- Intervall: 1 s
- Request-Timeout: 2 s
- Baseline: 60 s
- Nachlauf: 60 s

Der Pod-Ausfall und die Recovery-Erkennung funktionierten. Der Monitor wurde
jedoch noch mit SIGINT beendet und lief nach dem offiziellen Testende weiter.
Die Requests außerhalb des offiziellen Testfensters werden daher nicht
ausgewertet. Dieser Lauf dient ausschließlich als technischer Vorversuch.

## smoke-test-sync-term

Validierung der korrigierten Monitor-Beendigung mittels SIGTERM.

Parameter:

- synchroner Request-Monitor
- Intervall: 1 s
- Request-Timeout: 2 s
- Baseline: 10 s
- Nachlauf: 10 s

Der Test bestätigte:

- erfolgreiche Pod-Löschung,
- Recovery auf drei Ready-Replikate,
- korrekte Begrenzung der requests.csv auf den Testzeitraum,
- keine verbleibenden Monitor- oder Testprozesse.

Dieser Lauf ist ebenfalls ein technischer Vorversuch und nicht Teil der
zehn finalen Wiederholungen.
