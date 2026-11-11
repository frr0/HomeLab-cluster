# K3s Cluster Remote Telegram Bot

A lightweight, zero-dependency Python Telegram bot designed for remote cluster administration and observability.

## Key Capabilities

- **Workload Lifecycle Control**: Interactive inline keyboards to start, stop, or rolling-restart deployments in real time.
- **Power Management (`/power`)**: One-tap scale-to-zero for non-essential workloads to conserve memory and CPU, with one-tap restoration.
- **Live Pod Telemetry (`/pods`)**: Status badges (`🟢 Running`, `🟡 Pending`, `🔴 CrashLoopBackOff`), restart counts, and uptime.
- **Resource Metrics (`/top`)**: Real-time CPU and Memory consumption retrieved via the Kubernetes Metrics Server API.
- **Log Streaming (`/logs`)**: Immediate retrieval of container logs directly into chat.
- **Health Checks & App Routing (`/apps`)**: Automated HTTP health probing with direct LAN and WireGuard/Tailscale links.
- **Strict Access Control**: Enforces Telegram user ID whitelist; all unauthorized access attempts are rejected and logged.

## Configuration

Copy `config.example.json` to `config.json`:
```bash
cp config.example.json config.json
```

Populate the required configuration fields:
```json
{
  "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "allowed_user_ids": [123456789],
  "server_lan_ip": "192.168.1.100",
  "server_tailscale_ip": "100.64.0.10",
  "default_namespace": "homelab"
}
```

## Systemd Service Installation

```bash
# Enable user lingering for uninterrupted execution
loginctl enable-linger $USER

# Copy service definition
mkdir -p ~/.config/systemd/user/
cp cluster-bot.service.example ~/.config/systemd/user/cluster-bot.service

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable --now cluster-bot.service
systemctl --user status cluster-bot.service
```
