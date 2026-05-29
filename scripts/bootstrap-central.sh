#!/usr/bin/env bash
# Markaziy stekni ko'taradi: Wazuh + DefectDojo + orchestrator.
# Tarmoq deklarativ (docker-compose.override.yml fayllari tizim_net'ga ulaydi).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/7] tizim_net tarmog'i..."
docker network create tizim_net >/dev/null 2>&1 || true

echo "[2/7] env fayllar..."
[ -f compose/.env ] || cp compose/.env.example compose/.env
if [ ! -f compose/defectdojo/.env ]; then
  echo "  XATO: compose/defectdojo/.env yo'q — .env.example'dan ko'chiring va" >&2
  echo "        MAJBURIY maxfiy kalitlarni to'ldiring (DD_SECRET_KEY, AES, DB parol)." >&2
  exit 1
fi

echo "[3/7] Wazuh DEMO parollarini rotatsiya (kuchli tasodifiy)..."
bash scripts/gen-wazuh-secrets.sh
bash scripts/configure-telegram.sh   # .env'da TELEGRAM_* bo'lsa alertni ulaydi

echo "[4/7] Wazuh sertifikatlari..."
( cd compose/wazuh && docker compose -f generate-indexer-certs.yml run --rm generator )

echo "[5/7] Wazuh single-node (override tizim_net'ga ulaydi)..."
( cd compose/wazuh && docker compose up -d )

echo "[6/7] DefectDojo..."
( cd compose/defectdojo && docker compose up -d )

echo "[7/7] Orchestrator + mailhog..."
( cd compose && docker compose up -d --build )

echo
echo "Tayyor. Kirish faqat localhost (xavfsizlik) — SSH tunnel orqali:"
echo "  Wazuh dashboard : https://localhost:443"
echo "  DefectDojo      : http://localhost:8080"
echo "  Mailhog (sinov) : http://localhost:8025"
echo "Eslatma: agentlar -> bash scripts/enroll-agents.sh (inventory.ini to'ldirilgach)"
