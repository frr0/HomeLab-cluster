#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
  else
    echo "❌ Error: Neither .env nor .env.example found."
    exit 1
  fi
fi

cmd="${1:-status}"

case "${cmd}" in
  start|up)
    target="${2:-}"
    if [[ -z "${target}" ]]; then
      echo "🚀 Starting all HomeLab containers..."
      docker compose up -d
    else
      echo "🚀 Starting service: ${target}..."
      docker compose up -d "${target}"
    fi
    ;;

  stop|down)
    target="${2:-}"
    if [[ -z "${target}" ]]; then
      echo "🛑 Stopping all HomeLab containers..."
      docker compose down
    else
      echo "🛑 Stopping service: ${target}..."
      docker compose stop "${target}"
    fi
    ;;

  restart)
    target="${2:-}"
    if [[ -z "${target}" ]]; then
      echo "🔄 Restarting all HomeLab containers..."
      docker compose restart
    else
      echo "🔄 Restarting service: ${target}..."
      docker compose restart "${target}"
    fi
    ;;

  status|ps)
    echo "📊 Container Status:"
    docker compose ps
    ;;

  logs)
    target="${2:-}"
    if [[ -z "${target}" ]]; then
      docker compose logs -f --tail=50
    else
      docker compose logs -f --tail=50 "${target}"
    fi
    ;;

  *)
    echo "Usage: $0 {start|stop|restart|status|logs} [service-name]"
    exit 1
    ;;
esac
