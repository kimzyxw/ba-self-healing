# KubeEdge Latenztests

## Methodischer Hinweis zur ersten Messreihe

Die ursprünglich durchgeführten KubeEdge-Latenztests wurden archiviert, da sie nicht vollständig analog zu den K3s-Latenztests durchgeführt wurden.

Bei K3s wurde die künstliche Netzwerklatenz auf genau einem Router-Interface gesetzt. Im K3s-Skript wurde dafür ROUTER_IFACE="ens256" verwendet. Bei den ursprünglichen KubeEdge-Latenztests wurde die Latenz dagegen standardmäßig auf zwei Router-Interfaces gesetzt. Im KubeEdge-Skript war dafür ROUTER_IFACES="${ROUTER_IFACES:-ens161 ens256}" konfiguriert.

Damit wurde die Latenz bei KubeEdge bidirektional beziehungsweise auf beiden Router-Seiten eingebracht, während sie bei K3s nur auf einer Richtung des Routerpfads gesetzt wurde. Da HTTP-Anfragen sowohl Hin- als auch Rückrichtung betreffen, sind diese ursprünglichen KubeEdge-Latenzwerte nicht direkt 1:1 mit den K3s-Latenztests vergleichbar.

## Archivierte Messdaten

Die ursprünglichen KubeEdge-Latenztests wurden nicht gelöscht, sondern in folgendem Archivordner innerhalb dieses Verzeichnisses abgelegt:

archived-bidirectional/

Diese Daten bleiben zur Nachvollziehbarkeit erhalten, werden aber nicht als finale Vergleichsbasis für die Gegenüberstellung mit K3s verwendet.

## Konsequenz für die finale Auswertung

Für die finale vergleichende Auswertung werden die KubeEdge-Latenztests erneut durchgeführt. Dabei wird die Latenz analog zu K3s nur auf einem Router-Interface gesetzt.

Für die neuen Messreihen wird explizit folgendes verwendet:

ROUTER_IFACES="ens161"

Dadurch wird sichergestellt, dass KubeEdge und K3s methodisch konsistenter verglichen werden können: In beiden Fällen wird die künstliche Latenz auf genau einem Router-Interface eingebracht.

## Betroffene Szenarien

Die folgenden KubeEdge-Latenzszenarien werden erneut durchgeführt:

| Szenario | Dauer der Störphase | Runs |
|---|---:|---:|
| latency-1s | 1s | 10 |
| latency-1min | 60s | 10 |
| latency-10min | 600s | 10 |
| latency-30min | 1800s | 10 |

## Nicht betroffene Szenarien

Die Packet-Loss-Tests sind von diesem Problem nicht betroffen, da sowohl bei K3s als auch bei KubeEdge jeweils nur ein Router-Interface für tc netem loss verwendet wurde.

Die Link-Cut-Tests sind ebenfalls nicht betroffen, da in beiden Systemen jeweils ein Router-Interface mittels ip link down/up temporär deaktiviert wurde.
