# Vorversuche zu KubeEdge Cloud-Node-Ausfällen

Dieses Verzeichnis enthält Vor- und Zwischentests zu Cloud-Node-Ausfällen in der KubeEdge-Testumgebung.

Die Läufe `run-01-c2` und `run-02-c3` wurden zunächst mit einem automatischen Recovery-Timeout von 600 Sekunden durchgeführt. In beiden Fällen wurde der betroffene Cloud-Knoten innerhalb dieses Zeitfensters nicht wieder als Ready erkannt. Da kein bestätigter manueller Eingriff auf dem jeweils betroffenen Cloud-Knoten durchgeführt wurde, werden diese Läufe nicht als finale, vergleichbare Messläufe verwendet.

Anschließend wurde mit `pretest-1800s-c2` ein Zwischentest mit einem erhöhten Recovery-Timeout von 1800 Sekunden durchgeführt. In diesem Lauf wurde c2 ohne bestätigten manuellen Eingriff wieder als Ready erkannt. Die Recovery dauerte jedoch deutlich länger als 600 Sekunden.

Daraus folgt für die finale Cloud-Node-Failure-Serie:
- Recovery-Timeout: 1800 Sekunden
- kein manueller Eingriff vor Ablauf dieses Timeouts
- nur Läufe mit identischer Methodik werden in die finale Auswertung aufgenommen
