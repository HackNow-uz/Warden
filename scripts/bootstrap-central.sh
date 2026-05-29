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

echo "[4/6] Stacklarni tizim_net'ga ulash (TLS-mos service nomlari uchun)..."
IDX=$(cd compose/wazuh && docker compose ps -q wazuh.indexer)
MGR=$(cd compose/wazuh && docker compose ps -q wazuh.manager)
NGX=$(cd compose/defectdojo && docker compose ps -q nginx)
docker network connect --alias wazuh.indexer tizim_net "$IDX" 2>/dev/null || true
docker network connect --alias wazuh.manager tizim_net "$MGR" 2>/dev/null || true
docker network connect --alias nginx         tizim_net "$NGX" 2>/dev/null || true

echo "[5/6] orchestrator .env..."
[ -f compose/.env ] || cp compose/.env.example compose/.env

echo "[6/6] Orchestrator + mailhog..."
( cd compose && docker compose up -d --build )

echo
echo "Tayyor:"
echo "  Wazuh dashboard : https://localhost"
echo "  DefectDojo      : http://localhost:8080"
echo "  Mailhog (test)  : http://localhost:8025"
