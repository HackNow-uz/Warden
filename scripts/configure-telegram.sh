#!/usr/bin/env bash
# compose/.env'dagi TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID bo'lsa, Wazuh manager
# L12+ alert integration hook_url'ini ulaydi. (Orchestrator kunlik hisobot Telegram'i
# allaqachon env-driven — bu skript faqat Wazuh real-vaqt alertini ulaydi.)
# Token bo'sh bo'lsa jimgina o'tkazib yuboradi — email kanali baribir ishlaydi.
set -euo pipefail
cd "$(dirname "$0")/.."
ENVF=compose/.env
CONF=compose/wazuh/config/wazuh_cluster/wazuh_manager.conf
[ -f "$ENVF" ] || exit 0

TOK=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENVF" 2>/dev/null | cut -d= -f2- || true)
CHAT=$(grep '^TELEGRAM_CHAT_ID=' "$ENVF" 2>/dev/null | cut -d= -f2- || true)
if [ -z "$TOK" ] || [ -z "$CHAT" ]; then
  echo "  TELEGRAM_BOT_TOKEN/CHAT_ID bo'sh — Wazuh Telegram alert o'tkazib yuborildi."
  exit 0
fi
# hook_url'ni o'rnatish (# delimiter — token : / belgilarini buzmaydi)
sed -i "s#<hook_url>.*</hook_url>#<hook_url>${TOK}|${CHAT}</hook_url>#" "$CONF"
echo "  Wazuh L12+ Telegram alert hook_url o'rnatildi (manager restart kerak)."
