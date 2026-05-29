# TIZIM — To'liq Qo'llanma (GUIDE)

Ushbu hujjat TIZIM'ni **noldan tushunish, o'rnatish, sozlash, ishlatish, kuzatish va
kengaytirish** uchun yagona batafsil qo'llanma. Tezkor havolalar:
[README](../README.md) · [Arxitektura](architecture.md) · [Production checklist](PROD-READINESS.md) ·
[Spec](specs/2026-05-29-tizim-design.md) · [Reja](plans/2026-05-29-tizim-build.md)

---

## Mundarija
1. [TIZIM nima va nega](#1-tizim-nima-va-nega)
2. [Arxitektura](#2-arxitektura)
3. [Talablar](#3-talablar)
4. [O'rnatish (lokal sinov)](#4-ornatish-lokal-sinov)
5. [O'rnatish (production)](#5-ornatish-production)
6. [Konfiguratsiya — to'liq ma'lumotnoma](#6-konfiguratsiya--toliq-malumotnoma)
7. [Kundalik ishlash](#7-kundalik-ishlash)
8. [Agentlarni boshqarish (RHEL serverlar)](#8-agentlarni-boshqarish-rhel-serverlar)
9. [Skriptlar ma'lumotnomasi](#9-skriptlar-malumotnomasi)
10. [Texnik xizmat (backup, retention, upgrade)](#10-texnik-xizmat)
11. [Muammolarni bartaraf etish](#11-muammolarni-bartaraf-etish)
12. [Xavfsizlik modeli](#12-xavfsizlik-modeli)
13. [Kengaytirish](#13-kengaytirish)
14. [FAQ](#14-faq)

---

## 1. TIZIM nima va nega

TIZIM — **self-hosted, ochiq kodli ichki xavfsizlik monitoring platformasi**. U RHEL-oilasi
(Rocky/Alma/RHEL) serverlaringizdagi zaifliklarni markazlashgan tarzda kuzatib, **har kuni
avtomatik HTML xavfsizlik hisobotini** yuboradi.

**To'rt o'lcham:**
1. **OS paketlar** — serverga o'rnatilgan RPM paketlardagi ma'lum CVE'lar (Wazuh agent).
2. **Docker image'lar** — konteyner image'laridagi zaifliklar (Trivy + Grype).
3. **Kod bog'liqliklari** — pip/npm/go.mod kutubxonalari (Trivy fs).
4. **Compliance** — CIS Benchmark / SCAP audit (OpenSCAP).

Hammasi bitta dashboardda (Wazuh) + agregator (DefectDojo)da jamlanadi va hisobot
email/Telegram orqali yetkaziladi. Noldan yozilmagan — yetuk ochiq kodli vositalar ulangan.

---

## 2. Arxitektura

Ikki qism:

**A — Markaziy stek (Docker Compose, monitoring host):**
- **Wazuh** single-node: `wazuh.manager` + `wazuh.indexer` + `wazuh.dashboard` — SIEM, agent,
  OS-CVE (CTI feed), SCA/CIS.
- **DefectDojo**: zaifliklarni jamlash, dedup, trend (released-image compose).
- **Orchestrator** (Python): cron 02:00 — Wazuh'dan zaifliklarni oladi, Trivy/Grype skanini
  ishga tushiradi, DefectDojo'ga import qiladi, HTML hisobotni email/Telegram'ga yuboradi.
- **mailhog**: faqat lokal sinov uchun (email tutib oluvchi).

**B — RHEL target'lar (Ansible):**
- `wazuh_agent` role — har serverga agent.
- `openscap` role — CIS audit.

Batafsil diagrammalar (flowchart, sequence, tarmoq): [architecture.md](architecture.md).

**Tarmoq:** uchala stek `tizim_net` (external) tarmog'ida. `docker-compose.override.yml` fayllari
`wazuh.indexer`/`wazuh.manager`/`nginx`'ni unga **deklarativ** ulaydi (service-nomi = alias) →
orchestrator ularga TLS-mos nomlar bilan yetadi, restart'dan keyin ham saqlanadi.

**Portlar (default, faqat localhost — xavfsizlik):**
| Servis | Port | Kim uchun |
|---|---|---|
| Wazuh dashboard | `127.0.0.1:8444` | admin (SSH tunnel) |
| Wazuh indexer | `127.0.0.1:9200` | admin/debug |
| Wazuh API | `127.0.0.1:55000` | admin/orchestrator |
| Wazuh agent (events/enroll) | `0.0.0.0:1514/1515` | **agentlar** (tarmoqdan ochiq) |
| DefectDojo | `127.0.0.1:8888` | admin (SSH tunnel) |
| mailhog | `127.0.0.1:8025` | sinov |

---

## 3. Talablar

- **Monitoring host:** Docker + Docker Compose v2, ~**12 GB RAM** (Wazuh indexer + DefectDojo),
  ≥50 GB disk, `vm.max_map_count ≥ 262144` (`sysctl -w vm.max_map_count=262144`).
- **Target serverlar:** RHEL/Rocky/Alma 8/9/10, SSH kirish (kalit bilan), 1514/1515 portlari
  monitoring host'ga ochiq.
- **Lokal sinov uchun:** Ansible (`pip install ansible-core`), `openssl`, `python3`.

---

## 4. O'rnatish (lokal sinov)

```bash
git clone <tizim-repo> && cd TIZIM
cp compose/.env.example compose/.env
cp compose/defectdojo/.env.example compose/defectdojo/.env
# DefectDojo majburiy kalitlarini to'ldiring (6-bo'lim)

bash scripts/bootstrap-central.sh    # parol rotatsiya + certs + stek
bash scripts/configure-retention.sh  # ISM retention (indexer ko'tarilgach)
bash test/e2e.sh                     # smoke test
```

Dashboardlarga kirish (localhost-bound) — SSH tunnel orqali:
```bash
ssh -L 8444:127.0.0.1:8444 -L 8888:127.0.0.1:8888 user@host
# Wazuh: https://localhost:8444   DefectDojo: http://localhost:8888
```

⚠️ Kam RAM bo'lsa Wazuh va DefectDojo'ni navbatma-navbat sinang.

---

## 5. O'rnatish (production)

To'liq runbook va checklist: **[PROD-READINESS.md](PROD-READINESS.md)**. Qisqacha:

```bash
# 1. Repo + env
cp compose/.env.example compose/.env
cp compose/defectdojo/.env.example compose/defectdojo/.env

# 2. DefectDojo MAJBURIY kalitlari (compose/defectdojo/.env):
python -c 'import secrets;print(secrets.token_urlsafe(50))'   # DD_SECRET_KEY
openssl rand -base64 24                                        # DD_CREDENTIAL_AES_256_KEY
openssl rand -base64 24                                        # DD_DATABASE_PASSWORD (+ DD_DATABASE_URL)

# 3. (ixtiyoriy) compose/.env: TELEGRAM_BOT_TOKEN/CHAT_ID, HEARTBEAT_URL, real SMTP

# 4. Bootstrap (Wazuh demo parollarini AVTOMATIK rotatsiya qiladi)
bash scripts/bootstrap-central.sh

# 5. Retention + 6. Agentlar + 7. Backup cron — PROD-READINESS.md'ga qarang
```

Bootstrap avtomatik bajaradi: `tizim_net` → `gen-wazuh-secrets.sh` (parol rotatsiya) →
`configure-telegram.sh` → certs → Wazuh up → DefectDojo up → orchestrator up.

---

## 6. Konfiguratsiya — to'liq ma'lumotnoma

### `compose/.env` (markaziy stek + orchestrator)
| O'zgaruvchi | Tavsif |
|---|---|
| `WAZUH_VERSION` | Wazuh image tegi (4.9.2) |
| `WAZUH_DASHBOARD_PORT` | Dashboard localhost porti (8444) |
| `INDEXER_PASSWORD` | Indexer admin paroli — **`gen-wazuh-secrets.sh` rotatsiya qiladi** |
| `WAZUH_API_USER` / `WAZUH_API_PASSWORD` | Wazuh API (wazuh-wui). Parol **murakkab** bo'lishi shart (katta/kichik/raqam/maxsus) |
| `INDEXER_URL` / `INDEXER_USER` | Orchestrator indexer ulanishi (`https://wazuh.indexer:9200`, admin) |
| `DEFECTDOJO_URL` | Orchestrator DefectDojo ulanishi (`http://nginx:8080` — internal) |
| `DD_API_TOKEN` | DefectDojo API token (DefectDojo ko'tarilgach olinadi) |
| `CA_BUNDLE` | Indexer TLS uchun CA (`/opt/tizim/certs/root-ca.pem`) — **verify hech qachon o'chmaydi** |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram alert (bo'sh => o'tkazib yuboriladi) |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM/TO` | Email. Gmail: `smtp.gmail.com:587` + app password + `SMTP_TLS=true` |
| `SMTP_TLS` | `true` => STARTTLS+login (auth TLS'siz **taqiqlanadi**) |
| `HEARTBEAT_URL` | Dead-man's-switch (healthchecks.io) — muvaffaqiyatda GET qilinadi |

### `compose/defectdojo/.env`
| O'zgaruvchi | Tavsif |
|---|---|
| `DD_PORT` / `DD_TLS_PORT` | DefectDojo localhost portlari (8888/8446) |
| `DD_ALLOWED_HOSTS` | **`nginx` bo'lishi SHART** (orchestrator shu nom bilan ulanadi) + FQDN |
| `DD_SECRET_KEY` / `DD_CREDENTIAL_AES_256_KEY` | MAJBURIY (`${VAR:?}`) — generatsiya qiling |
| `DD_DATABASE_PASSWORD` / `DD_DATABASE_URL` | MAJBURIY, parol mos bo'lsin |

### `ansible/inventory.ini`
SSH-kalit bilan real serverlar; `wazuh_manager_ip` = manager hostining real IP/DNS.
Namuna: `inventory.ini.example`.

---

## 7. Kundalik ishlash

**Avtomatik sikl (cron, har kuni 02:00):**
1. Orchestrator Wazuh indexer'dan agent OS-CVE'larini oladi.
2. `scanning/images.txt`dagi image'larni Trivy + Grype bilan skanlaydi.
3. `scanning/repos.yml`dagi repo'larni klonlab `trivy fs` bilan skanlaydi.
4. Natijalarni DefectDojo'ga import qiladi (dedup, `close_old_findings`).
5. Barcha manbalarni jamlab HTML hisobot tuzadi.
6. Email (+ Telegram) yuboradi: body'da xulosa + barcha CRITICAL, ilovada to'liq `.html`.
7. Muvaffaqiyatda `HEARTBEAT_URL` GET qilinadi.

**Qo'lda ishga tushirish:** `bash scripts/run-daily-scan.sh`

**Skan nishonlarini sozlash:**
- `scanning/images.txt` — har qatorda image ref (masalan `registry.example/app:1.2`).
- `scanning/repos.yml` — `repos: [{name, url, ecosystem}]`.

**Dashboardlar:** Wazuh (`https://localhost:8444` tunnel orqali) — agent holati, CVE, SCA/CIS;
DefectDojo (`http://localhost:8888`) — jamlangan topilmalar, trend, engagement'lar.

---

## 8. Agentlarni boshqarish (RHEL serverlar)

```bash
cp ansible/inventory.ini.example ansible/inventory.ini   # real serverlar + SSH kalit
bash scripts/enroll-agents.sh                            # agent + openscap o'rnatadi
```

`wazuh_agent` role: Wazuh repo qo'shadi, `wazuh-agent` o'rnatadi (`WAZUH_MANAGER`=manager IP),
service yoqadi. `openscap` role: `openscap-scanner`+`scap-security-guide`, datastream'ni distro
bo'yicha avtomatik tanlaydi, kunlik CIS skani uchun systemd timer.

Agent ro'yxatdan o'tganini tekshirish (manager API'da):
```bash
TOKEN=$(curl -sk -u wazuh-wui:<API_PW> -X POST "https://127.0.0.1:55000/security/user/authenticate?raw=true")
curl -sk -H "Authorization: Bearer $TOKEN" "https://127.0.0.1:55000/agents?select=name,status"
```

---

## 9. Skriptlar ma'lumotnomasi

| Skript | Vazifa |
|---|---|
| `bootstrap-central.sh` | Markaziy stekni to'liq ko'taradi (parol rotatsiya + telegram + certs + up) |
| `gen-wazuh-secrets.sh` | Wazuh demo parollarini kuchli tasodifiyga almashtiradi (fresh deploy) |
| `configure-telegram.sh` | `.env`dagi `TELEGRAM_*`dan Wazuh L12 alert hook_url'ini ulaydi |
| `configure-retention.sh` | Wazuh ISM retention policy (`wazuh-alerts-*` N kun) |
| `backup-defectdojo.sh` | DefectDojo Postgres + media backup (cron uchun) |
| `enroll-agents.sh` | Ansible: agent + openscap (real inventar talab qiladi) |
| `run-daily-scan.sh` | Kunlik skan siklini qo'lda ishga tushiradi |

---

## 10. Texnik xizmat

- **Backup (kunlik cron):**
  `echo "0 3 * * * cd /opt/TIZIM && bash scripts/backup-defectdojo.sh" | crontab -`
  (`TIZIM_BACKUP_DIR`, `BACKUP_KEEP_DAYS` sozlanadi.)
- **Retention:** `RETENTION_DAYS=90 bash scripts/configure-retention.sh` (yangi indekslarga avto).
- **Loglar:** orchestrator → docker `json-file` (10m × 3) avto-rotation. `docker logs compose-orchestrator-1`.
- **Heartbeat:** `HEARTBEAT_URL` o'rnatilsa, kunlik sikl ishlamasa tashqi xizmat (healthchecks.io) alert beradi.
- **Upgrade:** image teglarini (`WAZUH_VERSION`, `DJANGO_VERSION`, Dockerfile'da trivy/grype/syft pin)
  yangilang → staging'da sinang → backup → prod.
- **Unit testlar:** `cd compose/orchestrator && python -m pytest tests/`.

---

## 11. Muammolarni bartaraf etish

| Belgi | Sabab | Yechim |
|---|---|---|
| Manager `Restarting`, log `Error 5007 Insecure user password` | Wazuh API paroli murakkab emas | `WAZUH_API_PASSWORD`ga katta/kichik/raqam/maxsus belgi (`gen-wazuh-secrets.sh` to'g'ri qiladi) |
| Indexer/API `HTTP 401` | Noto'g'ri parol yoki `.env`da **dublikat** kalit (`grep` ko'p qiymat oladi) | `.env`da bitta kalit; skriptlar `head -1` ishlatadi |
| `HTTP 000` (curl) | TLS hostname mos emas (cert SAN `wazuh.indexer` ≠ `localhost`) | `--resolve wazuh.indexer:9200:127.0.0.1 --cacert root-ca.pem` |
| Dashboard `HTTP 302` | Login redirect | **Normal** — stek sog'lom |
| DefectDojo import `400 "Schema not supported"` | Soxta/noto'g'ri JSON | Haqiqiy `trivy --format json` chiqishi |
| DefectDojo `400 "no product_type_name"` | auto_create product_type kerak | import'ga `product_type_name` (orchestrator qiladi) |
| DefectDojo `400` HTML javob | `DD_ALLOWED_HOSTS`da `nginx` yo'q | `nginx` qo'shing |
| Trivy build `404` (install.sh) | `get.trivy.dev` eski versiyaga 404 | GitHub release'dan direct + SHA256 (Dockerfile shunday) |
| `tizim_net could not be found` | Bo'sh tarmoq `docker network prune` o'chirgan | `docker network create tizim_net` (konteyner ulangach himoyalanadi) |
| Agent OS-CVE = 0 | Yangi/patched minimal tizim — legitim | Real serverda to'ladi; isbot uchun **test VM'da** ataylab zaif paket |
| Skript deploy oxirida `exit 1` | `set -e + pipefail + grep` topmadi | `grep ... \|\| true` |

Diagnostika: `docker logs <konteyner>`, manager ichida `/var/ossec/logs/ossec.log`,
indexer `/_cat/indices`, `docker ps` status/healthcheck.

---

## 12. Xavfsizlik modeli

- **Internal-only:** dashboard/DefectDojo/indexer faqat `127.0.0.1` — internetga **ochiq emas**.
  Kirish: SSH tunnel yoki VPN. Public kerak bo'lsa: reverse-proxy + TLS + auth (PROD-READINESS §3).
- **Maxfiy kalitlar:** Wazuh demo parollari rotatsiya qilinadi; DefectDojo kalitlari majburiy
  (`${VAR:?}`); sirlar `.env`da (gitignore), repo'ga commit qilinmaydi.
- **TLS verification HECH QACHON o'chirilmaydi** — orchestrator Wazuh CA'ga qarshi tekshiradi.
- **SMTP auth faqat TLS bilan** (cleartext parol himoyasi).
- **docker.sock mount qilinmaydi** (host-root oldini olish) — Trivy registry'dan pull qiladi.
- **Resurs limitlari** — TIZIM boshqa servislarni siqib qo'ymaydi.

---

## 13. Kengaytirish

- **Yangi skan nishoni:** `scanning/images.txt` (image) yoki `scanning/repos.yml` (repo) ga qo'shing.
- **Yangi notifier:** `compose/orchestrator/app/notifiers.py`ga funksiya + `main.py`da chaqiruv + test.
- **Hisobot formati:** `compose/orchestrator/app/report.py` (`render_html_summary`/`render_html_full`).
- **Yangi skaner:** `app/scanners.py`ga wrapper + `parse_findings`ga normalizatsiya + DefectDojo parser.
- **Har o'zgarishdan keyin:** `pytest` + `docker compose config` + CI (`.github/workflows/ci.yml`).

---

## 14. FAQ

**S: Bir vaqtning o'zida nechta server kuzatadi?**
J: Single-node Wazuh kichik-o'rta park (<100 agent) uchun. Kattaroq uchun Wazuh cluster (alohida ish).

**S: Hisobotni Telegram'ga ham yuborsam bo'ladimi?**
J: Ha — `compose/.env`da `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` to'ldiring, orchestrator'ni recreate qiling.

**S: Email Gmail'ga qanday ketadi?**
J: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER`=Gmail, `SMTP_PASSWORD`=app password, `SMTP_TLS=true`.

**S: OS-CVE topilmasa nima qilay?**
J: Real serverda agent inventari to'lgach CVE'lar chiqadi. Pipeline'ni isbotlash uchun alohida
test VM'da ataylab eski paket o'rnating (prod'da emas).

**S: Hammasi to'g'ri ishlayotganini qanday bilaman?**
J: `bash test/e2e.sh` — dashboard, DefectDojo, kunlik hisobot va email/exit-0 tekshiriladi.
