#!/usr/bin/env python3
"""
IoT Network Sentinel Daemon
Periodically scans local wireless and wired segments, identifies connected hardware via ARP,
filters transient disconnects via anti-flapping algorithms, and alerts administrators via Telegram.
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
import logging
from typing import Dict, Set, Tuple

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("network-sentinel")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Configuration file not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()
BOT_TOKEN = CONFIG.get("bot_token", "").strip()
ALLOWED_USERS = set(int(uid) for uid in CONFIG.get("allowed_user_ids", []))
INTERFACE = CONFIG.get("interface", "wlan0")
SUBNET = CONFIG.get("subnet", "192.168.1.0/24")
SCAN_INTERVAL = int(CONFIG.get("scan_interval_seconds", 60))
GRACE_CYCLES = int(CONFIG.get("anti_flapping_grace_cycles", 10))
KNOWN_DEVICES = {k.upper(): v for k, v in CONFIG.get("known_devices", {}).items()}

# State: mac -> missed_cycles
missed_counts: Dict[str, int] = {}
active_devices: Dict[str, str] = {}  # mac -> ip


def send_telegram(chat_id: int, text: str):
    if not BOT_TOKEN:
        logger.warning(f"Telegram notification skipped (no token): {text}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


def notify_admins(text: str):
    for uid in ALLOWED_USERS:
        send_telegram(uid, text)


def perform_network_scan() -> Dict[str, str]:
    """Scans the subnet using arp-scan or falls back to /proc/net/arp."""
    results: Dict[str, str] = {}
    try:
        proc = subprocess.run(
            ["arp-scan", "--interface", INTERFACE, "--localnet", "-q"],
            capture_output=True,
            text=True,
            timeout=25
        )
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and ":" in parts[1]:
                ip, mac = parts[0], parts[1].upper()
                results[mac] = ip
    except (FileNotFoundError, subprocess.SubprocessError):
        # Fallback to kernel neighbor table
        try:
            with open("/proc/net/arp", "r", encoding="utf-8") as f:
                lines = f.readlines()[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                    ip, mac = parts[0], parts[3].upper()
                    results[mac] = ip
        except Exception as e:
            logger.error(f"ARP scan failed: {e}")
    return results


def run_cycle():
    global missed_counts, active_devices
    scanned = perform_network_scan()

    # Detect new arrivals
    for mac, ip in scanned.items():
        if mac not in active_devices:
            dev_name = KNOWN_DEVICES.get(mac, "Unknown Device (Untrusted)")
            status_icon = "🟢" if mac in KNOWN_DEVICES else "🚨 ALERT: Unknown Device"
            msg = f"{status_icon} *Device Connected*\n• *Name:* {dev_name}\n• *MAC:* `{mac}`\n• *IP:* `{ip}`"
            logger.info(f"Arrival: {mac} ({dev_name}) at {ip}")
            notify_admins(msg)
            active_devices[mac] = ip
        missed_counts[mac] = 0

    # Anti-flapping departed detection
    departed = []
    for mac, ip in list(active_devices.items()):
        if mac not in scanned:
            missed_counts[mac] = missed_counts.get(mac, 0) + 1
            if missed_counts[mac] >= GRACE_CYCLES:
                dev_name = KNOWN_DEVICES.get(mac, "Unknown Device")
                msg = f"⚪ *Device Disconnected*\n• *Name:* {dev_name}\n• *MAC:* `{mac}`\n• *Last IP:* `{ip}`"
                logger.info(f"Departure confirmed: {mac} ({dev_name}) after {GRACE_CYCLES} missed cycles")
                notify_admins(msg)
                departed.append(mac)

    for mac in departed:
        active_devices.pop(mac, None)
        missed_counts.pop(mac, None)


def main():
    logger.info("Starting IoT Network Sentinel daemon...")
    notify_admins("📡 *Network Sentinel Online*\nContinuous ARP monitoring initialized.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            logger.error(f"Error in scan loop: {e}")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
