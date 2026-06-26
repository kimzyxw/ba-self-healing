# KubeEdge Latenztest: 1s

## Szenario

In diesem Szenario wurde auf dem Router-VM-Interface `ens161` eine künstliche Netzwerklatenz von `1s` gesetzt. Damit wurde der Datenpfad zwischen Cloud- und Edge-Seite beeinflusst. Die Messung wurde mit dem asynchronen Request-Monitor und `MAX_IN_FLIGHT=10` durchgeführt.

Die Messreihe umfasst 10 Versuchsläufe.

## Methodische Validierung

Alle 10 Läufe wurden erfolgreich abgeschlossen. In allen Läufen wurde die Latenz ausschließlich auf dem Router-Interface `ens161` gesetzt. Die vorherige bidirektionale KubeEdge-Latenzmessung wurde archiviert und wird nicht als finale Vergleichsbasis verwendet.

Validierung über alle Läufe:

- `router_ifaces=ens161`
- `tc_active=yes`
- `tc_cleanup_documented=yes`
- `latency_applied=yes`

Damit ist diese Messreihe methodisch konsistenter mit den K3s-Latenztests, bei denen ebenfalls nur ein Router-Interface belastet wurde.

## Ergebnisse

Über alle 10 Läufe blieb die Testanwendung vollständig erreichbar. Die Success Rate betrug sowohl insgesamt als auch in Baseline, Störphase und Nachlauf 100 %. Es wurden keine HTTP-Fehler beobachtet.

| Metrik | Ergebnis |
|---|---:|
| Runs | 10 |
| Overall Success Rate | 100.00 % |
| Overall Error Rate | 0.00 % |
| Baseline Success Rate | 100.00 % |
| Fault Success Rate | 100.00 % |
| After Success Rate | 100.00 % |
| Fault Median Latency | 1001.87 ms |
| Fault p95 Latency | 1003.15 ms |
| Fault p99 Latency | 1004.75 ms |
| After Median Latency | 1.25 ms |
| Recovery Latency Median | 1.18 s |

## Bewertung

Die eingebrachte Latenz von 1 s führte bei KubeEdge zu keiner Dienstunterbrechung. Während der Störphase erhöhte sich die Antwortzeit erwartungsgemäß ungefähr um die gesetzte Verzögerung. Nach Entfernen der Latenz sank die Antwortzeit wieder auf das Ausgangsniveau ab.

In allen Läufen wurden auch in der Nachlaufphase Requests erfasst. Die Nachlaufphase ist daher für dieses Szenario aussagekräftig. Die Anwendung war nach Entfernen der Latenz weiterhin erreichbar, und der Cluster befand sich nach Abschluss der Messreihe in einem stabilen Zustand.

## Clusterzustand nach der Messreihe

Nach Abschluss der Messreihe waren alle Knoten im Zustand `Ready`. Die drei Pods der Testanwendung liefen im Zustand `Running`, und die NodePort-Prüfung auf beiden Edge-Knoten lieferte HTTP 200.
