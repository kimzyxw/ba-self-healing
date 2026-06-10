# Ergebnisse – 100 % Paketverlust mit Safety-Cleanup

## Versuchsaufbau

Zwischen den Control-Plane- und Worker-Knoten wurde mittels `tc netem` auf der Router-VM ein Paketverlust von 100 % simuliert. Dadurch wurde die Kommunikation über den Routerpfad vollständig unterbrochen.

Für jeden Durchlauf waren 3 Minuten Vorlauf, 10 Minuten Störphase und 3 Minuten Nachlauf vorgesehen. Zusätzlich wurde der Request-Monitor mit einem Zeitpuffer gestartet, damit der Nachlauf auch bei Cleanup-Verzögerungen vollständig erfasst werden kann.

Im Vergleich zu den vorherigen Paketverlusttests wurde ein zusätzlicher Safety-Cleanup eingeführt. Die Router-VM setzt die `tc netem`-Regel, wartet lokal die konfigurierte Störphase ab und entfernt die Regel anschließend selbstständig. Zusätzlich versucht `k3s-s1` nach Ablauf der Störphase, die Regel über die NAT-Adresse des Routers erneut zu entfernen. Dadurch soll verhindert werden, dass eine aktive Störung versehentlich länger bestehen bleibt.

## Parameter

| Parameter                   |                                                   Wert |
| --------------------------- | -----------------------------------------------------: |
| Eingebrachter Paketverlust  |                                                  100 % |
| Vorlauf                     |                                                  180 s |
| Störphase                   |                                                  600 s |
| Nachlauf                    |                                                  180 s |
| zusätzlicher Monitor-Puffer |                                                   60 s |
| Wiederholungen              |                                                     10 |
| HTTP Timeout                |                                                  300 s |
| Request-Intervall           |                                                    1 s |
| Max. parallele Requests     |                                                     10 |
| Steuerung der Störung       | Router-VM mit zusätzlichem Safety-Cleanup von `k3s-s1` |

## Validierung

Der Paketverlust wurde in allen zehn Läufen erfolgreich aktiviert. In allen `tc_during.txt`-Dateien wurde eine aktive `netem`-Regel mit `loss 100%` dokumentiert.

Nach Abschluss der Störphase wurde in allen `tc_after.txt`-Dateien wieder die normale Queueing Discipline `fq_codel` dokumentiert. Damit wurde die Störung in allen Läufen erfolgreich entfernt.

Die `s1_safety_cleanup.log`-Dateien enthalten in allen Läufen die Meldung:

```text
Error: Cannot delete qdisc with handle of zero.
```

Diese Meldung ist in diesem Fall unkritisch. Sie zeigt, dass die `netem`-Regel bereits durch den Router-Job entfernt wurde und der zusätzliche Cleanup von `k3s-s1` keine aktive Regel mehr vorfand.

## Zeitliche Auffälligkeiten

Obwohl der Router-Job und der zusätzliche Safety-Cleanup eingesetzt wurden, traten in einzelnen Läufen weiterhin zeitliche Abweichungen auf. Die geplante Störphase von 600 Sekunden wurde in mehreren Läufen deutlich überschritten.

| Run           | Bewertung der Fault-Dauer |
| ------------- | ------------------------- |
| run-01-router | verlängert                |
| run-02-router | korrekt                   |
| run-03-router | korrekt                   |
| run-04-router | korrekt                   |
| run-05-router | korrekt                   |
| run-06-router | verlängert                |
| run-07-router | korrekt                   |
| run-08-router | korrekt                   |
| run-09-router | verlängert                |
| run-10-router | korrekt                   |

Für die quantitative Auswertung werden daher primär die methodisch sauberen Läufe `run-02`, `run-03`, `run-04`, `run-05`, `run-07`, `run-08` und `run-10` betrachtet.

Die verlängerten Fault-Phasen werden nicht als Self-Healing-Verhalten interpretiert, sondern als methodische Auffälligkeit der lokalen Testumgebung. Da sowohl Router-Job als auch Safety-Cleanup später als geplant ausgeführt wurden, liegt die Ursache vermutlich in Verzögerungen der VM- oder Host-Ausführung und nicht in der Kubernetes-Reaktion selbst.

## Zusammenfassung pro Run

| Run           | Requests gesamt | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | Fault p99 [ms] | Timeouts | Recovery [s] | Bewertung               |
| ------------- | --------------: | ------------------: | ----------------: | --------------: | ----------------: | -------------: | -------------: | -------: | -----------: | ----------------------- |
| run-01-router |             641 |               28.24 |              0.43 |           99.57 |           1468.29 |        3102.38 |       70249.88 |        1 |           NA | verlängerte Fault-Phase |
| run-02-router |             956 |               43.93 |              0.74 |           99.26 |           1373.46 |        3105.79 |       70151.84 |        1 |         0.26 | auswertbar              |
| run-03-router |             958 |               43.95 |              0.56 |           99.44 |           1388.66 |        3103.65 |       70059.79 |        1 |         0.12 | auswertbar              |
| run-04-router |             973 |               43.27 |              0.72 |           99.28 |           1493.24 |        3104.18 |       69534.80 |        1 |         0.49 | auswertbar              |
| run-05-router |             957 |               44.10 |              0.93 |           99.07 |           1261.98 |        3100.37 |       70099.12 |        1 |         0.31 | auswertbar              |
| run-06-router |             682 |               26.54 |              0.40 |           99.60 |           1427.43 |        3100.03 |       69385.05 |        1 |           NA | verlängerte Fault-Phase |
| run-07-router |             956 |               44.14 |              0.93 |           99.07 |           1294.59 |        3101.21 |       70103.02 |        1 |         0.94 | auswertbar              |
| run-08-router |             973 |               43.27 |              0.72 |           99.28 |           1591.40 |        3103.25 |       69591.25 |        1 |         0.30 | auswertbar              |
| run-09-router |             427 |               42.39 |              0.40 |           99.60 |           1571.11 |       68341.93 |      923099.29 |        1 |           NA | verlängerte Fault-Phase |
| run-10-router |             989 |               42.47 |              0.52 |           99.48 |           1390.21 |        3099.90 |       37702.18 |        1 |         0.76 | auswertbar              |

