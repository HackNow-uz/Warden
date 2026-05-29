#!/usr/bin/env bash
# Wazuh indexer'da ISM retention policy yaratadi — wazuh-alerts-* indekslari
# RETENTION_DAYS (default 90) dan keyin avtomatik o'chiriladi (disk cheksiz o'smasin).
# Bootstrap'dan KEYIN, indexer ko'tarilgach ishlatiladi.
set -euo pipefail
cd "$(dirname "$0")/.."
ENVF=compose/.env
DAYS="${RETENTION_DAYS:-90}"
IDX_URL="${INDEXER_URL:-https://localhost:9200}"
PW=$(grep '^INDEXER_PASSWORD=' "$ENVF" 2>/dev/null | cut -d= -f2-)
USER=$(grep '^INDEXER_USER=' "$ENVF" 2>/dev/null | cut -d= -f2-); USER="${USER:-admin}"
CA="${CA_BUNDLE:-compose/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem}"
CACURL=( --cacert "$CA" ); [ -f "$CA" ] || CACURL=( -k )

read -r -d '' POLICY <<JSON || true
{
  "policy": {
    "description": "TIZIM: wazuh-alerts retention (${DAYS}d)",
    "default_state": "hot",
    "states": [
      {"name": "hot", "actions": [],
       "transitions": [{"state_name": "delete", "conditions": {"min_index_age": "${DAYS}d"}}]},
      {"name": "delete", "actions": [{"delete": {}}], "transitions": []}
    ],
    "ism_template": [{"index_patterns": ["wazuh-alerts-*", "wazuh-archives-*"], "priority": 100}]
  }
}
JSON

echo "ISM policy 'tizim-retention' (${DAYS} kun) o'rnatilmoqda..."
curl -s "${CACURL[@]}" -u "${USER}:${PW}" -X PUT \
  "${IDX_URL}/_plugins/_ism/policies/tizim-retention" \
  -H 'Content-Type: application/json' -d "$POLICY" -w "\nHTTP %{http_code}\n" | tail -3
echo "Eslatma: policy faqat YANGI indekslarga avto-biriktiriladi (ism_template)."
echo "Mavjudlariga: curl ... POST /_plugins/_ism/add/wazuh-alerts-* '{\"policy_id\":\"tizim-retention\"}'"
