# Ergebnisse – 50 % Paketverlust

## Versuchsaufbau

Zwischen den Control-Plane- und Worker-Knoten wurde mittels tc/netem auf der Router-VM ein Paketverlust von 50 % simuliert.

Für jeden Durchlauf wurden 3 Minuten Vorlauf, 10 Minuten Störphase und 3 Minuten Nachlauf aufgezeichnet.

Insgesamt wurden zehn Wiederholungen durchgeführt. Aufgrund fehlerhafter zeitlicher Abläufe einzelner Durchläufe wurden für die quantitative Auswertung ausschließlich die vollständig aufgezeichneten Läufe berücksichtigt.

## Beobachtungen

Der konfigurierte Paketverlust von 50 % wurde in allen Durchläufen erfolgreich angewendet.

Im Gegensatz zu den Experimenten mit 1 % und 10 % Paketverlust wurden erstmals Auswirkungen auf die Clusterkommunikation sichtbar. Mehrere Worker-Knoten wurden während der Störphase zeitweise als `NodeNotReady` markiert.

Trotzdem wurden keine Pods neu gestartet, keine Pods migriert und keine zusätzlichen Container erzeugt. Ebenso traten keine BackOff-, Failed- oder Killing-Events auf.

## Anwendungsverhalten

Die Auswirkungen auf die Anwendung waren deutlich stärker als bei niedrigeren Paketverlustraten.

Während der Median der Antwortzeiten in der Störphase auf etwa 210 ms anstieg, erhöhten sich die P95-Werte auf etwa 2,7–3,3 Sekunden. Einzelne Anfragen erreichten Antwortzeiten von über 20 Sekunden.

Zusätzlich wurden erstmals Timeouts beobachtet. Die Erfolgsrate sank in einzelnen Durchläufen geringfügig auf Werte zwischen etwa 99,5 % und 99,8 %.

## Bewertung

Ein Paketverlust von 50 % beeinträchtigt sowohl die Anwendungskommunikation als auch die interne Clusterkommunikation deutlich.

Die Kubernetes-Überwachungsmechanismen erkennen zeitweise Kommunikationsprobleme zwischen Worker- und Control-Plane-Knoten und markieren einzelne Nodes als `NodeNotReady`.

Trotz dieser Erkennung werden jedoch noch keine tatsächlichen Self-Healing-Maßnahmen wie Pod-Neustarts oder Rescheduling-Vorgänge ausgelöst.

Die Ergebnisse deuten darauf hin, dass 50 % Paketverlust einen kritischen Bereich darstellen, in dem die Clusterstabilität sichtbar beeinträchtigt wird, ohne dass das System bereits aktiv Gegenmaßnahmen einleitet.

## Methodische Auffälligkeit und Konsequenz für Folgetests

Bei mehreren Durchläufen wurde festgestellt, dass die tatsächliche Dauer der Störphase von der geplanten Dauer abwich. Die Ursache liegt vermutlich darin, dass das Entfernen der `tc netem`-Regel von `k3s-s1` aus per SSH auf der Router-VM ausgelöst wurde. Bei hohem Paketverlust kann genau diese Steuerverbindung beeinträchtigt werden, sodass das Entfernen der Störung verzögert erfolgt.

Diese Abweichung betrifft vor allem die quantitative Vergleichbarkeit einzelner Durchläufe. Für die Auswertung wurden deshalb nur die zeitlich vollständigen und methodisch sauberen Läufe herangezogen.

Als Konsequenz wird die Steuerung der Störphase für die folgenden höheren Paketverluststufen angepasst: Die Router-VM soll die `tc netem`-Regel künftig selbst setzen, die Störphase lokal abwarten und die Regel anschließend eigenständig entfernen. Dadurch hängt das Ende der Störphase nicht mehr von einer SSH-Verbindung während der aktiven Netzwerkstörung ab.
