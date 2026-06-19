# Archivierte KubeEdge Pod-Failure-Läufe

Diese Läufe wurden nicht als finale Messdaten verwendet.

Grund:
Im ersten Lauf zeigte sich eine Recovery Time von 61 Sekunden. Die Datei recovery_poll.log enthält jedoch nur einen einzigen Polling-Eintrag mit bereits 3/3 bereiten Pods. Das deutet darauf hin, dass kubectl delete pod blockierend ausgeführt wurde und das Recovery-Polling erst nach Abschluss des Delete-Kommandos startete.

Zur methodisch saubereren Messung wurde das Skript anschließend angepasst, sodass kubectl delete mit --wait=false ausgeführt wird. Dadurch beginnt das Recovery-Polling unmittelbar nach der Fehlerauslösung.
