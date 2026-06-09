# Ergebnisse – 10 % Paketverlust

## Versuchsaufbau

Zwischen den Control-Plane- und Worker-Knoten wurde mittels Linux tc/netem ein Paketverlust von 10 % simuliert. Die Störung wurde auf der Router-VM erzeugt, sodass sämtlicher Verkehr zwischen den beiden Teilnetzen den Paketverlust durchlaufen musste.

Für jeden Durchlauf wurden 3 Minuten Vorlauf, 10 Minuten Störphase und 3 Minuten Nachlauf aufgezeichnet. Insgesamt wurden zehn Wiederholungen durchgeführt. Ein Lauf wurde aufgrund eines fehlerhaften zeitlichen Ablaufs verworfen.

## Beobachtungen

In allen gültigen Durchläufen konnte die erfolgreiche Anwendung des Paketverlusts anhand der tc-Konfiguration nachgewiesen werden. Während der Störphase blieb das Kubernetes-Cluster vollständig funktionsfähig.

Es wurden keine Node-Ausfälle, keine Pod-Ausfälle, keine Pod-Neustarts und keine Rescheduling-Vorgänge beobachtet. Ebenso traten keine Kubernetes-Events auf, die auf die Aktivierung von Self-Healing-Mechanismen hindeuten würden.

Die Erfolgsrate der HTTP-Anfragen blieb in allen gültigen Durchläufen bei 100 %. Timeouts oder dauerhafte Verbindungsabbrüche wurden nicht festgestellt.

Die Auswirkungen zeigten sich hauptsächlich in den Antwortzeiten. Während der Median der Antwortzeiten nahezu unverändert blieb, stiegen die oberen Perzentile deutlich an. Insbesondere die P95- und P99-Werte erhöhten sich während der Störphase auf etwa 210–420 ms. Dies deutet auf TCP-Neuübertragungen infolge verlorener Pakete hin.

## Bewertung

Ein Paketverlust von 10 % beeinträchtigt die Anwendungskommunikation messbar, führt jedoch nicht zu einer Aktivierung der Kubernetes-Self-Healing-Mechanismen. Die Anwendung bleibt vollständig verfügbar und das Cluster verhält sich stabil. Die beobachteten Auswirkungen beschränken sich auf erhöhte Antwortzeiten einzelner Anfragen.

10 Wiederholungen wurden durchgeführt.

Neun Läufe konnten erfolgreich ausgewertet werden.

Ein Lauf (Run 08) wurde aufgrund eines fehlerhaften zeitlichen Ablaufs des Messskripts verworfen.

Die verbleibenden neun Läufe zeigen konsistente Ergebnisse.
