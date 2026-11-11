# Service Catalog & Port Allocation Matrix

## 1. Master Application Inventory

All workloads run in the Kubernetes `homelab` namespace (or `kube-system` / `argocd`), mounting host directories for persistent state.

| Application | Namespace | Container Image | Host Port (NodePort) | Local URL (LAN) | Remote URL (Tailscale) | Purpose & Persistence Layout |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Headlamp** | `kube-system` | `ghcr.io/headlamp-k8s/headlamp:latest` | `80` / `443` *(Ingress)* | `http://192.168.1.100` | `http://100.64.0.10` | Web UI for Kubernetes introspection, live logs, and web terminal. |
| **ArgoCD** | `argocd` | `quay.io/argoproj/argocd:v3.6.1` | `30200` | `http://192.168.1.100:30200` | `http://100.64.0.10:30200` | GitOps continuous delivery engine synchronizing `k8s-manifests/`. |
| **Homepage** | `homelab` | `ghcr.io/gethomepage/homepage:latest` | `30050` | `http://192.168.1.100:30050` | `http://100.64.0.10:30050` | Application launcher and system metrics dashboard (`homepage/config`). |
| **Paperless-ngx** | `homelab` | `ghcr.io/paperless-ngx/paperless-ngx:latest` | `30082` | `http://192.168.1.100:30082` | `http://100.64.0.10:30082` | Document archiving and OCR. Backed by Redis cache (`paperless/data`, `media`). |
| **Nextcloud** | `homelab` | `docker.io/library/nextcloud:apache` | `30080` | `http://192.168.1.100:30080` | `http://100.64.0.10:30080` | Self-hosted cloud storage, calendar, and contacts (`nextcloud/html`). |
| **Firefly III** | `homelab` | `docker.io/fireflyiii/core:latest` | `30090` | `http://192.168.1.100:30090` | `http://100.64.0.10:30090` | Personal finance management and double-entry budgeting (`firefly/upload`). |
| **Firefly Importer** | `homelab` | `docker.io/fireflyiii/data-importer:latest` | `30091` | `http://192.168.1.100:30091` | `http://100.64.0.10:30091` | Automated banking CSV / OFX ingestion tool. |
| **Grafana** | `homelab` | `docker.io/grafana/grafana:latest` | `30030` | `http://192.168.1.100:30030` | `http://100.64.0.10:30030` | Telemetry visualizer (`monitoring/grafana_data`). |
| **Prometheus** | `homelab` | `docker.io/prom/prometheus:latest` | `9090` *(Internal)* | `http://192.168.1.100:9090` | - | Time-series metrics engine (`monitoring/prometheus_data`). |
| **Node Exporter** | `homelab` | `docker.io/prom/node-exporter:latest` | `9100` *(HostNet)* | `http://192.168.1.100:9100` | - | Host hardware telemetry DaemonSet (CPU, temperature, disks, net). |
| **Pi-hole (RPI)** | Standalone | `pihole/pihole:latest` *(Native FTL)* | `53`, `80` | `http://192.168.1.20/admin` | `http://100.64.0.20/admin` | Network-wide ad-blocking and DNS sinkhole running on Raspberry Pi Zero W. |
| **Cockpit** | Systemd | Fedora native cockpit daemon | `9090` | `https://192.168.1.100:9090` | `https://100.64.0.10:9090` | Linux operating system administration (storage, updates, journals). |
| **Syncthing** | Systemd | Syncthing daemon | `8384` | `http://192.168.1.100:8384` | `http://100.64.0.10:8384` | Peer-to-peer data and vault synchronization Web GUI. |
| **LocalSend** | Systemd | `localgo` daemon | `53317` | - | - | Headless local high-throughput file transfer listener. |

---

## 2. Port Allocation Reference Matrix

| Port | Protocol | Scope | Service Mapping |
| :--- | :--- | :--- | :--- |
| **80** | HTTP | Ingress (Traefik) | Headlamp Web UI / HTTP Ingress Router |
| **443** | HTTPS | Ingress (Traefik) | Traefik TLS Termination |
| **6443** | HTTPS | TLS API | Kubernetes K3s API Server |
| **8080** | HTTP | Internal Pod | Firefly III Core / Importer Container Endpoint |
| **8384** | HTTP | Host / Mesh | Syncthing Web Management GUI |
| **9090** | HTTP / HTTPS | Host / Pod | Cockpit Web Admin / Prometheus Metrics |
| **9100** | HTTP | HostNetwork | Node Exporter Hardware Telemetry |
| **22000** | TCP / UDP | Mesh / LAN | Syncthing Peer Sync Protocol (TLS 1.3 / QUIC) |
| **30030** | HTTP | NodePort | Grafana Dashboard UI |
| **30050** | HTTP | NodePort | Homepage Service Portal |
| **30080** | HTTP | NodePort | Nextcloud Cloud Suite |
| **30082** | HTTP | NodePort | Paperless-ngx Document Engine |
| **30090** | HTTP | NodePort | Firefly III Personal Finance |
| **30091** | HTTP | NodePort | Firefly III Data Importer |
| **30200** | HTTP | NodePort | ArgoCD Continuous Delivery Console |
| **41641** | UDP | Mesh | Tailscale WireGuard Encapsulation |
| **53317** | TCP | LAN Local | LocalSend Headless File Receiver |
