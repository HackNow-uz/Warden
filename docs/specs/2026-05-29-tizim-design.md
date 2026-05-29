# TIZIM — Ichki Xavfsizlik Monitoring Platformasi

**Dizayn spetsifikatsiyasi**
**Sana:** 2026-05-29
**Status:** tasdiqlangan (dizayn) → implementatsiya rejasiga tayyor
**Muhit (target):** RHEL-oilasi (Rocky Linux / AlmaLinux / RHEL)
**Litsenziya cheklovi:** faqat ochiq kodli, self-hosted

---

## 1. Maqsad

Bir nechta RHEL-oilasi serverni markazlashgan, avtomatlashtirilgan tarzda xavfsizlik nuqtai
nazaridan kuzatib boruvchi platforma qurish. Tizim har kuni quyidagilarni aniqlaydi va hisobot yuboradi:

1. **OS paketlar** — serverga o'rnatilgan RPM paketlar versiyasidagi ma'lum CVE'lar
2. **Docker image'lar** — konteyner image'lari ichidagi OS va kutubxona zaifliklari
3. **Kod bog'liqliklari** — pip / npm / go.mod kutubxonalaridagi zaifliklar
4. **Compliance** — CIS Benchmark / SCAP bo'yicha noto'g'ri sozlamalar

**Asosiy talablar:** markaziy dashboard · agent-based yig'ish · tarixiy trend · alert ·
avtomatik kunlik hisobot (email + Telegram).

## 2. Qamrov

**Ushbu speс — to'liq stek (full stack).** Barcha 4 o'lcham + dashboard + agregatsiya +
compliance + avtomatik hisobot + alert.