## Aggregierte Beobachtung der auswertbaren Läufe

Die folgenden Werte beziehen sich auf die methodisch saubersten Läufe `run-02`, `run-03`, `run-04`, `run-05`, `run-07`, `run-08` und `run-10`.

* Auswertbare Läufe: 7/10
* Baseline Success Rate: 100 % in allen auswertbaren Läufen
* Fault Success Rate: ca. 0.52 % bis 0.93 %
* Fault Error Rate: ca. 99.07 % bis 99.48 %
* Fault Median: ca. 1262 ms bis 1591 ms
* Fault p95: ca. 3100 ms bis 3106 ms
* Fault p99: ca. 37.7 s bis 70.2 s
* Timeouts: 1 pro Lauf
* After Success Rate: 100 % in allen auswertbaren Läufen
* Recovery Time: ca. 0.12 s bis 0.94 s

## Kubernetes- und Self-Healing-Beobachtungen

Bei 100 % Paketverlust wurden in allen Läufen `NodeNotReady`-Events beobachtet. Betroffen waren sowohl `k3s-w1` als auch `k3s-w2`. Dies zeigt, dass die Control Plane die Worker-Knoten während der vollständigen Netzwerkunterbrechung nicht zuverlässig erreichen konnte.

Gleichzeitig wurden keine Hinweise auf `Killing`-, `BackOff`- oder `Failed`-Events gefunden. Es wurden somit keine klassischen Self-Healing-Maßnahmen auf Pod-Ebene beobachtet, insbesondere keine Pod-Neustarts und kein sichtbares Rescheduling der Testanwendung.

Die Clusterüberwachung erkennt also die gestörte Worker-Kommunikation, leitet in diesem Szenario jedoch keine unmittelbare Wiederherstellung der Anwendung durch Pod-Neustarts oder Pod-Verschiebungen ein.

## Anwendungsverhalten

Während der Baseline-Phasen war die Anwendung vollständig erreichbar. In den Fault-Phasen brach die Erreichbarkeit nahezu vollständig zusammen. Die Erfolgsrate lag in den auswertbaren Läufen nur noch bei ungefähr 0.5 % bis 0.9 %.

Nach Entfernen der Paketverlustregel erholte sich die Anwendung sehr schnell. In den Nachlaufphasen wurde wieder eine Erfolgsrate von 100 % erreicht. Die gemessene Recovery Time lag in den auswertbaren Läufen unter einer Sekunde.

Damit unterscheidet sich 100 % Paketverlust deutlich von den niedrigeren Paketverluststufen: Während 50 % und 70 % noch eine eingeschränkte, aber teilweise vorhandene Anwendungserreichbarkeit zeigten, führte 100 % Paketverlust praktisch zu einer temporären Nichtverfügbarkeit der Anwendung über den gestörten Pfad.

## Interpretation

Ein Paketverlust von 100 % entspricht einer vollständigen Netzwerkpartition zwischen Control Plane und Worker-Netz. Die Anwendung ist während der Störphase über den gemessenen Pfad praktisch nicht erreichbar.

K3s erkennt die Kommunikationsstörung und markiert die betroffenen Worker-Knoten als `NodeNotReady`. Trotzdem wurden keine Pod-Neustarts, keine BackOff-Zustände und kein Rescheduling beobachtet. Die Wiederherstellung der Anwendung erfolgte erst nach Entfernen der Netzwerkstörung.

Damit zeigt das Experiment, dass K3s unter vollständiger Unterbrechung der Verbindung keine Anwendungserreichbarkeit aufrechterhalten kann, wenn die Requests über den unterbrochenen Pfad laufen. Die Self-Healing-Mechanismen erkennen zwar den Node-Zustand, führen aber in diesem lokalen Setup nicht zu einer automatischen Wiederherstellung der Anwendung während der aktiven Partition.

## Methodische Einschränkung

Mehrere Läufe zeigten verlängerte Fault-Dauern. Diese Abweichungen werden als Einschränkung der lokalen Versuchsumgebung dokumentiert. Für die quantitative Auswertung werden deshalb nur die zeitlich korrekten Läufe herangezogen.

Der zusätzliche Safety-Cleanup konnte dokumentieren, dass die `tc`-Regel nach der Störphase entfernt wurde. Die Meldung `Cannot delete qdisc with handle of zero` ist dabei als Hinweis zu verstehen, dass der Router-Job bereits erfolgreich aufgeräumt hatte.

## Fazit

100 % Paketverlust stellt die stärkste getestete Netzwerkstörung dar und führt während der Fault-Phase zu einer nahezu vollständigen Nichtverfügbarkeit der Anwendung. Nach Beendigung der Störung erholt sich die Anwendung jedoch sehr schnell.

Auf Kubernetes-Ebene werden die Worker-Knoten zuverlässig als `NodeNotReady` erkannt. Pod-bezogene Self-Healing-Maßnahmen wie Neustarts oder Rescheduling wurden jedoch nicht beobachtet. Damit liefert der Test einen klaren Hinweis darauf, dass die automatische Wiederherstellung in K3s bei vollständiger Netzwerkpartition stark von der Wiederherstellung der Netzwerkverbindung selbst abhängt.
