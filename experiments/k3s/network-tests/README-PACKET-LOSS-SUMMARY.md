# Zusammenfassung – Paketverlusttests in K3s

## Ziel der Paketverlusttests

Ziel der Paketverlusttests war es, das Verhalten des K3s-Clusters bei zunehmend instabiler Netzwerkkommunikation zwischen Control Plane und Worker-Knoten zu untersuchen. Die Paketverluste wurden zentral auf der Router-VM mittels `tc netem` eingebracht, sodass der Datenverkehr zwischen Server-Netz und Worker-Netz gezielt beeinträchtigt werden konnte.

Untersucht wurden Paketverlustraten von 1 %, 10 %, 50 %, 70 % und 100 %. Für jedes Szenario waren zehn Wiederholungen vorgesehen. Pro Durchlauf wurden eine Vorlaufphase, eine Störphase und eine Nachlaufphase aufgezeichnet. Die Anwendung wurde währenddessen über regelmäßige HTTP-Requests gegen den NodePort der Testanwendung überwacht.

## Überblick über die Szenarien

| Szenario           | Beobachtung                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------- |
| 1 % Paketverlust   | Keine sichtbare Beeinträchtigung der Anwendung oder Clusterstabilität                        |
| 10 % Paketverlust  | Anwendung weiterhin vollständig erreichbar, aber erhöhte Latenzspitzen                       |
| 50 % Paketverlust  | Erste Timeouts, deutliche Latenzanstiege und erstmals `NodeNotReady`-Events                  |
| 70 % Paketverlust  | Regelmäßige Timeouts, starke Latenzspitzen und `NodeNotReady` für beide Worker               |
| 100 % Paketverlust | Nahezu vollständige Nichtverfügbarkeit während der Störphase, schnelle Erholung nach Cleanup |

## Allgemeine Beobachtungen

Bei niedrigen Paketverlustraten von 1 % und 10 % blieb die Anwendung praktisch vollständig verfügbar. Die HTTP-Erfolgsrate lag in den auswertbaren Läufen bei 100 %. Kubernetes zeigte in diesen Szenarien keine relevanten Self-Healing-Reaktionen, da weder Pods noch Nodes als fehlerhaft erkannt wurden. Die Störung wirkte sich hauptsächlich auf einzelne Antwortzeiten aus, führte aber nicht zu einer erkennbaren Clusterreaktion.

Ab 50 % Paketverlust veränderte sich das Verhalten deutlich. Die Anwendung blieb zwar überwiegend erreichbar, jedoch stiegen die Antwortzeiten stark an und es traten erste Timeouts auf. Gleichzeitig wurden erstmals `NodeNotReady`-Events für Worker-Knoten beobachtet. Damit wurde sichtbar, dass die Netzwerkstörung nicht mehr nur die Anwendungskommunikation beeinflusste, sondern auch die interne Kommunikation zwischen Control Plane und Worker-Knoten.

Bei 70 % Paketverlust verschärften sich diese Effekte. Die Fault-Phasen zeigten regelmäßig Timeouts, deutlich erhöhte Latenzwerte und reduzierte Erfolgsraten. Beide Worker-Knoten wurden zeitweise als `NodeNotReady` markiert. Dennoch wurden keine klassischen Pod-bezogenen Self-Healing-Maßnahmen beobachtet. Insbesondere traten keine `Killing`-, `BackOff`- oder `Failed`-Events auf, und es wurden keine sichtbaren Pod-Neustarts oder Rescheduling-Vorgänge dokumentiert.

Bei 100 % Paketverlust entsprach die Störung praktisch einer vollständigen Netzwerkpartition zwischen Control Plane und Worker-Netz. Während der Fault-Phase war die Anwendung über den gemessenen Pfad nahezu nicht erreichbar. In den methodisch sauberen Läufen lag die Erfolgsrate während der Störphase nur noch ungefähr zwischen 0,5 % und 0,9 %. Nach Entfernen der Paketverlustregel erholte sich die Anwendung jedoch sehr schnell und erreichte in der Nachlaufphase wieder eine Erfolgsrate von 100 %.

## Vergleich der Wirkung auf die Anwendung

| Paketverlust | Anwendungserreichbarkeit während der Störung  |
| ------------ | --------------------------------------------- |
| 1 %          | vollständig erreichbar                        |
| 10 %         | vollständig erreichbar, aber Latenzspitzen    |
| 50 %         | überwiegend erreichbar, erste Timeouts        |
| 70 %         | deutlich beeinträchtigt, regelmäßige Timeouts |
| 100 %        | nahezu nicht erreichbar                       |

Die Ergebnisse zeigen eine klare Eskalation: Während geringe Paketverluste durch TCP und die Anwendungsebene weitgehend kompensiert werden konnten, führten hohe Paketverlustraten zu massiven Verzögerungen und Fehlern. Der Übergang zwischen 10 % und 50 % stellt dabei den ersten sichtbaren Kipppunkt dar. Ab 50 % werden nicht nur HTTP-Metriken beeinträchtigt, sondern auch Kubernetes-Events sichtbar. Bei 100 % bricht die Anwendungserreichbarkeit während der Fault-Phase nahezu vollständig zusammen.

