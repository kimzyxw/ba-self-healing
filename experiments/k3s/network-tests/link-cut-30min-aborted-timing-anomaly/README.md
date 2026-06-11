
Der 30min-Verbindungsabbruch wurde begonnen, jedoch nicht als reguläres Szenario ausgewertet, da die geplante Fault-Dauer aufgrund deutlicher Timing-Anomalien nicht eingehalten wurde. Bereits run-01 dauerte statt 30 Minuten ca. 66 Minuten; in run-02 verzögerte sich bereits der Vorlauf deutlich.
# Abgebrochener Test – 30min Verbindungsabbruch

## Ziel des geplanten Experiments

Für dieses Szenario sollte ein 30-minütiger vollständiger Verbindungsabbruch zwischen Server-Netz und Worker-Netz simuliert werden. Der Test sollte analog zu den vorherigen Link-Cut-Experimenten durchgeführt werden:

* 180 s Vorlauf
* 1800 s Verbindungsabbruch
* 180 s Nachlauf
* 10 Wiederholungen
* HTTP-Monitoring über die Testanwendung

Die Störung sollte erneut über das Router-Interface `ens256` erzeugt werden. Dieses Interface verbindet im Testaufbau das Server-Netz mit der Router-VM und wird für Link-Cut-Experimente per `ip link set dev ens256 down` deaktiviert und anschließend wieder aktiviert.

## Abbruchgrund

Der 30min-Test wurde begonnen, aber nicht als reguläres Experiment ausgewertet. Bereits im ersten Lauf traten deutliche Timing-Anomalien auf. Die geplante Fault-Dauer betrug 1800 s, also 30 Minuten. Tatsächlich wurde für `run-01-router` jedoch folgende Zeit dokumentiert:

| Zeitpunkt     | Wert                      |
| ------------- | ------------------------- |
| Fault Start   | 2026-06-11T12:54:31+00:00 |
| Recovery Time | 2026-06-11T14:01:12+00:00 |

Damit dauerte die Fault-Phase nicht 30 Minuten, sondern ungefähr 66 Minuten. Zusätzlich war der Request-Monitor beim Testende bereits beendet, sodass keine reguläre Nachlaufphase mehr aufgezeichnet wurde:

```text
after requests_total=0
recovery_latency_s=NA
```

Auch im zweiten Lauf zeigte sich erneut eine deutliche zeitliche Verzögerung. Der Request-Monitor wurde um `2026-06-11T14:59:18+00:00` gestartet, der eigentliche Fault jedoch erst um `2026-06-11T15:22:11+00:00` injiziert. Damit wurde bereits der geplante Vorlauf von 180 s deutlich überschritten.

Aufgrund dieser Timing-Abweichungen wurde das Szenario abgebrochen.

## Beobachtungen aus dem unvollständigen Lauf

Obwohl `run-01-router` nicht als regulärer 30min-Lauf gewertet wird, zeigt er qualitativ das erwartbare Verhalten eines längeren vollständigen Link-Ausfalls:

| Phase    | Success Rate | Error Rate |
| -------- | -----------: | ---------: |
| Baseline |     100.00 % |     0.00 % |
| Fault    |       0.13 % |    99.87 % |
| After    |           NA |         NA |

Während der Fault-Phase war die Anwendung praktisch nicht erreichbar. Die Fault Success Rate lag nur bei 0.13 %, während die Error Rate 99.87 % betrug. Dieses Verhalten entspricht qualitativ den Ergebnissen des 10min-Link-Cut-Szenarios, ist aufgrund der falschen Fault-Dauer und fehlenden Nachlaufphase jedoch nicht quantitativ vergleichbar.

## Systemzustand nach Abbruch

Nach dem Abbruch wurde der Router manuell in einen sicheren Zustand zurückversetzt:

```bash
sudo ip link set dev ens256 up
sudo ip link set dev ens161 up
sudo sysctl -w net.ipv4.ip_forward=1
```

Anschließend wurde geprüft, dass:

* `ens256` wieder `UP` war
* `ens161` wieder `UP` war
* `net.ipv4.ip_forward = 1` gesetzt war
* alle K3s-Nodes wieder `Ready` waren
* alle Testanwendungs-Pods `Running` waren
* beide Worker-Knoten über das interne Testnetz erreichbar waren

Damit wurde der Cluster nach dem Abbruch wieder in einen stabilen Zustand gebracht.

## Methodische Einordnung

Der 30min-Link-Cut wurde nicht als reguläres Messergebnis aufgenommen, da die geplante Versuchsdauer in der lokalen VM-Umgebung nicht zuverlässig eingehalten wurde. Die deutliche Verlängerung der Fault-Phase und die fehlende Nachlaufphase würden die Vergleichbarkeit mit den anderen Link-Cut-Szenarien verfälschen.

Die Ergebnisse der vorherigen Szenarien reichen dennoch aus, um das Verhalten bei vollständigen Verbindungsabbrüchen einzuordnen:

* 1s-Link-Cut: kaum sichtbare Auswirkungen auf Anwendungsebene
* 1min-Link-Cut: deutliche Verzögerungen und blockierende Requests
* 10min-Link-Cut: nahezu vollständige Nichtverfügbarkeit während der Fault-Phase

Der abgebrochene 30min-Test bestätigt qualitativ, dass ein längerer vollständiger Link-Ausfall ebenfalls zu einer nahezu vollständigen Nichtverfügbarkeit der Anwendung führt. Er wird jedoch nicht quantitativ ausgewertet.

## Fazit

Das 30min-Szenario wurde aufgrund massiver Timing-Anomalien abgebrochen und archiviert. Die Daten werden nicht als regulärer Messlauf verwendet. Stattdessen wird der Abbruch als methodische Einschränkung dokumentiert: In der lokalen virtualisierten Testumgebung konnten sehr lange Link-Cut-Experimente nicht mehr zuverlässig mit der geplanten Fault-Dauer durchgeführt werden.

Für die weitere Auswertung werden daher die regulär abgeschlossenen Szenarien 1s, 1min und 10min verwendet.
