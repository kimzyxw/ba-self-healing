# Erkenntnisse aus den asynchronen Latenztests

## Ziel

Zur Untersuchung hoher Netzwerklatenzen wurde zusätzlich ein asynchroner Request-Monitor implementiert. Im Gegensatz zum ursprünglichen synchronen Monitor sendet dieser kontinuierlich neue HTTP-Anfragen, ohne auf den Abschluss vorheriger Anfragen zu warten. Dadurch können mehrere Anfragen gleichzeitig aktiv sein.

Die Tests wurden über einen dedizierten Router durchgeführt, auf dem mittels `tc netem` künstliche Netzwerklatenz erzeugt wurde.

---

## Verifikation der Störung

Die Router-basierte Störung wurde erfolgreich validiert.

Für jeden Testlauf wurden folgende Prüfungen durchgeführt:

* Aktivierung von IP-Forwarding auf dem Router
* Anpassung der Routingtabellen auf den beteiligten Knoten
* Traceroute-Prüfung vor Testbeginn
* Kontrolle der aktiven `tc netem`-Konfiguration während der Störung

Die Traceroute-Ausgaben bestätigten, dass der gesamte Datenverkehr über den Router geleitet wurde. Zusätzlich wurde während der Störung die erwartete `netem delay`-Konfiguration auf dem Router nachgewiesen.

Die Felder

```text
router_path_valid=yes
latency_applied=yes
```

wurden in allen betrachteten Testläufen erfolgreich gesetzt.

---

## Beobachtetes Verhalten

Bei einer konfigurierten Verzögerung von 60 Sekunden pro Paket wurden deutlich längere Antwortzeiten beobachtet als die nominell eingestellte Netzwerklatenz.

Beispielsweise traten erfolgreiche Requests mit Laufzeiten von deutlich über 60 Sekunden auf:

```text
60002 ms
68000 ms
83000 ms
122000 ms
183000 ms
```

Ebenso wurden zahlreiche Requests erst nach Ablauf des konfigurierten Client-Timeouts beendet.

Bei Verwendung eines Timeouts von 300 Sekunden lagen viele Messwerte nahe diesem Grenzwert:

```text
300000 ms
```

---

## Ursache

Der asynchrone Monitor startet unabhängig von bereits laufenden Requests jede Sekunde eine weitere Anfrage.

Während einer langen Störungsphase entstehen dadurch gleichzeitig viele aktive Verbindungen.

Vereinfacht ergibt sich folgendes Verhalten:

1. Neue Requests werden kontinuierlich gestartet.
2. Bereits laufende Requests bleiben aufgrund der künstlichen Netzwerklatenz lange aktiv.
3. Die Anzahl gleichzeitig offener Requests wächst während der Störung stetig an.
4. Nach Entfernen der Störung existieren weiterhin zahlreiche noch laufende Requests.
5. Diese Requests müssen zunächst erfolgreich abgeschlossen oder durch das Timeout beendet werden.

Dadurch entstehen Messwerte, die nicht ausschließlich die konfigurierte Netzwerklatenz widerspiegeln, sondern zusätzlich durch den aufgebauten Request-Stau beeinflusst werden.

---

## Auswirkungen auf die Messdaten

Bei kurzen Smoke-Tests (60 s Verzögerung, 180 s Fault-Dauer) zeigte sich bereits eine erhöhte Anzahl gleichzeitig laufender Requests.

Bei längeren Testläufen (60 s Verzögerung, 600 s Fault-Dauer) verstärkte sich dieser Effekt deutlich.

Folgende Phänomene wurden beobachtet:

* stark ansteigende Anzahl gleichzeitig aktiver Requests
* hohe Anzahl von Timeout-Fehlern
* sehr große Spannweite der gemessenen Antwortzeiten
* Antwortzeiten deutlich oberhalb der eingestellten Netzwerklatenz
* teilweise noch lange nach Ende der Störung laufende Requests

Die Messwerte beschreiben daher nicht ausschließlich den Einfluss der Netzwerklatenz, sondern zusätzlich das Verhalten des Systems unter einem wachsenden Request-Backlog.

---

## Beobachtungen zur Wiederherstellung

Nach Entfernen der Störung wurden keine dauerhaften Schäden am Cluster festgestellt.

In den meisten Testläufen erreichten neue Requests innerhalb weniger Sekunden wieder normale Antwortzeiten.

Die Wiederherstellungszeit (`recovery_latency_s`) lag typischerweise im Bereich von etwa einer bis zwei Sekunden, sofern ausreichend Nachlaufzeit zur Verfügung stand und keine große Anzahl noch laufender Requests die Auswertung beeinflusste.

---

## Fazit der Analyse

Die Router-basierte Erzeugung künstlicher Netzwerklatenz funktioniert wie vorgesehen und beeinflusst den Datenverkehr nachweislich.

Der asynchrone Monitor ermöglicht die Beobachtung paralleler Requests unter hohen Latenzen, erzeugt jedoch bei langen Verzögerungen und langen Fault-Phasen zusätzliche Queue- und Backlog-Effekte. Die resultierenden Antwortzeiten werden daher sowohl durch die konfigurierte Netzwerklatenz als auch durch die Anzahl gleichzeitig offener Requests beeinflusst.

Diese Beobachtung muss bei der Interpretation der Messergebnisse berücksichtigt werden.
