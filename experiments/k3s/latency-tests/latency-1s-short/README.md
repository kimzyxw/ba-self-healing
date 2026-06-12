# Latenztest 1s – verkürzte Messreihe

## Ziel

Ziel dieses Experiments war die Untersuchung des Verhaltens eines hochverfügbaren K3s-Clusters unter erhöhter Netzwerklatenz. Dabei sollte überprüft werden, ob eine künstlich eingebrachte Verzögerung von 1 Sekunde Auswirkungen auf die Erreichbarkeit der Anwendung, den Zustand des Clusters oder die Kubernetes-Komponenten hat.

Die Messreihe stellt die erste reguläre Versuchsreihe nach erfolgreicher Validierung des Testframeworks dar.

---

## Versuchsaufbau

### Infrastruktur

* K3s-Cluster mit drei Server-Nodes (Control Plane + etcd)
* Zwei Worker-Nodes
* Separate Router-VM zwischen Server- und Worker-Netz
* Ubuntu Server ARM64 auf VMware Fusion

### Testanwendung

* nginx Deployment
* 3 Replikate
* Bereitstellung über Kubernetes Service (NodePort)

### Monitoring

Während des gesamten Versuchs wurde jede Sekunde ein HTTP-Request an die Testanwendung gesendet. Für jeden Request wurden Zeitstempel, Antwortzeit, HTTP-Statuscode und Erfolg bzw. Fehler protokolliert.

---

## Versuchsparameter

| Parameter           | Wert  |
| ------------------- | ----- |
| Eingebrachte Latenz | 1 s   |
| Vorlauf             | 180 s |
| Störphase           | 300 s |
| Nachlauf            | 180 s |
| Wiederholungen      | 10    |
| Requestintervall    | 1 s   |

---

## Validierung der Störung

Vor jedem Durchlauf wurde geprüft, ob der Netzwerkverkehr tatsächlich über die Router-VM geleitet wird.

Die Traceroute-Ausgaben zeigten in allen zehn Durchläufen die Router-Adresse 10.10.10.128 als ersten Hop. Dadurch konnte bestätigt werden, dass die Testpakete den vorgesehenen Netzwerkpfad verwendeten.

Während der Störphase wurde auf der Router-VM mittels Linux NetEm eine Verzögerung von 1 Sekunde aktiviert:

```text
tc qdisc add ... netem delay 1s
```

Die automatische Validierung des Testframeworks bestätigte in allen zehn Durchläufen:

* Routerpfad korrekt verwendet
* NetEm-Regel aktiv
* NetEm-Regel nach Versuch wieder entfernt
* Latenz erfolgreich eingebracht

Für alle Durchläufe wurde deshalb die Kennzeichnung

```text
latency_applied=yes
```

ausgegeben.

---

## Ergebnisse

### Verfügbarkeit

| Kennzahl             | Ergebnis |
| -------------------- | -------- |
| Request Success Rate | 100 %    |
| Fehlerrate           | 0 %      |
| HTTP-Fehler          | keine    |
| Timeouts             | keine    |

Während des gesamten Experiments blieb die Testanwendung durchgehend erreichbar.

---

### Kubernetes-Verhalten

Während der Versuche wurden keine Auswirkungen auf den Clusterzustand beobachtet.

* Alle Nodes verblieben im Zustand Ready.
* Es traten keine Node-Ausfälle auf.
* Es wurden keine Kubernetes-Events erzeugt.
* Es wurden keine Pod-Restarts festgestellt.
* Die Control Plane blieb durchgehend verfügbar.
* Es waren keine Selbstheilungsmaßnahmen erforderlich.

---

### Antwortzeiten während der Störphase

Die Medianwerte der Antwortzeiten lagen bei allen Durchläufen sehr konstant bei etwa 2008–2010 ms.

Dies entspricht dem erwarteten Verhalten:

* 1 s Verzögerung auf dem Hinweg
* 1 s Verzögerung auf dem Rückweg

Daraus ergibt sich eine erwartete Round-Trip-Latenz von ungefähr 2 Sekunden.

