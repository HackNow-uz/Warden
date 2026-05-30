# Warden — Production Readiness

Ushbu hujjat Warden'ni haqiqiy production muhitga chiqarish uchun hardening holatini,
operator checklist'ini, deploy runbook'ini va xavfsizlik posturasini bayon qiladi.

> **Holat:** Barcha kritik va muhim kamchiliklar repo darajasida yopildi (quyida).
> Production deploy uchun operator faqat o'z muhit-spetsifik qiymatlarini beradi
> (serverlar, SSH kalit, ixtiyoriy Telegram token) va checklist'ni bajaradi.

---

## 1. Yopilgan kamchiliklar (hardening)

| # | Kamchilik | Yechim | Fayl |
|---|---|---|---|
| KRITIK-1 | Wazuh DEMO parollari | `gen-wazuh-secrets.sh` — admin/API/kibanaserver parollarini kuchli tasodifiyga almashtiradi + internal_users.yml hash'lari; bootstrap avtomatik chaqiradi | `scripts/gen-wazuh-secrets.sh` |
| KRITIK-2 | Telegram alert ulanmagan | `configure-telegram.sh` — `.env`dagi `TELEGRAM_*`dan hook_url'ni ulaydi (config-driven, token hardcode emas) | `scripts/configure-telegram.sh` |
| KRITIK-3 | Tarmoq glue mo'rt (qo'lda connect) | `docker-compose.override.yml` — indexer/manager/nginx `tizim_net`'ga DEKLARATIV ulanadi, restart-resilient | `compose/*/docker-compose.override.yml` |
| KRITIK-4 | OpenSCAP tekshirilmagan / datastream qattiq | Role distro bo'yicha datastream'ni AUTO aniqlaydi (Rocky/Alma/RHEL/CentOS) | `ansible/roles/openscap/` |
| MUHIM | Agentlar — parol auth, soxta target | Prod inventar SSH-kalit + ansible-vault; `enroll-agents.sh` real inventar talab qiladi | `ansible/inventory.ini.example` |
| MUHIM | Retention yo'q (disk o'sadi) | Wazuh ISM policy — `wazuh-alerts-*` N kundan keyin o'chadi | `scripts/configure-retention.sh` |
| MUHIM | Backup yo'q | DefectDojo Postgres + media backup + rotation | `scripts/backup-defectdojo.sh` |
| MUHIM | Resurs limiti yo'q | Har konteynerda `mem_limit`/`cpus` (shared host himoyasi) | override + top compose |
| MUHIM | docker.sock (host-root) | Olib tashlandi — Trivy/Grype registry'dan pull qiladi | `compose/docker-compose.yml` |
| MUHIM | Tashqi ekspozitsiya | Barcha port localhost-bound; SSH tunnel/VPN posturasi (3-bo'lim) | compose ports |
| OPS | Silent failure | `run_daily` try/except → alert; heartbeat dead-man's-switch | `app/main.py` |
| OPS | Log o'sishi | cron → docker stdout + json-file rotation (10m×3) | crontab + compose |
| OPS | CI yo'q | GitHub Actions: pytest + compose + ansible + bash | `.github/workflows/ci.yml` |
| OPS | Maxfiy kalitlar | DefectDojo kalitlari majburiy (`${VAR:?}`); TLS verify hech qachon o'chmaydi (CA) | compose + orchestrator |

## 2. Production deploy runbook (fresh)

```bash
# 1. Repo va env
git clone <tizim-repo> /opt/Warden && cd /opt/Warden
cp compose/.env.example compose/.env
cp compose/defectdojo/.env.example compose/defectdojo/.env

# 2. DefectDojo maxfiy kalitlari (MAJBURIY)
#    compose/defectdojo/.env ichida to'ldiring:
python -c 'import secrets;print(secrets.token_urlsafe(50))'   # DD_SECRET_KEY
openssl rand -base64 24                                        # DD_CREDENTIAL_AES_256_KEY
openssl rand -base64 24                                        # DD_DATABASE_PASSWORD (+ DD_DATABASE_URL'ga moslang)

# 3. (ixtiyoriy) Telegram + heartbeat — compose/.env:
#    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HEARTBEAT_URL
#    SMTP (real): SMTP_HOST/PORT/USER/PASSWORD/FROM/TO + SMTP_TLS=true

# 4. Markaziy stek (parol rotatsiya + telegram + certs + up — hammasi avtomatik)
bash scripts/bootstrap-central.sh

# 5. Retention policy (indexer ko'tarilgach)
RETENTION_DAYS=90 bash scripts/configure-retention.sh

# 6. Agentlar (RHEL serverlar)
cp ansible/inventory.ini.example ansible/inventory.ini   # real serverlar + SSH kalit
bash scripts/enroll-agents.sh

# 7. Backup cron (host crontab)
echo "0 3 * * * cd /opt/Warden && WARDEN_BACKUP_DIR=/var/backups/tizim bash scripts/backup-defectdojo.sh" | crontab -

# 8. Tekshiruv
bash test/e2e.sh
```

## 3. Xavfsizlik posturasi (access / TLS)

**Default (tavsiya): internal-only.** Wazuh dashboard, DefectDojo, mailhog faqat
`127.0.0.1`'ga bind qilingan — internetga ochiq emas. Bu xavfsizlik monitoring
vositasi uchun to'g'ri posture (Wazuh/DefectDojo'ni public qilish — keng tarqalgan xato).

Kirish usullari (operator tanlovi):
1. **SSH tunnel** (eng sodda): `ssh -L 8444:127.0.0.1:443 -L 8888:127.0.0.1:8080 user@host`
2. **VPN** (WireGuard/Tailscale) — internal tarmoqqa kirish.
3. **Reverse proxy + TLS** (bitta HTTPS kirish nuqtasi kerak bo'lsa): old nginx/traefik,
   Let's Encrypt sertifikat, basic-auth yoki SSO. Buni qo'shsangiz, dashboardni faqat
   reverse-proxy ko'radigan internal portga qoldiring, public'ga to'g'ridan chiqarmang.

Ichki TLS: Wazuh self-signed CA bilan ishlaydi; orchestrator o'sha CA'ga qarshi
**tekshiradi** (`verify=False` ishlatilmaydi).

## 4. Topilmalarni reconciliation (dedup)

- **Re-run dedup:** orchestrator har skanни DefectDojo'ga `close_old_findings=true` bilan
  yuboradi — eski (endi yo'q) topilmalar avtomatik yopiladi, takror o'smaydi.
- **Cross-scanner (Wazuh ↔ Trivy bir CVE):** DefectDojo System Settings → "Deduplicate
  findings" yoqing (yoki `DD_ENABLE_DEDUPLICATION`). Per-engagement ajratilgani uchun
  bir manba topilmasi ikkinchisini bekor qilmaydi; dedup hash CVE+paket bo'yicha birlashtiradi.
- Hisobot (email) barcha manbalarni jamlaydi; DefectDojo trend/holatni saqlaydi.

## 5. OS-paket CVE aniqlash — tekshiruv eslatmasi

Wazuh OS-paket CVE moduli to'g'ri sozlangan va ishlaydi: feed yuklanadi (~5.6 GB),
agent inventari (Syscollector, masalan 166 paket) bildiriladi, scanner ishlaydi.
Sinov muhitida (yangi, to'liq patched minimal Rocky 9.7) natija 0 bo'lishi mumkin —
bu legitim (barcha paket tuzatilgan versiyada). **Production'da real serverlarda
OS CVE'lar to'ladi.**

⚠️ Pipeline'ni isbotlash kerak bo'lsa, buni **alohida test VM'da** qiling
(prod hostida emas): ataylab eski/zaif paket o'rnatib, Wazuh aniqlashini kuzating.
Trivy/Grype image skani (1600+ topilma) image qatlamidagi CVE'larni qoplaydi.

## 6. Operatsiya
- **Backup:** `backup-defectdojo.sh` kunlik cron (DB+media, 14 kun rotation).
- **Retention:** `configure-retention.sh` (wazuh-alerts ${RETENTION_DAYS}d).
- **Monitoring-of-monitor:** `HEARTBEAT_URL` (healthchecks.io) — kunlik sikl ishlamasa tashqi alert.
- **Loglar:** docker json-file (10m×3) avto-rotation.
- **Upgrade:** image teglarini (`WAZUH_VERSION`, `DJANGO_VERSION`, trivy/grype/syft pin) yangilab,
  staging'da sinab, keyin prod (backup'dan keyin).

## 7. Hali ham e'tibordagi cheklovlar (halol)
- **Single-node Wazuh** — HA emas. Katta park / SLA uchun cluster kerak (alohida ish).
- **Real agent fleet deploy** operator muhitida bajariladi (bu repo IaC tayyor).
- **Reverse-proxy/TLS** ixtiyoriy — domen/sertifikat operatorники.
- **OS-CVE live isboti** alohida test VM talab qiladi (5-bo'lim).