## Vergleich der Kubernetes-Reaktion

| Paketverlust | Kubernetes-Beobachtung                             |
| ------------ | -------------------------------------------------- |
| 1 %          | keine relevanten Events                            |
| 10 %         | keine relevanten Events                            |
| 50 %         | erste `NodeNotReady`-Events                        |
| 70 %         | regelmäßige `NodeNotReady`-Events für beide Worker |
| 100 %        | `NodeNotReady` in allen Läufen für beide Worker    |

Die Kubernetes-Reaktion setzte erst bei hohen Paketverlustraten sichtbar ein. Bei 1 % und 10 % wurden keine Node-Ausfälle erkannt. Ab 50 % wurden Worker-Knoten zeitweise als `NodeNotReady` markiert. Bei 70 % und 100 % trat dieses Verhalten regelmäßig auf.

Trotz dieser Erkennung wurden keine Pod-Neustarts, keine BackOff-Zustände und kein sichtbares Rescheduling der Testanwendung beobachtet. Die Self-Healing-Mechanismen von K3s erkannten somit zwar die gestörte Node-Kommunikation, führten aber in diesen Paketverlustszenarien nicht zu einer automatischen Wiederherstellung der Anwendung während der aktiven Störung.

## Methodische Auffälligkeiten

Während der Paketverlusttests traten in mehreren Szenarien zeitliche Abweichungen der Fault-Dauer auf. Besonders bei hohen Paketverlustraten kam es teilweise dazu, dass die Störphase länger aktiv blieb als geplant. Für die späteren Tests wurde deshalb die Steuerung der Störung angepasst.

Zunächst wurde die Störung von `k3s-s1` aus per SSH auf der Router-VM gesetzt und entfernt. Ab den höheren Paketverluststufen wurde die Störphase direkt auf der Router-VM gesteuert. Zusätzlich wurde beim 100 %-Szenario ein Safety-Cleanup eingeführt, bei dem `k3s-s1` nach Ablauf der Störphase zusätzlich versucht, die `tc netem`-Regel über die NAT-Adresse des Routers zu entfernen.

Trotz dieser Anpassungen traten in einzelnen Läufen weiterhin zeitliche Abweichungen auf. Diese werden als methodische Einschränkung der lokalen Testumgebung dokumentiert und nicht als Kubernetes-Verhalten interpretiert. Für quantitative Vergleiche wurden daher bevorzugt die zeitlich sauberen Läufe berücksichtigt.

## Interpretation im Hinblick auf Self-Healing

Die Paketverlusttests zeigen, dass K3s bei geringer und mittlerer Netzwerkbeeinträchtigung keine Self-Healing-Maßnahmen auslöst, solange Pods und Nodes aus Sicht des Clusters nicht als fehlerhaft gelten. Die Anwendung bleibt in diesen Fällen erreichbar oder zumindest überwiegend nutzbar.

Bei hohen Paketverlustraten erkennt Kubernetes zwar Kommunikationsprobleme zu den Worker-Knoten und markiert diese als `NodeNotReady`. Daraus folgt jedoch nicht automatisch ein Pod-Neustart oder ein Rescheduling der Anwendung. Die Wiederherstellung der Anwendung erfolgt stattdessen primär durch das Entfernen der Netzwerkstörung.

Damit zeigen die Tests eine wichtige Grenze der untersuchten Self-Healing-Mechanismen: K3s kann Node-Kommunikationsprobleme erkennen, stellt die Anwendung während einer aktiven Netzwerkpartition jedoch nicht automatisch über alternative Platzierung wieder her. Die beobachtete Erholung nach der Störung ist daher eher als Wiederherstellung der Netzwerkverbindung zu interpretieren und nicht als aktive Pod-bezogene Self-Healing-Reaktion.

## Fazit

Die Paketverlusttests zeigen eine klare Eskalation des Systemverhaltens mit zunehmender Paketverlustrate.

Bis 10 % Paketverlust bleibt das System weitgehend stabil. Ab 50 % treten erste deutliche Beeinträchtigungen der Anwendung und der Clusterkommunikation auf. Bei 70 % werden diese Effekte deutlich stärker, während 100 % Paketverlust praktisch zu einer vollständigen temporären Nichtverfügbarkeit der Anwendung über den getesteten Pfad führt.

K3s erkennt hohe Paketverluste durch `NodeNotReady`-Events, löst jedoch keine sichtbaren Pod-bezogenen Self-Healing-Maßnahmen aus. Die Anwendung erholt sich nach Ende der Störung schnell, bleibt während starker oder vollständiger Netzwerkunterbrechungen aber nicht automatisch verfügbar.

Für die Gesamtbewertung bedeutet dies: Die Self-Healing-Fähigkeiten von K3s sind bei Paketverlust vor allem auf die Erkennung gestörter Nodes beschränkt. Eine aktive Wiederherstellung der Anwendung während der Netzwerkstörung konnte in diesen Experimenten nicht beobachtet werden.