### Non-goals (bu speс doirasida emas)
- Wazuh cluster (multi-node) — single-node bilan boshlaymiz; keyin masshtablash alohida ish
- WAF / IDS / EDR active response (Wazuh imkoniyati bor, lekin bu speс'da yoqilmaydi)
- Tashqi SaaS integratsiyasi (Snyk, Tenable va h.k.) — ochiq kodli cheklov

## 3. Yondashuv

Noldan yozilmaydi. Sanoatda yetuk ochiq kodli stek quriladi va o'zaro ulanadi:

| Komponent | Rol | Qoplaydigan o'lcham |
|---|---|---|
| **Wazuh** (manager + indexer + dashboard) | Markaziy platforma, agent, dashboard, alert | OS paket CVE (1) + CIS/SCA (4) |
| **Trivy** | Image + kod bog'liqlik skaneri | Docker (2) + deps (3) + OS |
| **Grype + Syft** | Cross-check skaner (SBOM) | Docker (2) + deps (3) |
| **DefectDojo** | Natijalarni jamlash, dedup, trend, hisobot | — (agregatsiya) |
| **OpenSCAP + SSG** | RHEL CIS audit dvigateli | Compliance (4) |
| **Orchestrator** (custom Python) | Glue: skan → import → hisobot → alert | — (avtomatika) |

## 4. Arxitektura — ikki qism

### A qism — Markaziy stek (Docker Compose, monitoring host)
- `wazuh-indexer`, `wazuh-manager`, `wazuh-dashboard` — rasmiy `wazuh/wazuh-docker`
  single-node (engine ≥ 4.8, ya'ni CTI-asoslangan yangi vulnerability-detection)
- DefectDojo — rasmiy compose (django-uwsgi, nginx, postgres, redis, celery-worker, celery-beat)
- **Orchestrator** — bizning Python xizmatimiz (konteyner), cron bilan boshqariladi

### B qism — RHEL target'lar (Ansible)
- `wazuh_agent` role — har serverga agent o'rnatadi, manager IP'siga ulaydi, ro'yxatdan o'tkazadi
- `openscap` role — `openscap-scanner` + `scap-security-guide` o'rnatadi, CIS profil bo'yicha
  rejalashtirilgan `oscap` skan sozlaydi; natija Wazuh'ga SCA orqali boradi
- `inventory.ini` — target serverlar ro'yxati

### Ma'lumot oqimi (kunlik sikl, 02:00)
```
1. wazuh-agent → manager:  OS paket inventari (uzluksiz, Syscollector)
2. manager:                CVE moslashtirish (CTI feed: RHEL/Rocky/Alma)
3. orchestrator (cron):    scanning/ dagi image + repo'larni Trivy & Grype bilan skan
4. orchestrator → DefectDojo:  Trivy/Grype JSON import (import-scan API, dedup)
5. orchestrator → Wazuh API:   GET zaifliklar + SCA holati
6. orchestrator:           jamlangan xulosa tuzadi (severity bo'yicha)
7. orchestrator → Telegram + SMTP:  kunlik hisobot
8. (real-vaqt) manager:    CRITICAL/HIGH yangi CVE → alert (Telegram)
```

## 5. Repo strukturasi (`TIZIM/`)

```
TIZIM/
├── README.md
├── .gitignore                      # .env, *.key, ansible retry, __pycache__
├── docs/
│   ├── prezentatsiya.html          # (mavjud)
│   ├── architecture.md             # arxitektura + diagramlar
│   └── specs/2026-05-29-tizim-design.md   # (ushbu fayl)
├── compose/                        # A qism — markaziy stek
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── wazuh/
│   │   ├── manager/ossec.conf      # <reports> bloki, vulnerability-detection, sca
│   │   ├── manager/integrations/   # custom-telegram alert integration
│   │   └── config/                 # indexer/dashboard certs generatsiyasi
│   ├── defectdojo/.env.example
│   └── orchestrator/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── crontab                 # 0 2 * * *  run-daily
│       └── app/
│           ├── main.py             # CLI entrypoint (run-daily, run-scan)
│           ├── config.py           # env'dan sozlama (pydantic-settings)
│           ├── wazuh_client.py     # Wazuh API: auth, vulnerabilities, sca
│           ├── scanners.py         # Trivy + Grype subprocess wrappers
│           ├── defectdojo_client.py# import-scan API
│           ├── report.py           # jamlangan kunlik hisobot tuzish
│           └── notifiers.py        # Telegram + SMTP
├── ansible/                        # B qism — RHEL target'lar
│   ├── ansible.cfg
│   ├── inventory.ini.example
│   ├── site.yml
│   └── roles/
│       ├── wazuh_agent/            # agent o'rnatish + register + service
│       └── openscap/               # oscap + ssg + scheduled scan
├── scanning/
│   ├── images.txt                  # skan qilinadigan image ref'lar (registry)
│   └── repos.yml                   # kod repo'lar (git url + ekotizim)
├── scripts/
│   ├── bootstrap-central.sh        # A qismni ko'tarish + sertifikat init
│   ├── enroll-agents.sh            # ansible-playbook site.yml
│   └── run-daily-scan.sh           # orchestrator'ni qo'lda ishga tushirish
└── test/
    ├── docker-compose.targets.yml  # rockylinux:9 + systemd (soxta agentlar)
    └── e2e.sh                      # lokal end-to-end smoke test
```

## 6. Komponent tafsilotlari

### 6.1 Wazuh (markaziy)
- Single-node, 3 konteyner. `ossec.conf`'da:
  - `<vulnerability-detection><enabled>yes` (4.8+ yangi nom; eski `vulnerability-detector` EMAS)
  - `<sca>` yoqilgan (CIS policy)
  - `<reports>` bloki — kunlik alert summary (email orqali, manager native)
  - `<integration>` — custom Telegram skripti (CRITICAL/HIGH uchun)
- Sertifikatlar `wazuh-certs-tool` bilan generatsiya qilinadi (bootstrap skriptida)

### 6.2 DefectDojo (agregatsiya)
- Rasmiy docker-compose asosida, alohida `.env`
- Parserlar: **Trivy** (Trivy JSON) va **Trivy Operator** — native qo'llab-quvvatlanadi
- Orchestrator `import-scan` / `reimport-scan` API orqali yuboradi → dedup avtomatik
- Engagement: har skan turi uchun alohida (image-scan, deps-scan)

### 6.3 Orchestrator (custom glue)
- Til: Python 3.12, base `python:3.12-slim`, ichida `trivy` va `grype` binary
- `main.py run-daily` → to'liq sikl; `main.py run-scan` → faqat skan
- Cron `0 2 * * *`; xato bo'lsa alert yuboradi (silent failure YO'Q)
- Sozlama `.env`'dan: WAZUH_API_URL/USER/PASS, DEFECTDOJO_URL/TOKEN,
  TELEGRAM_BOT_TOKEN/CHAT_ID, SMTP_*
- Trivy RHEL gotcha: image'lar **ref bo'yicha** (registry'dan) skanlash —
  flatten qilingan FS emas (false-positive oldini olish)

### 6.4 Ansible — `wazuh_agent` role
- `dnf` repo qo'shadi (Wazuh GPG), `wazuh-agent` o'rnatadi
- `WAZUH_MANAGER` o'zgaruvchisi orqali manager IP, `authd` orqali register
- idempotent; service enable + start

### 6.5 Ansible — `openscap` role
- `openscap-scanner`, `scap-security-guide` o'rnatadi
- CIS profil (`xccdf_org.ssgproject.content_profile_cis`) bo'yicha skan
- systemd timer (kunlik) yoki Wazuh SCA bilan integratsiya
- ⚠️ Red Hat OVAL v2 → CSAF/VEX migratsiyasi: CIS/XCCDF baholash davom etadi,
  lekin CVE-OVAL baholash uchun Wazuh CTI feed'ga tayanamiz (OpenSCAP'ni faqat
  configuration compliance uchun ishlatamiz, CVE uchun emas)

## 7. Konfiguratsiya va maxfiy ma'lumot
- Barcha sirlar `.env`'da (gitignore), `.env.example` commit qilinadi
- Sertifikatlar va kalitlar repo'ga tushmaydi
- Ansible vault (ixtiyoriy) — agent registration parol uchun

## 8. Lokal sinov yondashuvi
Host Arch bo'lsa-da, markaziy stek Docker'da kross-platforma ishlaydi.
- `compose/` → `docker-compose up` bilan to'liq platforma lokal
- `test/docker-compose.targets.yml` → `rockylinux:9` + systemd konteynerlar (privileged,
  faqat sinov) — Ansible playbook ularga qarshi ishlaydi, real enrollment simulyatsiyasi
- `test/e2e.sh` tekshiradi:
  1. Wazuh dashboard 443 ochiladi
  2. Soxta Rocky agent ro'yxatdan o'tdi (`GET /agents`)
  3. Agent vuln data bor (`GET /vulnerability`)
  4. Trivy skan DefectDojo'ga import bo'ldi (finding count > 0)
  5. Test hisobot test Telegram kanaliga / mailhog'ga yetdi

## 9. Qurish bosqichlari (build order)
Full stack, lekin har bosqich mustaqil tekshiriladi:

| # | Bosqich | Acceptance |
|---|---|---|
| 1 | Repo skelet + README + .gitignore + Wazuh single-node compose | dashboard ko'tarildi |
| 2 | DefectDojo compose'ga qo'shildi | DefectDojo UI ochildi |
| 3 | Orchestrator: Wazuh API client + kunlik hisobot (TG/SMTP) | test hisobot yetdi |
| 4 | Orchestrator: Trivy + Grype skan → DefectDojo import | finding'lar DefectDojo'da |
| 5 | Ansible `wazuh_agent` + Rocky test konteynerlar | agent enrolled |
| 6 | Ansible `openscap` + Wazuh SCA/CIS | CIS natija ko'rinadi |
| 7 | Cron + Telegram alert avtomatika | 02:00 sikl + CRITICAL alert |
| 8 | architecture.md + e2e.sh + README yakunlash | e2e.sh yashil |

## 10. Resurs talablari (lokal sinov + prod)
- Wazuh indexer: ~2–4 GB RAM (JVM heap), DefectDojo: ~2 GB, manager+dashboard: ~2 GB
- **Lokal to'liq stek: ~10–12 GB RAM tavsiya.** Mashina yetmasa — Wazuh va DefectDojo
  navbatma-navbat sinaladi (compose profile bilan ajratiladi)
- Disk: indexer ma'lumoti uchun ≥ 30 GB
- Prod single-node (<100 agent): 4 vCPU, 8–16 GB RAM, 50+ GB disk

## 11. Xavf va yumshatish (research'dan tasdiqlangan)
- **Wazuh 4.8 rewrite:** eski `vulnerability-detector` config tag ishlamaydi → yangi
  `vulnerability-detection` + indexer aloqasi ishlatiladi
- **OVAL v2 deprecation:** OpenSCAP'ni CVE-OVAL uchun emas, faqat config compliance uchun;
  CVE'lar Wazuh CTI + Trivy (CSAF/VEX) orqali
- **Scanner kelishmovchiligi (~31%):** Trivy + Grype ikkalasi ishlatiladi, DefectDojo dedup
- **Trivy layer-flatten false-positive:** image'lar ref bo'yicha skanlash
- **Silent failure yo'q:** orchestrator har xatoda alert yuboradi, e2e.sh CI-da tekshiradi
- **TLS verification hech qachon o'chirilmaydi:** bu xavfsizlik platformasi — Wazuh self-signed
  sertifikat uchun generatsiya qilingan `root-ca.pem` orchestrator'ga mount qilinadi va
  `CA_BUNDLE` orqali tekshiriladi (`verify=False` ANTIPATTERN, ishlatilmaydi)

## 12. Ochiq savollar (implementatsiya davomida hal qilinadi)
- DefectDojo'da Wazuh (CTI) va Trivy (CSAF) dublikat CVE'larni qanday reconcile qilish
  (boshlanishida: alohida engagement, keyin product-level dedup sozlash)
- Telegram alert rate-limit (CRITICAL ko'p bo'lsa) — batafsil throttle keyin
- Real registry kredensiallari (image pull) — prod inventarga bog'liq
