#!/usr/bin/env bash
# TIZIM — Wazuh DEMO parollarini kuchli tasodifiy parollar bilan almashtiradi.
#
# MAJBURIY: prod'dan oldin ishlatiladi. Wazuh single-node 3 ta demo cred bilan keladi:
#   admin / SecretPassword        (indexer; filebeat, dashboard, orchestrator ishlatadi)
#   wazuh-wui / MyS3cr37P450r.*-   (Wazuh API)
#   kibanaserver / kibanaserver    (dashboard -> indexer)
#
# Bu skript ENG SODDA va ishonchli — FRESH deploy'dan OLDIN (birinchi `docker compose up`gacha)
# ishlatiladi: indexer yangi parol bilan initsializatsiya bo'ladi, securityadmin kerak emas.
# Ishlab turgan stekda almashtirish uchun: docs/PROD-READINESS.md (securityadmin yo'li).
set -euo pipefail
cd "$(dirname "$0")/.."
WZVER="${WAZUH_VERSION:-4.9.2}"
DC="compose/wazuh/docker-compose.yml"
IU="compose/wazuh/config/wazuh_indexer/internal_users.yml"
WY="compose/wazuh/config/wazuh_dashboard/wazuh.yml"
ENVF="compose/.env"

[ -f "$ENVF" ] || { echo "XATO: $ENVF yo'q — avval .env.example'dan ko'chiring." >&2; exit 1; }

# Idempotentlik: demo parol allaqachon yo'q bo'lsa, to'xtaymiz
if ! grep -q "SecretPassword" "$DC"; then
  echo "Demo parol topilmadi — allaqachon rotatsiya qilingan ko'rinadi. To'xtatildi."
  exit 0
fi

gen() { openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 28; }
NEW_ADMIN=$(gen); NEW_API=$(gen); NEW_KIBANA=$(gen)
echo "[1/4] Kuchli parollar generatsiya qilindi (admin, API, kibanaserver)."

hash_pw() {
  docker run --rm wazuh/wazuh-indexer:"$WZVER" \
    bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p "$1" 2>/dev/null \
    | grep -E '^\$2' | tail -1
}
echo "[2/4] bcrypt hash hisoblanmoqda (indexer image tool)..."
ADMIN_HASH=$(hash_pw "$NEW_ADMIN")
KIBANA_HASH=$(hash_pw "$NEW_KIBANA")
[ -n "$ADMIN_HASH" ] && [ -n "$KIBANA_HASH" ] || { echo "XATO: hash generatsiya bo'lmadi (image bormi?)." >&2; exit 1; }

echo "[3/4] internal_users.yml hash'lar yangilanmoqda..."
python3 - "$IU" "$ADMIN_HASH" "$KIBANA_HASH" <<'PY'
import sys, yaml
path, ah, kh = sys.argv[1], sys.argv[2], sys.argv[3]
d = yaml.safe_load(open(path))
d["admin"]["hash"] = ah
d["kibanaserver"]["hash"] = kh
yaml.safe_dump(d, open(path, "w"), default_flow_style=False, sort_keys=False)
print("   admin + kibanaserver hash o'rnatildi")
PY

echo "[4/4] compose env, dashboard config va .env yangilanmoqda..."
# admin paroli (har joyda: manager, indexer, dashboard INDEXER_PASSWORD)
sed -i "s/SecretPassword/${NEW_ADMIN}/g" "$DC"
# API paroli (manager, dashboard, wazuh.yml) — '.' va '*' ni escape qilamiz
sed -i "s/MyS3cr37P450r\.\*-/${NEW_API}/g" "$DC" "$WY"
# kibanaserver paroli — FAQAT DASHBOARD_PASSWORD (USERNAME'ga tegmaymiz)
sed -i "s/DASHBOARD_PASSWORD=kibanaserver/DASHBOARD_PASSWORD=${NEW_KIBANA}/" "$DC"
# orchestrator/.env
sed -i "s/^INDEXER_PASSWORD=.*/INDEXER_PASSWORD=${NEW_ADMIN}/" "$ENVF"
sed -i "s/^WAZUH_API_PASSWORD=.*/WAZUH_API_PASSWORD=${NEW_API}/" "$ENVF"

echo
echo "[✓] Wazuh parollari rotatsiya qilindi. Demo parollar yo'q."
echo "    Endi FRESH deploy: bash scripts/bootstrap-central.sh"
echo "    (Parollar compose/.env va vendored config'da — repo'ga commit QILMANG.)"
