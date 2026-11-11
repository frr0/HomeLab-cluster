#!/usr/bin/env python3
"""
HomeLab Docker Telegram Bot
Lightweight Telegram bot using Python standard library to monitor and manage Docker containers.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import subprocess
import logging

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("admin-bot")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Config file not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


CONFIG = load_config()
BOT_TOKEN = CONFIG.get("bot_token", "").strip()
WEBAPP_DIR = CONFIG.get("webapp_dir", "/home/workstation/HomeLab-cluster/docker")
ALLOWED_USER_IDS = set(int(uid) for uid in CONFIG.get("allowed_user_ids", [123456789]))

# WebApp registry: Container to Web UI mapping
KNOWN_WEBAPPS = {
    "homepage": {"port": 30050, "protocol": "http", "label": "Homepage"},
    "portainer": {"port": 9000, "protocol": "http", "label": "Portainer"},
    "adguard-home": {"port": 8080, "protocol": "http", "label": "AdGuard Home"},
    "adguard": {"port": 8080, "protocol": "http", "label": "AdGuard Home"},
    "nextcloud": {"port": 30080, "protocol": "http", "label": "Nextcloud"},
    "paperless-web": {"port": 30082, "protocol": "http", "label": "Paperless-ngx"},
    "paperless": {"port": 30082, "protocol": "http", "label": "Paperless-ngx"},
    "firefly-app": {"port": 30090, "protocol": "http", "label": "Firefly III"},
    "firefly": {"port": 30090, "protocol": "http", "label": "Firefly III"},
    "firefly-importer": {"port": 30091, "protocol": "http", "label": "Firefly Importer"},
    "grafana": {"port": 30030, "protocol": "http", "label": "Grafana"},
    "prometheus": {"port": 9090, "protocol": "http", "label": "Prometheus"},
}


def get_server_host():
    """Retrieve host/IP used to access web applications."""
    conf = load_config()
    if conf.get("server_host"):
        return conf["server_host"].strip()

    # Fallback: check TAILSCALE_IP in Webapp/.env
    env_path = os.path.join(WEBAPP_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TAILSCALE_IP=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception as e:
            logger.debug(f"Could not read .env: {e}")

    return "localhost"


def get_container_webapp(container_name):
    """Return webapp information (URL and label) if the container provides a web interface."""
    conf = load_config()
    server_host = get_server_host()

    # 1. Custom overrides from config.json
    custom = conf.get("custom_webapps", {})
    if container_name in custom:
        item = custom[container_name]
        if isinstance(item, str):
            url = item.replace("{host}", server_host)
            return {"url": url, "label": container_name}
        elif isinstance(item, dict):
            port = item.get("port")
            protocol = item.get("protocol", "http")
            label = item.get("label", container_name)
            url = item.get("url", f"{protocol}://{server_host}:{port}")
            return {"url": url, "label": label}

    # 2. Known webapps dictionary
    c_clean = container_name.lower().strip()
    if c_clean in KNOWN_WEBAPPS:
        info = KNOWN_WEBAPPS[c_clean]
        url = f"{info['protocol']}://{server_host}:{info['port']}"
        return {"url": url, "label": info["label"]}

    # Avoid matching databases or non-webapp workers
    skip_keywords = ["db", "database", "redis", "mysql", "mariadb", "postgres", "data-fetch", "exporter"]
    if any(k in c_clean for k in skip_keywords):
        return None

    # Substring / partial matching
    for key, info in KNOWN_WEBAPPS.items():
        if key in c_clean:
            url = f"{info['protocol']}://{server_host}:{info['port']}"
            return {"url": url, "label": info["label"]}

    return None


def get_all_webapps():
    """Retrieve all webapps along with their current container running state."""
    containers = {c["name"]: c for c in get_containers()}
    order = [
        "homepage",
        "portainer",
        "nextcloud",
        "paperless-web",
        "firefly-app",
        "firefly-importer",
        "adguard-home",
        "grafana",
        "prometheus"
    ]
    webapps = []
    seen = set()

    for name in order:
        webapp = get_container_webapp(name)
        if webapp:
            seen.add(name)
            c_info = containers.get(name)
            is_running = (c_info["state"] == "running") if c_info else False
            webapps.append({
                "container_name": name,
                "label": webapp["label"],
                "url": webapp["url"],
                "is_running": is_running
            })

    # Add any extra containers that have a webapp configured
    for c_name, c_info in containers.items():
        if c_name not in seen:
            webapp = get_container_webapp(c_name)
            if webapp:
                seen.add(c_name)
                webapps.append({
                    "container_name": c_name,
                    "label": webapp["label"],
                    "url": webapp["url"],
                    "is_running": c_info["state"] == "running"
                })

    return webapps


def is_user_allowed(user_id):
    try:
        return int(user_id) in ALLOWED_USER_IDS
    except (ValueError, TypeError):
        return False


def telegram_api(method, payload=None, timeout=35):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Telegram API Error ({method}): {e.code} - {err_msg}")
        return None
    except Exception as e:
        logger.error(f"Network error in {method}: {e}")
        return None


def get_host_stats():
    # CPU Load
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()[:3]
            load_str = " ".join(load)
    except Exception:
        load_str = "N/A"

    # RAM
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem = {}
        for l in lines:
            parts = l.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        total_mb = mem.get("MemTotal", 0) // 1024
        avail_mb = mem.get("MemAvailable", 0) // 1024
        used_mb = total_mb - avail_mb
        ram_pct = int((used_mb / total_mb) * 100) if total_mb else 0
        ram_str = f"{used_mb}MB / {total_mb}MB ({ram_pct}%)"
    except Exception:
        ram_str = "N/A"

    # Disk
    try:
        st = os.statvfs("/")
        total_gb = (st.f_blocks * st.f_frsize) / (1024 ** 3)
        avail_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)
        used_gb = total_gb - avail_gb
        disk_pct = int((used_gb / total_gb) * 100) if total_gb else 0
        disk_str = f"{used_gb:.1f}GB / {total_gb:.1f}GB ({disk_pct}%)"
    except Exception:
        disk_str = "N/A"

    return f"🧠 *RAM:* {ram_str}\n📊 *Carico (1/5/15m):* `{load_str}`\n💾 *Disco:* {disk_str}"


def get_webapp_services():
    """Retrieve all services defined in the Webapp docker-compose setup."""
    try:
        res = subprocess.run(
            ["docker", "compose", "config", "--services"],
            capture_output=True,
            text=True,
            cwd=WEBAPP_DIR,
            timeout=10
        )
        if res.returncode == 0:
            services = [s.strip() for s in res.stdout.strip().split("\n") if s.strip()]
            if services:
                return services
    except Exception as e:
        logger.debug(f"Error querying docker compose services: {e}")

    # Fallback to predefined list if compose command fails
    return [
        "homepage", "portainer", "nextcloud", "paperless-web", "paperless-redis",
        "firefly-app", "firefly-db", "firefly-importer", "adguard-home",
        "grafana", "prometheus", "node-exporter", "influxdb", "garmin-fetch-data"
    ]


def get_containers():
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        existing = {}
        if res.returncode == 0:
            for line in res.stdout.strip().split("\n"):
                if line:
                    try:
                        c = json.loads(line)
                        name = c.get("Names", "unknown")
                        existing[name] = {
                            "name": name,
                            "status": c.get("Status", ""),
                            "state": c.get("State", "").lower(),
                            "image": c.get("Image", ""),
                            "ports": c.get("Ports", ""),
                            "is_homelab": False
                        }
                    except Exception:
                        pass

        webapp_services = get_webapp_services()
        containers = []
        seen = set()

        # Preferred display order for HomeLab services
        priority_order = [
            "homepage", "portainer", "nextcloud", "paperless-web", "paperless-redis",
            "firefly-app", "firefly-db", "firefly-importer", "adguard-home",
            "grafana", "prometheus", "node-exporter", "influxdb", "garmin-fetch-data"
        ]

        ordered_homelab = []
        for s in priority_order:
            if s in webapp_services and s not in ordered_homelab:
                ordered_homelab.append(s)
        for s in webapp_services:
            if s not in ordered_homelab:
                ordered_homelab.append(s)

        for s in ordered_homelab:
            seen.add(s)
            if s in existing:
                item = existing[s]
                item["is_homelab"] = True
                containers.append(item)
            else:
                containers.append({
                    "name": s,
                    "status": "Fermo (down)",
                    "state": "down",
                    "image": "",
                    "ports": "",
                    "is_homelab": True
                })

        # Add any other non-homelab containers from docker ps -a
        for name, item in sorted(existing.items()):
            if name not in seen:
                containers.append(item)

        return containers
    except Exception as e:
        logger.error(f"Error querying docker: {e}")
        return []


def run_command(cmd, cwd=None, timeout=45):
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        out = (res.stdout + "\n" + res.stderr).strip()
        return res.returncode == 0, out
    except Exception as e:
        return False, str(e)


def build_main_menu():
    containers = get_containers()
    stats = get_host_stats()
    text = f"🖥️ *HomeLab Docker Controller*\n\n{stats}\n\n*Container Attivi:* {sum(1 for c in containers if c['state'] == 'running')}/{len(containers)}\n\n_Seleziona un container per gestirlo:_"

    keyboard = []
    row = []
    for c in containers:
        icon = "🟢" if c["state"] == "running" else "🔴"
        name = c["name"]
        btn = {"text": f"{icon} {name}", "callback_data": f"select:{name}"}
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Actions row
    keyboard.append([
        {"text": "🌐 Elenco Web App", "callback_data": "webapps_list"},
        {"text": "🔄 Aggiorna Stato", "callback_data": "refresh"}
    ])
    keyboard.append([
        {"text": "🚀 Avvia Tutto", "callback_data": "compose_start"},
        {"text": "🛑 Ferma Tutto", "callback_data": "compose_stop"}
    ])

    return text, {"inline_keyboard": keyboard}


def build_webapps_view():
    webapps = get_all_webapps()
    text = "🌐 *Web App del tuo HomeLab*\n\n"
    if not webapps:
        text += "_Nessuna web app rilevata o configurata._"
        return text, {"inline_keyboard": [[{"text": "🔙 Torna al Menu", "callback_data": "menu"}]]}

    text += "Tocca un pulsante per aprire direttamente la Web App nel browser:\n\n"
    keyboard = []

    for item in webapps:
        icon = "🟢" if item["is_running"] else "🔴"
        status_str = "Attivo" if item["is_running"] else "Fermo"
        text += f"{icon} *{item['label']}* ({status_str})\n"
        text += f"   🔗 `{item['url']}`\n\n"
        # Pulsante inline di tipo URL che apre il browser
        keyboard.append([{"text": f"{icon} Apri {item['label']}", "url": item["url"]}])

    keyboard.append([{"text": "🔄 Aggiorna", "callback_data": "webapps_list"}])
    keyboard.append([{"text": "🔙 Torna al Menu", "callback_data": "menu"}])

    return text, {"inline_keyboard": keyboard}


def build_container_view(container_name):
    containers = get_containers()
    target = next((c for c in containers if c["name"] == container_name), None)
    webapp_info = get_container_webapp(container_name)

    if not target:
        msg = f"❌ Container `{container_name}` non trovato."
        kb = []
        if webapp_info:
            msg += f"\n\n🌐 *Web App associata:* [{webapp_info['label']}]({webapp_info['url']})"
            kb.append([{"text": f"🌐 Apri {webapp_info['label']}", "url": webapp_info["url"]}])
        kb.append([{"text": "🔙 Torna al Menu", "callback_data": "menu"}])
        return msg, {"inline_keyboard": kb}

    icon = "🟢" if target["state"] == "running" else "🔴"
    text = (
        f"📦 *Container:* `{target['name']}`\n"
        f"🏷️ *Stato:* {icon} `{target['status']}`\n"
        f"🖼️ *Immagine:* `{target['image']}`\n"
    )
    if target["ports"]:
        text += f"🔌 *Porte:* `{target['ports']}`\n"
    if webapp_info:
        text += f"🌐 *Web App:* [{webapp_info['label']}]({webapp_info['url']})\n"
        text += f"🔗 *URL:* `{webapp_info['url']}`\n"

    keyboard = []
    # If container has an associated webapp, add the direct URL button on top
    if webapp_info:
        keyboard.append([
            {"text": f"🌐 Apri {webapp_info['label']}", "url": webapp_info["url"]}
        ])

    keyboard.append([
        {"text": "▶️ Avvia", "callback_data": f"start:{container_name}"},
        {"text": "⏹️ Ferma", "callback_data": f"stop:{container_name}"},
        {"text": "🔄 Riavvia", "callback_data": f"restart:{container_name}"}
    ])
    keyboard.append([
        {"text": "📋 Log (ultime righe)", "callback_data": f"logs:{container_name}"}
    ])
    keyboard.append([
        {"text": "🔙 Torna alla Lista", "callback_data": "menu"}
    ])

    return text, {"inline_keyboard": keyboard}


def handle_callback_query(cq):
    cq_id = cq["id"]
    from_user = cq["from"]["id"]
    data = cq.get("data", "")
    msg = cq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    if not is_user_allowed(from_user):
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "⛔ Accesso non autorizzato!", "show_alert": True})
        return

    if data == "menu" or data == "refresh":
        text, reply_markup = build_main_menu()
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Aggiornato!"})

    elif data == "webapps_list":
        text, reply_markup = build_webapps_view()
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id})

    elif data.startswith("select:"):
        c_name = data.split(":", 1)[1]
        text, reply_markup = build_container_view(c_name)
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id})

    elif data.startswith("start:"):
        c_name = data.split(":", 1)[1]
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": f"Avvio di {c_name}..."})
        success, out = run_command(f"docker start {c_name}")
        if not success:
            logger.info(f"docker start {c_name} non riuscito ({out}). Tento docker compose up -d {c_name}...")
            run_command(f"docker compose up -d {c_name}", cwd=WEBAPP_DIR)
        time.sleep(1.5)
        text, reply_markup = build_container_view(c_name)
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif data.startswith("stop:"):
        c_name = data.split(":", 1)[1]
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": f"Arresto di {c_name}..."})
        run_command(f"docker stop {c_name}")
        time.sleep(1)
        text, reply_markup = build_container_view(c_name)
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif data.startswith("restart:"):
        c_name = data.split(":", 1)[1]
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": f"Riavvio di {c_name}..."})
        success, out = run_command(f"docker restart {c_name}")
        if not success:
            logger.info(f"docker restart {c_name} non riuscito ({out}). Tento docker compose up -d {c_name}...")
            run_command(f"docker compose up -d --force-recreate {c_name}", cwd=WEBAPP_DIR)
        time.sleep(1.5)
        text, reply_markup = build_container_view(c_name)
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif data.startswith("logs:"):
        c_name = data.split(":", 1)[1]
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Recupero log..."})
        success, logs = run_command(f"docker logs --tail 25 {c_name}")
        if not success or not logs:
            logs = "Nessun log disponibile o container non ancora creato/avviato."
        # Limit text length for telegram
        if len(logs) > 3000:
            logs = logs[-3000:]
        text = f"📋 *Ultimi Log di* `{c_name}`:\n\n```\n{logs}\n```"
        keyboard = [
            [{"text": "🔄 Aggiorna Log", "callback_data": f"logs:{c_name}"}],
            [{"text": f"🔙 Torna a {c_name}", "callback_data": f"select:{c_name}"}],
            [{"text": "🏠 Menu Principale", "callback_data": "menu"}]
        ]
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": keyboard}
        })

    elif data == "compose_start":
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Avvio di tutte le webapp in corso...", "show_alert": True})
        manage_script = os.path.join(WEBAPP_DIR, "manage.sh")
        if os.path.exists(manage_script):
            run_command(f"{manage_script} start", cwd=WEBAPP_DIR)
        else:
            run_command("docker compose up -d", cwd=WEBAPP_DIR)
        time.sleep(2)
        text, reply_markup = build_main_menu()
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif data == "compose_stop":
        telegram_api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Arresto di tutte le webapp in corso...", "show_alert": True})
        manage_script = os.path.join(WEBAPP_DIR, "manage.sh")
        if os.path.exists(manage_script):
            run_command(f"{manage_script} stop", cwd=WEBAPP_DIR)
        else:
            run_command("docker compose stop", cwd=WEBAPP_DIR)
        time.sleep(2)
        text, reply_markup = build_main_menu()
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })


def handle_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    from_user = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()

    if not is_user_allowed(from_user):
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": f"⛔ *Accesso Negato.*\nIl tuo ID utente `{from_user}` non è autorizzato ad inviare comandi a questo server.",
            "parse_mode": "Markdown"
        })
        return

    if text in ["/start", "/menu", "menu", "status"]:
        menu_text, reply_markup = build_main_menu()
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": menu_text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif text in ["/webapps", "/links", "webapps", "links"]:
        webapps_text, reply_markup = build_webapps_view()
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": webapps_text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })

    elif text == "/stats":
        stats = get_host_stats()
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": f"🖥️ *Statistiche Host:*\n\n{stats}",
            "parse_mode": "Markdown"
        })

    else:
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": "👋 Comandi disponibili:\n• /menu - Visualizza i container e le azioni\n• /webapps - Elenco dei link a tutte le webapp\n• /stats - Statistiche di carico host",
            "parse_mode": "Markdown"
        })


def main():
    if not BOT_TOKEN or BOT_TOKEN == "INSERISCI_IL_TUO_BOT_TOKEN_QUI":
        logger.error("Token Telegram mancante in config.json! Inserisci il token creato con @BotFather.")
        print("\n[ERRORE] Inserisci il tuo Bot Token in config.json!\n")
        return

    logger.info("Verifica connessione con Telegram...")
    me = telegram_api("getMe")
    if not me or not me.get("ok"):
        logger.error("Token non valido o impossibile contattare Telegram.")
        return

    bot_name = me["result"]["first_name"]
    bot_username = me["result"].get("username", "")
    logger.info(f"Bot avviato con successo: @{bot_username} ({bot_name})")

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            updates = telegram_api("getUpdates", params, timeout=40)
            if updates and updates.get("ok"):
                for u in updates["result"]:
                    offset = u["update_id"] + 1
                    if "message" in u:
                        handle_message(u["message"])
                    elif "callback_query" in u:
                        handle_callback_query(u["callback_query"])
        except KeyboardInterrupt:
            logger.info("Bot interrotto dall'utente.")
            break
        except Exception as e:
            logger.error(f"Eccezione nel ciclo principale: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