| Run | Median [ms] | p95 [ms] |
| --- | ----------: | -------: |
| 01  |     2008.24 |  2011.05 |
| 02  |     2009.53 |  2014.33 |
| 03  |     2008.43 |  2013.01 |
| 04  |     2007.38 |  2012.01 |
| 05  |     2009.76 |  2012.68 |
| 06  |     2007.88 |  2011.87 |
| 07  |     2009.05 |  2013.59 |
| 08  |     2008.66 |  2016.69 |
| 09  |     2007.47 |  2012.54 |
| 10  |     2007.74 |  2013.10 |

Die geringe Streuung zwischen den Durchläufen zeigt eine hohe Reproduzierbarkeit der eingebrachten Netzwerklatenz.

---

### Recovery Time

Nach dem Entfernen der NetEm-Regel normalisierten sich die Antwortzeiten innerhalb weniger Sekunden.

| Run | Recovery Time [s] |
| --- | ----------------: |
| 01  |             11.41 |
| 02  |             11.63 |
| 03  |             10.93 |
| 04  |             11.45 |
| 05  |             11.52 |
| 06  |             11.74 |
| 07  |             11.38 |
| 08  |             12.01 |
| 09  |             12.47 |
| 10  |             11.20 |

Die Wiederherstellungszeit lag damit in allen Durchläufen zwischen etwa 11 und 12,5 Sekunden.

---

## Beobachtete Ausreißer

In einzelnen Durchläufen wurden sehr hohe Einzelwerte beobachtet.

Beispiele:

* Run 02: maximal 996.115 ms
* Run 08: maximal 140.466 ms

Diese Werte liegen deutlich außerhalb des zu erwartenden Bereichs einer künstlich eingebrachten Latenz von 1 Sekunde.

Gleichzeitig zeigen die zugehörigen Median- und Perzentilwerte weiterhin die erwarteten Werte von etwa 2 Sekunden.

Beispiel Run 02:

| Kennzahl |       Wert |
| -------- | ---------: |
| Median   |    2009 ms |
| p95      |    2014 ms |
| Maximum  | 996.115 ms |

Da die Ausreißer nur vereinzelt auftreten und weder Median noch p95 signifikant beeinflussen, wird davon ausgegangen, dass es sich nicht um tatsächliche Netzwerkeffekte handelt.

Mögliche Ursachen sind:

* kurzfristige Verzögerungen im Request-Monitor
* blockierte Python-Prozesse
* verzögert abgeschlossene HTTP-Verbindungen
* Zeitmessungsartefakte innerhalb der virtuellen Umgebung

Aus diesem Grund werden für die Bewertung der Netzwerklatenz hauptsächlich Median und Perzentile verwendet. Diese Kennzahlen gelten als robuster gegenüber einzelnen Extremwerten.

Die Ausreißer werden dennoch vollständig dokumentiert, um die Nachvollziehbarkeit der Messergebnisse sicherzustellen.

---

## Interpretation

Die künstlich eingebrachte Netzwerklatenz wurde erfolgreich und reproduzierbar angewendet.

Eine zusätzliche Verzögerung von 1 Sekunde führte zu einer erwarteten Erhöhung der Antwortzeit auf etwa 2 Sekunden, beeinflusste jedoch weder die Verfügbarkeit der Anwendung noch den Zustand des Kubernetes-Clusters.

Es konnten keine Selbstheilungsmechanismen beobachtet werden, da kein tatsächlicher Ausfallzustand eintrat. Die erhöhte Latenz stellt somit für das betrachtete K3s-System keinen Fehlerfall dar, der eine Reaktion der Kubernetes-Komponenten auslöst.

---

## Methodische Anpassung

Vor dieser Messreihe wurde ein Pilotversuch mit deutlich längerer Störphase durchgeführt. Dieser bestätigte bereits die korrekte Funktionsweise des Testframeworks und die erfolgreiche Einbringung der Latenz.

Da längere Störphasen keine zusätzlichen Erkenntnisse lieferten, gleichzeitig jedoch einen erheblichen Zeitaufwand verursachten, wurde die Dauer der regulären Messreihen reduziert.

Die hier dokumentierte Messreihe dient daher als Grundlage für die weitere Untersuchung höherer Latenzen.
