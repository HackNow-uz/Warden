#!/usr/bin/env bash
# Markaziy stekni ko'taradi: Wazuh + DefectDojo + orchestrator, va ularni
# bitta `tizim_net` tarmog'iga (alias bilan) ulaydi.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[0/6] tizim_net tarmog'i..."
docker network create tizim_net >/dev/null 2>&1 || true

echo "[1/6] Wazuh sertifikatlari..."
( cd compose/wazuh && docker compose -f generate-indexer-certs.yml run --rm generator )

echo "[2/6] Wazuh single-node..."
( cd compose/wazuh && docker compose up -d )

echo "[3/6] DefectDojo..."
if [ ! -f compose/defectdojo/.env ]; then
  echo "  XATO: compose/defectdojo/.env yo'q." >&2
  echo "  .env.example'dan ko'chiring va majburiy kalitlarni to'ldiring." >&2
  exit 1
fi
( cd compose/defectdojo && docker compose up -d )

echo "[4/6] Tarmoq: docker-compose.override.yml fayllari indexer/manager/nginx'ni"
echo "      tizim_net'ga DEKLARATIV ulaydi (qo'lda connect kerak emas, restart-resilient)."

echo "[5/6] orchestrator .env..."
[ -f compose/.env ] || cp compose/.env.example compose/.env

echo "[6/6] Orchestrator + mailhog..."
( cd compose && docker compose up -d --build )

echo
echo "Tayyor:"
echo "  Wazuh dashboard : https://localhost"
echo "  DefectDojo      : http://localhost:8080"
echo "  Mailhog (test)  : http://localhost:8025"
