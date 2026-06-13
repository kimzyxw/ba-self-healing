# EdgeMesh-Setup für den KubeEdge-Servicezugriff

Dieses Verzeichnis dokumentiert das EdgeMesh-Setup, das für den Servicezugriff im KubeEdge-Testsystem verwendet wurde.

## Motivation

Die NGINX-Testanwendung wird im KubeEdge-Setup analog zu den K3s-Experimenten mit drei Replikaten und einem NodePort-Service auf Port 30080 bereitgestellt. Im initialen KubeEdge-Aufbau wurden die NGINX-Pods erfolgreich auf den Edge-Knoten ausgeführt und waren über ihre Pod-IPs erreichbar. Der NodePort-Service war jedoch auf den Edge-Knoten zunächst nicht erreichbar.

Der Grund dafür ist, dass KubeEdge-Edge-Knoten über EdgeCore angebunden sind und sich nicht vollständig wie klassische Kubernetes-Worker mit kube-proxy-basiertem NodePort-Verhalten verhalten. Für die Experimente wird jedoch ein stabiler und reproduzierbarer Service-Endpunkt benötigt.

Deshalb wurde EdgeMesh ergänzt. EdgeMesh stellt in KubeEdge-Umgebungen Service Discovery und Traffic Proxying für Edge-Szenarien bereit. In diesem Setup stellt der EdgeMesh-Agent den Zugriff auf die NGINX-Testanwendung über den NodePort 30080 auf den Edge-Knoten bereit.

## Version und Quelle

EdgeMesh wurde aus dem offiziellen Repository `kubeedge/edgemesh` verwendet. Installiert wurde der Release-Tag `v1.17.0`.

Die verwendeten Manifeste wurden in dieses Repository kopiert:

* `crd-destinationrule.yaml`
* `crd-gateway.yaml`
* `crd-virtualservice.yaml`
* `01-serviceaccount.yaml`
* `02-clusterrole.yaml`
* `03-clusterrolebinding.yaml`
* `04-configmap.yaml`
* `05-daemonset.yaml`

## Lokale Anpassungen

Das Standardmanifest des EdgeMesh-Agents wurde für das Testsetup angepasst.

Zunächst wurde ein neuer Pre-Shared Key für die EdgeMesh-Agent-Konfiguration erzeugt. Außerdem wurde das DaemonSet so eingeschränkt, dass der EdgeMesh-Agent nur auf den Edge-Knoten läuft. Dafür wurde ein `nodeSelector` ergänzt:

```yaml
nodeSelector:
  node-role.kubernetes.io/edge: ""
```

Dadurch läuft der EdgeMesh-Agent nur auf `e1` und `e2`, nicht jedoch auf den Cloud-/Control-Plane-Knoten `c1`, `c2` und `c3`.

## Validierung

Nach der Installation liefen zwei EdgeMesh-Agent-Pods erfolgreich auf den beiden Edge-Knoten:

* `e1` mit der IP-Adresse `10.10.20.131`
* `e2` mit der IP-Adresse `10.10.20.132`

Der NGINX-Service war anschließend über den NodePort 30080 auf beiden Edge-Knoten erreichbar.

Erfolgreiche Validierung von `c1`:

* `http://10.10.20.131:30080` → `HTTP/1.1 200 OK`
* `http://10.10.20.132:30080` → `HTTP/1.1 200 OK`

Erfolgreiche Validierung von `e1`:

* `http://127.0.0.1:30080` → `HTTP/1.1 200 OK`
* `http://10.10.20.131:30080` → `HTTP/1.1 200 OK`
* `http://10.10.20.132:30080` → `HTTP/1.1 200 OK`

Erfolgreiche Validierung von `e2`:

* `http://127.0.0.1:30080` → `HTTP/1.1 200 OK`
* `http://10.10.20.132:30080` → `HTTP/1.1 200 OK`
* `http://10.10.20.131:30080` → `HTTP/1.1 200 OK`

Damit ist bestätigt, dass die NGINX-Testanwendung über EdgeMesh auf beiden Edge-Knoten erreichbar ist.

## Methodischer Hinweis

Für die weiteren KubeEdge-Experimente werden daher folgende Service-Endpunkte verwendet:

```text
http://10.10.20.131:30080
http://10.10.20.132:30080
```

Der Cloud-Edge-Netzwerkpfad verläuft weiterhin über die Router-VM. Dadurch können Latenz, Paketverlust und Verbindungsabbrüche weiterhin zentral auf der Router-VM injiziert werden. EdgeMesh ergänzt lediglich die fehlende Servicezugriffsschicht auf den KubeEdge-Edge-Knoten und ersetzt keine Netzwerkstörung oder Routingkomponente des Versuchsaufbaus.
