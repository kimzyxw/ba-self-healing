# Methodische Hinweise

## Nachträglich identifizierte Konfigurationsabweichung im asynchronen Request-Monitor

Nach Abschluss der Latenzexperimente (`latency-60s-async-limited`, `latency-10min-async-limited` und `latency-30min-async-limited`) wurde eine Abweichung zwischen der dokumentierten und der tatsächlich verwendeten Konfiguration des asynchronen Request-Monitors festgestellt.

In den erzeugten Testartefakten wurde für alle Läufe ein Wert von

```text
max_in_flight = 10
```

dokumentiert. Dieser Wert sollte die maximale Anzahl gleichzeitig offener HTTP-Anfragen begrenzen.

Bei einer nachträglichen Überprüfung des Testskripts zeigte sich jedoch, dass der konfigurierte Wert nicht an den Request-Monitor übergeben wurde. Stattdessen wurde intern ein fester Wert von

```text
--max-in-flight 2000
```

verwendet. Die effektive Begrenzung gleichzeitig offener Requests war somit deutlich höher als ursprünglich vorgesehen.

Die Request-Erzeugungsrate blieb unverändert bei einer Anfrage pro Sekunde. Aufgrund der hohen Netzwerklatenzen und der langen Timeout-Werte konnten sich jedoch wesentlich mehr gleichzeitig aktive Requests ansammeln als im ursprünglich geplanten Messmodell. Dies kann insbesondere die gemessenen Erfolgsraten, Fehlerraten, Antwortzeiten und Timeout-Effekte beeinflusst haben.

Die zentralen Beobachtungen auf Cluster-Ebene bleiben hiervon jedoch unberührt. Während der Latenzexperimente wurden:

* keine Node-Ausfälle beobachtet,
* keine Pod-Ausfälle festgestellt,
* keine Rescheduling-Vorgänge ausgelöst,
* keine zusätzlichen Kubernetes-Recovery-Maßnahmen beobachtet und
* keine Self-Healing-Mechanismen aktiviert.

Die Aussage, dass erhöhte Netzwerklatenz primär die Anwendungskommunikation beeinträchtigt, jedoch keine Instabilität des Clusters verursacht hat, bleibt daher bestehen.

Der Fehler wurde im Commit

```text
6aca7a0 – Fix max in flight parameter for async latency monitor
```

korrigiert. Alle nachfolgenden Experimente zu Paketverlust und Verbindungsabbrüchen werden mit der korrigierten Implementierung durchgeführt.
