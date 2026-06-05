# Anpassung des asynchronen Request-Monitors

## Ausgangspunkt

Für die Untersuchung hoher Netzwerklatenzen wurde zusätzlich zum synchronen Request-Monitor ein asynchroner Monitor implementiert. Dieser startet Requests unabhängig voneinander, sodass neue Anfragen nicht erst nach Abschluss vorheriger Anfragen gesendet werden.

In ersten Testläufen zeigte sich jedoch, dass bei langen Fault-Phasen und hohen Timeouts sehr viele Requests gleichzeitig offen bleiben können. Dadurch entsteht ein Request-Backlog, der die Messergebnisse zusätzlich beeinflusst. Die gemessenen Antwortzeiten beschreiben dann nicht mehr nur die eingebrachte Netzwerklatenz, sondern auch Queueing- und Timeout-Effekte auf Client-Seite.

## Änderung

Der asynchrone Monitor wurde daher so angepasst, dass die Anzahl gleichzeitig aktiver Requests begrenzt wird. Dazu wurde der Parameter `--max-in-flight` eingeführt bzw. wirksam umgesetzt.

Der Monitor startet weiterhin neue Requests in festen Intervallen, erzeugt jedoch nur dann einen neuen Request, wenn weniger als die konfigurierte Anzahl an Requests gleichzeitig aktiv ist. Ist die maximale Anzahl aktiver Requests erreicht, wartet der Monitor zunächst, bis mindestens ein laufender Request abgeschlossen wurde.

Damit ergibt sich folgendes Verhalten:

```text
max-in-flight = 10

maximal 10 Requests gleichzeitig offen
neuer Request erst, wenn ein vorheriger Request beendet wurde
keine unbegrenzte Anhäufung offener Requests

Bedeutung für die Messung
Die Anpassung bildet ein kontrolliertes asynchrones Kommunikationsmodell ab. Im Unterschied zum synchronen Monitor blockiert nicht ein einzelner Request die gesamte Messung. Gleichzeitig wird verhindert, dass bei hohen Latenzen ein unkontrolliert wachsender Request-Stau entsteht.
Damit kann untersucht werden, ob die Anwendung unter hoher Netzwerklatenz weiterhin erreichbar bleibt, wenn mehrere Requests parallel verarbeitet werden dürfen, ohne das System beliebig stark zu überlasten.

Einordnung
Der asynchrone Monitor ist kein vollständiges DTN- oder Message-Queue-System. Er nähert jedoch ein asynchrones Kommunikationsverhalten an, indem Anfragen unabhängig voneinander gestartet und Antworten unabhängig voneinander ausgewertet werden.
Die Parameter --timeout, --interval und --max-in-flight beeinflussen die Messergebnisse wesentlich und werden daher pro Testlauf dokumentiert. Für die weitere Evaluation wird eine begrenzte Parallelität verwendet, da der Schwerpunkt der Arbeit auf dem Self-Healing-Verhalten des Kubernetes-Systems liegt und nicht auf der Optimierung eines Lastgenerators oder Kommunikationsprotokolls.
Die gewählte Konfiguration stellt somit einen pragmatischen Kompromiss dar: Sie vermeidet die starke Blockierung des synchronen Request-Monitors, begrenzt aber gleichzeitig künstliche Backlog-Effekte durch zu viele parallele Requests.
