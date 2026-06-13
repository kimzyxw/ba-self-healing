# Initialer Service-Check im KubeEdge-Setup

In diesem Verzeichnis wird der erste Service-Check der nginx-Testanwendung im KubeEdge-Setup dokumentiert.

Die Testanwendung wurde analog zum vorherigen K3s-Setup bereitgestellt. Sie basiert auf dem Container-Image `nginx:stable`, wird mit drei Replikas betrieben und befindet sich im Namespace `testapp`. Zusätzlich wurde ein Kubernetes-Service vom Typ `NodePort` mit dem festen Port `30080` angelegt.

## Ziel des Checks

Ziel dieses initialen Checks war es, zu prüfen, ob die im K3s-Setup verwendete Zugriffsstrategie über einen `NodePort` im KubeEdge-Setup in gleicher Weise funktioniert.

Dabei sollte insbesondere überprüft werden:

* ob die nginx-Pods erfolgreich auf den Edge-Knoten gestartet werden,
* ob die Anwendung innerhalb der Edge-Knoten erreichbar ist,
* ob der konfigurierte `NodePort` auf den Edge-Knoten erreichbar ist,
* ob ein Zugriff über die Cloud-Knoten möglich ist.

## Beobachteter Zustand

Die Pods wurden erfolgreich auf den KubeEdge-Edge-Knoten `e1` und `e2` gestartet.

Beobachtete Pod-Verteilung:

```text
e1: zwei nginx-Replikas
e2: eine nginx-Replika
```

Da im KubeEdge-Setup zwei Edge-Knoten zur Verfügung stehen, werden die drei Replikas auf diese beiden Knoten verteilt. Dadurch führt ein Edge-Knoten mehr als eine Replika aus. Entscheidend ist, dass die Anwendung ausschließlich auf der Edge-Seite läuft und nicht auf den cloudseitigen Control-Plane-Knoten.

Die direkte Erreichbarkeit der nginx-Pods über ihre Pod-IP-Adressen wurde auf den jeweiligen Edge-Knoten erfolgreich getestet. Die HTTP-Anfragen lieferten jeweils den Status `HTTP/1.1 200 OK` zurück.

Beispiele:

```bash
curl -I --max-time 3 http://10.88.1.2
curl -I --max-time 3 http://10.88.1.3
curl -I --max-time 3 http://10.88.2.2
```

Damit wurde bestätigt, dass die Testanwendung selbst korrekt gestartet wurde und innerhalb der Edge-Knoten erreichbar ist.

## NodePort-Verhalten

Der Service vom Typ `NodePort` war im KubeEdge-Setup nicht über die IP-Adressen der Edge-Knoten erreichbar.

Getestete Zugriffe auf die Edge-Knoten:

```bash
curl -I --max-time 3 http://10.10.20.131:30080
curl -I --max-time 3 http://10.10.20.132:30080
```

Beide Anfragen schlugen fehl.

Zusätzlich war der `NodePort` auch nicht über die cloudseitigen Knoten erreichbar:

```bash
curl -I --max-time 3 http://10.10.10.133:30080
curl -I --max-time 3 http://10.10.10.134:30080
curl -I --max-time 3 http://10.10.10.135:30080
```

Auch diese Anfragen liefen in Timeouts.

Auf den Edge-Knoten wurde zusätzlich geprüft, ob Port `30080` geöffnet ist:

```bash
sudo ss -tulpen | grep 30080 || echo "no nodeport listener"
```

Dabei zeigte sich, dass auf den Edge-Knoten kein Listener für den NodePort vorhanden war.

## Interpretation

Der Test zeigt, dass die nginx-Anwendung im KubeEdge-Setup korrekt ausgeführt wird, der Kubernetes-`NodePort` jedoch nicht wie im K3s-Setup auf den Edge-Knoten bereitgestellt wird.

Dies ist ein relevanter Unterschied zwischen beiden Systemen. Im K3s-Setup wurden die Worker-Knoten als reguläre Kubernetes-Knoten mit vollständiger Service-Proxy-Funktionalität betrieben. Im KubeEdge-Setup sind die Edge-Knoten dagegen über EdgeCore angebunden und verhalten sich nicht vollständig wie klassische Kubernetes-Worker.

Der NodePort-Service existiert zwar im Cluster, ist aber auf den KubeEdge-Edge-Knoten nicht in gleicher Weise nutzbar.

## Konsequenz für die weiteren Experimente

Für eine saubere und realitätsnahe KubeEdge-Testumgebung wird der Servicezugriff daher nicht über manuelle Pod-IP-Zugriffe, statische Portweiterleitungen oder zusätzliche `iptables`-Regeln nachgebildet.

Stattdessen soll der KubeEdge-spezifische Servicezugriff über EdgeMesh ergänzt werden. Dadurch bleibt die Testanwendung strukturell vergleichbar zum K3s-Setup, während gleichzeitig ein für KubeEdge geeigneter und produktionsnäherer Zugriffspfad verwendet wird.

Die geplanten Netzwerkstörungen werden weiterhin ausschließlich über die Router-VM gesteuert. Damit bleibt der relevante Kommunikationspfad zwischen Cloud- und Edge-Netz kontrollierbar und vergleichbar.
