#!/usr/bin/env bash
# TIZIM end-to-end smoke test. Markaziy stek + kamida bitta agent ko'tarilgan
# bo'lishi kerak (bootstrap-central.sh + enroll-agents.sh).
set -euo pipefail
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }

echo "== TIZIM E2E =="

# 1. Wazuh dashboard
code=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost:443 || true)
[ "$code" = "200" ] && pass "Wazuh dashboard ($code)" || fail "dashboard $code"

# 2. DefectDojo
code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login || true)
case "$code" in
  200|302) pass "DefectDojo ($code)";;
  *) fail "defectdojo $code";;
esac

# 3. Agent enrolled
TOKEN=$(curl -sk -u wazuh-wui:MyS3cr37P450r.*- -X POST \
  "https://localhost:55000/security/user/authenticate?raw=true")
agents=$(curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:55000/agents?select=name" | grep -c rocky-target || true)
[ "$agents" -ge 1 ] && pass "agent enrolled" || fail "agent topilmadi"

# 4. Orchestrator daily run prints a report
out=$(cd compose && docker compose run --rm orchestrator python -m app.main run-daily)
echo "$out" | grep -q "Jami zaiflik" && pass "kunlik hisobot ishladi" || fail "hisobot yo'q"

# 5. Mailhog received the email
msgs=$(curl -s http://localhost:8025/api/v2/messages | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])" || echo 0)
[ "$msgs" -ge 1 ] && pass "email mailhog'da ($msgs)" || fail "email yetmadi"

echo "== E2E yashil =="
