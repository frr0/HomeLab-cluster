# System Architecture & Hardware Topology

## 1. Architectural Vision

This repository documents a production-grade, multi-node personal infrastructure designed for high availability, self-healing, zero-trust remote access, and automated GitOps continuous reconciliation.

The infrastructure bridges physical servers, developer workstations, low-power edge sentinels, and mobile endpoints across an end-to-end encrypted WireGuard mesh network (Tailscale).

```mermaid
flowchart TD
    subgraph Mobile["📱 Mobile Client (Android)"]
        Phone["Motorola Edge 50 Neo\n(100.64.0.60)"]
        TeleApp["Telegram App\n(4 Bot Interfaces)"]
        ObsMobile["Obsidian Mobile Vault"]
        SyncPhone["Syncthing P2P Node"]
        Phone --> TeleApp
        Phone --> ObsMobile
        Phone --> SyncPhone
    end

    subgraph Mesh["🔒 Tailscale Encrypted Mesh Overlay (WireGuard)"]
        TS_Workstation["Workstation (cachyos-thinkpad)\n(100.64.0.50)"]
        TS_Server["Server (fedora-server)\n(100.64.0.10)"]
        TS_Sentinel["Sentinel (raspberrypi-zero)\n(100.64.0.20)"]
        TS_Phone["Mobile Client\n(100.64.0.60)"]
    end

    subgraph Host_Workstation["💻 Workstation: ThinkPad (CachyOS Linux / Wayland)"]
        DesktopShell["Niri Scrollable Tiling Compositor\n+ Noctalia UI + Alacritty + Tmux + LazyVim"]
        KubeClient["kubectl CLI Client v1.37.2\n(Remote TLS 6443)"]
        SyncPC["Syncthing Daemon (PC)"]
        LocalgoPC["LocalSend CLI"]
        BotsWorkstation["Local Bots:\n• AIbot (Autonomous CLI Agent)\n• Cluster Admin Bot (@myclusterremotebot)"]
    end

    subgraph Host_Server["🖥️ HomeLab Server: x86_64 Headless (Fedora Server 45)"]
        subgraph K3s_Engine["☸️ Lightweight Kubernetes Cluster (K3s v1.37.2+k3s1)"]
            ControlPlane["K3s Control Plane + containerd 2.3.7\n(Embedded Kine / SQLite)"]
            Traefik["Traefik v3 Ingress Controller\n(Port 80 HTTP / 443 HTTPS)"]
            ArgoCD["ArgoCD v3.6.1 GitOps Engine\n(Automated Git Sync & Self-Healing)"]
        end

        subgraph K3s_System["Namespace: kube-system"]
            Headlamp["🌟 Headlamp Web Dashboard (:4466)\n(Traefik Ingress on /)"]
            CoreDNS["CoreDNS Internal Resolver"]
            MetricsServer["Kubernetes Metrics Server"]
            LocalPath["Local-Path Storage Provisioner"]
        end

        subgraph K3s_Homelab["Namespace: homelab"]
            Nextcloud["☁️ Nextcloud Apache (:30080)"]
            Paperless["📄 Paperless-ngx (:30082) + Redis"]
            Firefly["💰 Firefly III (:30090) + MariaDB + Importer (:30091)"]
            Homepage["🏠 Homepage Dashboard (:30050)"]
            Monitoring["📊 Grafana (:30030) + Prometheus (:9090) + Node-Exporter (:9100)"]
        end

        subgraph Server_Host_Services["Host Services & Storage Engine"]
            HostStorage["Persistent HostPath Storage\n(/home/server/homelab-storage/...)"]
            Cockpit["Cockpit Web Admin (:9090)"]
            SyncServer["Syncthing Server Daemon (:8384)"]
            LocalgoServer["LocalSend Headless Daemon (:53317)"]
            ExitNode["Tailscale Exit Node\n(IP Forwarding & NAT Masquerade)"]
        end
    end

    subgraph Host_Sentinel["📡 Edge Sentinel & DNS: Raspberry Pi Zero W (100.64.0.20)"]
        RPI_Pihole["🛡️ Pi-hole v6 FTL (:53 DNS, :80 Web)\nGlobal DNS Sinkhole for Mesh Clients"]
        RPI_Sentinel["📡 24/7 Network Sentinel Bot\nARP Scans, Anti-Flapping Filter, Intrusion Alerts"]
    end

    %% Network links
    KubeClient -->|"TLS API (:6443)"| ControlPlane
    Phone -->|"Tailscale Mesh (HTTP :80/:443)"| Traefik
    Traefik --> Headlamp
    Phone -->|"NodePort Access"| K3s_Homelab
    Host_Workstation -->|"NodePort Access"| K3s_Homelab
    K3s_Homelab -->|"hostPath Mounts"| HostStorage
    SyncPhone <-->|"P2P TLS 1.3 Sync"| SyncPC
    SyncPC <-->|"P2P TLS 1.3 Sync"| SyncServer
    LocalgoPC <-->|"LAN High-Speed Transfer"| LocalgoServer
    TeleApp <-->|"Remote Ops & Alerts"| BotsWorkstation
    TeleApp <-->|"Intrusion Notifications"| RPI_Sentinel
    TS_Phone -->|"Encrypted Tunnel via Exit Node"| ExitNode
```

