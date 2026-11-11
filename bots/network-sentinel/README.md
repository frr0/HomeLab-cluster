# IoT Network Sentinel (Raspberry Pi Zero W)

A lightweight 24/7 network watchdog running on ARMv6 (Raspberry Pi Zero W) that continuously monitors the domestic Wi-Fi and LAN segment, tracks connected endpoints, and notifies administrators of unauthorized devices or presence events.

## Architecture & Features

- **Continuous ARP Discovery**: Scans the network without pinging overhead using `arp-scan` or direct Linux `/proc/net/arp` extraction.
- **Anti-Flapping Filter with Grace Period**: Modern mobile operating systems enter aggressive Wi-Fi power-save modes when locked, briefly dropping from scan results. The sentinel enforces a configurable grace period (default: 10 missed scan cycles) before marking a device offline, eliminating false alarm chatter.
- **Intrusion Alerts**: Devices whose MAC addresses do not match the trusted whitelist (`known_devices`) trigger an immediate high-priority warning alert to the Telegram admin channel.
- **Ultra-Low Resource Footprint**: Consumes < 15 MB of RAM and negligible CPU on single-core 1.0 GHz ARMv6 hardware (power draw < 1 Watt).

## Configuration

Copy `config.example.json` to `config.json` and adjust the interface, subnet, and device whitelist:
```bash
cp config.example.json config.json
```

## Systemd Service Setup

```bash
sudo cp sentinel.service.example /etc/systemd/system/sentinel.service
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel.service
sudo systemctl status sentinel.service
```
