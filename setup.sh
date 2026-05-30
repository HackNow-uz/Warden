#!/usr/bin/env bash
# Warden — bir buyruqli o'rnatish.
#   git clone <repo> && cd Warden && ./setup.sh
# Bajaradi: preflight tekshiruv -> .env fayllar + DefectDojo sirlarini AVTO-generatsiya
#           -> bootstrap (Wazuh+DefectDojo+orchestrator).
# Sinov (bootstrap'siz, faqat tekshiruv+sirlar):  ./setup.sh --check
set -euo pipefail
cd "$(dirname "$0")"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'
ok(){   printf "  ${G}✓${N} %s\n" "$1"; }
warn(){ printf "  ${Y}!${N} %s\n" "$1"; }
die(){  printf "  ${R}✗ %s${N}\n" "$1" >&2; exit 1; }
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1

printf "${B}== Warden setup — preflight ==${N}\n"

# --- Docker ---
command -v docker >/dev/null 2>&1 || die "docker topilmadi — https://docs.docker.com/engine/install/"
docker compose version >/dev/null 2>&1 || die "docker compose (v2) topilmadi."
docker info >/dev/null 2>&1 || die "docker daemon ishlamayapti yoki ruxsat yo'q (sudo / docker guruh)."
ok "docker + compose"

# --- RAM ---
ram_gb=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 ))
if [ "$ram_gb" -lt 12 ]; then
  warn "RAM ${ram_gb} GB — to'liq stek uchun ~12 GB tavsiya (kam bo'lsa Wazuh va DefectDojo'ni navbatma-navbat sinang)"
else ok "RAM ${ram_gb} GB"; fi

# --- vm.max_map_count (Wazuh indexer) ---
mmc=$(cat /proc/sys/vm/max_map_count 2>/dev/null || echo 0)
if [ "$mmc" -lt 262144 ]; then
  if [ "$(id -u)" = "0" ]; then
    sysctl -w vm.max_map_count=262144 >/dev/null 2>&1 && ok "vm.max_map_count -> 262144 (o'rnatildi)" \
      || warn "vm.max_map_count=${mmc} — qo'lda: sysctl -w vm.max_map_count=262144"
  else
    warn "vm.max_map_count=${mmc} (indexer ≥262144 talab) — bajaring: sudo sysctl -w vm.max_map_count=262144"
  fi
else ok "vm.max_map_count=${mmc}"; fi

# --- Disk ---
disk_gb=$(df -BG . 2>/dev/null | awk 'NR==2{gsub(/G/,"",$4);print $4}' || echo 0)
if [ "${disk_gb:-0}" -lt 30 ]; then warn "bo'sh disk ${disk_gb} GB (≥30 GB tavsiya)"; else ok "disk ${disk_gb} GB bo'sh"; fi

# --- Portlar (localhost) ---
busy=""
for p in 8444 8888 9200 55000 1514 1515 8025; do
  if ss -tlnH 2>/dev/null | grep -q ":${p} "; then busy="$busy $p"; fi
done
if [ -n "$busy" ]; then warn "band portlar:${busy} — compose/.env (WAZUH_DASHBOARD_PORT) / defectdojo/.env (DD_PORT) da o'zgartiring"; else ok "kerakli portlar bo'sh"; fi

printf "${B}== env + maxfiy kalitlar ==${N}\n"
gen(){ openssl rand -base64 "$1" | tr -dc 'A-Za-z0-9' | head -c "$2"; }
# key faqat bo'sh yoki yo'q bo'lsa o'rnatadi (mavjudini buzmaydi)
set_secret(){ local key="$1" file="$2" val="$3"
  if grep -qE "^${key}=." "$file" 2>/dev/null; then return 1; fi   # allaqachon to'ldirilgan
  if grep -qE "^${key}=" "$file" 2>/dev/null; then sed -i "s|^${key}=.*|${key}=${val}|" "$file"; else echo "${key}=${val}" >> "$file"; fi
  return 0
}

[ -f compose/.env ] || { cp compose/.env.example compose/.env; ok "compose/.env yaratildi (example'dan)"; }
DDENV=compose/defectdojo/.env
[ -f "$DDENV" ] || { cp compose/defectdojo/.env.example "$DDENV"; ok "compose/defectdojo/.env yaratildi"; }

filled=0
set_secret DD_SECRET_KEY "$DDENV" "$(gen 50 50)" && filled=1 || true
set_secret DD_CREDENTIAL_AES_256_KEY "$DDENV" "$(gen 24 32)" && filled=1 || true
if ! grep -qE "^DD_DATABASE_PASSWORD=." "$DDENV" 2>/dev/null; then
  DBPASS=$(gen 24 24)
  sed -i "s|^DD_DATABASE_PASSWORD=.*|DD_DATABASE_PASSWORD=${DBPASS}|" "$DDENV"
  sed -i "s|^DD_DATABASE_URL=.*|DD_DATABASE_URL=postgresql://defectdojo:${DBPASS}@postgres:5432/defectdojo|" "$DDENV"
  filled=1
fi
if [ "$filled" = 1 ]; then ok "DefectDojo maxfiy kalitlari avto-generatsiya qilindi (qo'lda tahrir kerak emas)"
else ok "DefectDojo kalitlari allaqachon to'ldirilgan — tegilmadi"; fi
warn "Email/Telegram (ixtiyoriy): compose/.env'da SMTP_* / TELEGRAM_* to'ldiring (docs/GUIDE.md)"

if [ "$CHECK_ONLY" = 1 ]; then
  printf "${B}== --check: preflight + sirlar tayyor (bootstrap o'tkazib yuborildi) ==${N}\n"
  exit 0
fi

printf "${B}== bootstrap (bir necha daqiqa — image pull + stek) ==${N}\n"
bash scripts/bootstrap-central.sh
echo
ok "Warden tayyor! Keyingi: bash scripts/configure-retention.sh  (indexer retention)"
ok "Agentlar (RHEL): ansible/inventory.ini to'ldiring -> bash scripts/enroll-agents.sh"