---

## 2. Hardware Topology & Specifications

| Node Identifier | Hardware Architecture | CPU & Specs | RAM & Storage | Operating System | Network Interfaces | Primary Responsibilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fedora Server** (`fedora-server`) | x86_64 Laptop (Headless, Lid Inactive) | Intel Core i5-4200U<br>(2C/4T @ 2.6 GHz) | 16 GB DDR3L RAM<br>240 GB SSD (LVM ext4) | **Fedora Server 45**<br>(Linux Kernel 6.17+) | LAN: `192.168.1.100`<br>Tailscale: `100.64.0.10` | K3s Control Plane & Worker, ArgoCD GitOps, Traefik Ingress, Headlamp UI, Cockpit, Tailscale Exit Node, Persistent Storage. |
| **Workstation** (`cachyos-thinkpad`) | Lenovo ThinkPad Laptop | AMD Ryzen 5 PRO 5650U<br>(6C/12T @ 4.2 GHz) | 16 GB DDR4 RAM<br>512 GB NVMe SSD | **CachyOS Linux**<br>(BORE scheduler, Wayland/Niri) | Wi-Fi (DHCP)<br>Tailscale: `100.64.0.50` | Primary development workstation, `kubectl` administration, dotfiles repository, local AIbot, Syncthing peer. |
| **Network Sentinel** (`raspberrypi`) | Single-board Computer (SBC) | Broadcom BCM2835<br>ARMv6l single-core @ 1.0 GHz | 512 MB LPDDR2 RAM<br>32 GB Class 10 MicroSD | **Raspberry Pi OS Lite**<br>(Debian Bullseye, 32-bit) | Wi-Fi: `192.168.1.20`<br>Tailscale: `100.64.0.20` | 24/7 Network Sentinel (ARP discovery & anti-flapping), Pi-hole DNS sinkhole across Tailscale mesh (< 1 Watt power draw). |
| **Mobile Endpoint** | Smartphone | Octa-Core Processor | 12 GB RAM<br>512 GB Storage | **Android 14 / 15** | Mobile 5G / Wi-Fi<br>Tailscale: `100.64.0.60` | Remote mobile terminal: Telegram bots interface, Obsidian Mobile vault, webapp browser access. |

> [!NOTE] Architectural Note on Raspberry Pi Zero W (ARMv6l)
> The Raspberry Pi Zero W utilizes the ARMv6l instruction set. Standard Kubernetes and K3s binaries require `armv7` or `aarch64` architectures; attempting to execute K3s on ARMv6 generates an `Illegal instruction` kernel fault. Consequently, the Pi Zero W operates as a dedicated, low-power IoT sentinel and DNS sinkhole, while the K3s cluster runs on the x86_64 server node.

---

## 3. Storage Hierarchy & Data Persistence

Workloads running inside the Kubernetes cluster achieve persistence via `hostPath` bindings mapped directly to the server filesystem under `/home/server/homelab-storage/`:

- **Nextcloud**: Application core files and document libraries (`nextcloud/html`) with ownership set to `www-data` (`UID:GID 33:33`).
- **Paperless-ngx**: Extracted metadata (`paperless/data`), original scanned media (`paperless/media`), automatic consumption directory (`paperless/consume`), and export archive (`paperless/export`).
- **Firefly III**: Relational database persistence under MariaDB 10.11 (`firefly/db_data`) with initial SQL schema import.
- **Monitoring**: Time-series metrics retention under Prometheus TSDB (`monitoring/prometheus_data`) and Grafana user dashboards (`monitoring/grafana_data`).
- **Homepage**: Declarative dashboard YAML declarations (`homepage/config`).
