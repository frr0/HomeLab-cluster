# Docker Compose Telegram Admin Bot

A lightweight, zero-dependency Python bot that provides mobile interactive control over standalone Docker Compose services.

## Features

- **Container Status Dashboard**: Real-time status indicators (`🟢 Running`, `🔴 Stopped`).
- **Inline Action Buttons**: Start, stop, or restart individual containers or entire stacks with a single tap.
- **Log Streaming**: Read live container log streams without opening SSH shells.
- **URL Generators**: Fast generation of direct LAN and WireGuard access links.

## Configuration

Copy `config.example.json` to `config.json` and set your credentials:
```bash
cp config.example.json config.json
```
