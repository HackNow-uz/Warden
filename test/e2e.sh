#!/usr/bin/env bash
# TIZIM end-to-end smoke test. Markaziy stek ko'tarilgan bo'lishi kerak.
# Portlar/parollar .env'dan o'qiladi (hardening: rotatsiya + localhost bind).
set -euo pipefail
cd "$(dirname "$0")/.."
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }
getenv() { grep -h "^$1=" "$2" 2>/dev/null | cut -d= -f2- | tail -1 || true; }

DASH_PORT=$(getenv WAZUH_DASHBOARD_PORT compose/.env); DASH_PORT=${DASH_PORT:-8444}
DD_PORT=$(getenv DD_PORT compose/defectdojo/.env);     DD_PORT=${DD_PORT:-8080}
API_PW=$(getenv WAZUH_API_PASSWORD compose/.env);      API_PW=${API_PW:-MyS3cr37P450r.*-}
SMTP_HOST=$(getenv SMTP_HOST compose/.env);            SMTP_HOST=${SMTP_HOST:-mailhog}

echo "== TIZIM E2E =="

# 1. Wazuh dashboard (localhost) — 302 = login redirect = sog'lom
code=$(curl -sk -o /dev/null -w "%{http_code}" "https://127.0.0.1:${DASH_PORT}" || true)
case "$code" in
  200|302) pass "Wazuh dashboard ($code)";;
  *) fail "dashboard $code";;
esac

# 2. DefectDojo (localhost)
code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${DD_PORT}/login" || true)
case "$code" in
  200|302) pass "DefectDojo ($code)";;
  *) fail "defectdojo $code";;
esac

# 3. Agent (ixtiyoriy — fleet enroll qilinmagan bo'lsa skip)
TOKEN=$(curl -sk -u "wazuh-wui:${API_PW}" -X POST \
  "https://127.0.0.1:55000/security/user/authenticate?raw=true" || true)
agents=$(curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://127.0.0.1:55000/agents?select=id" \
  | python3 -c "import sys,json;print(sum(1 for a in json.load(sys.stdin)['data']['affected_items'] if a['id']!='000'))" 2>/dev/null || echo 0)
if [ "$agents" -ge 1 ]; then pass "agent enrolled ($agents)"; else echo "ℹ️  agent yo'q (fleet ixtiyoriy)"; fi

# 4. Orchestrator kunlik sikl
out=$(cd compose && docker compose run --rm orchestrator python -m app.main run-daily)
echo "$out" | grep -q "Jami zaiflik" && pass "kunlik hisobot ishladi" || fail "hisobot yo'q"

# 5. Email yetkazish
if [ "$SMTP_HOST" = "mailhog" ]; then
  msgs=$(curl -s "http://127.0.0.1:8025/api/v2/messages" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])" 2>/dev/null || echo 0)
  [ "$msgs" -ge 1 ] && pass "email mailhog'da ($msgs)" || fail "email yetmadi"
else
  pass "hisobot real SMTP ($SMTP_HOST) orqali yuborildi (run exit 0)"
fi

echo "== E2E yashil =="
