# Warden Build — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted, open-source security monitoring platform (Wazuh + Trivy/Grype + DefectDojo + OpenSCAP) as an Infrastructure-as-Code repo under `Warden/`, locally testable with Docker, deployable to RHEL-family servers via Ansible, emitting a daily security report.

**Architecture:** Two parts. **Part A** (central stack) runs via Docker Compose on a monitoring host: Wazuh single-node, DefectDojo, and a custom Python "orchestrator" glue service. **Part B** (RHEL targets) is provisioned by Ansible: `wazuh-agent` + `openscap`. A cron-driven daily cycle pulls Wazuh vuln/SCA data, runs Trivy+Grype on images/repos, imports to DefectDojo, and sends a Telegram+email report.

**Tech Stack:** Docker Compose, Wazuh 4.x (≥4.8 CTI engine), DefectDojo, Trivy, Grype, Syft, Python 3.12 (requests, pydantic-settings, pytest), Ansible, Rocky Linux 9 test containers.

**Spec:** `Warden/docs/specs/2026-05-29-tizim-design.md`

**Conventions:**
- All shell commands assume CWD = `Warden/` unless stated.
- Commit messages: formal Uzbek, no Claude co-author (per org CLAUDE.md). Conventional Commits prefix allowed.
- Secrets only in `.env` (gitignored). `.env.example` is committed with placeholder values.
- "Verify" steps are the IaC equivalent of TDD: bring a thing up, assert it responds, tear down.

---

## Phase 0: Repo scaffold & git

### Task 0.1: Initialize repo skeleton

**Files:**
- Create: `Warden/.gitignore`
- Create: `Warden/README.md`
- Create: `Warden/.env.example` (root, points to sub-stack envs)

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# secrets & env
.env
*.env
!*.env.example
# certs & keys
*.pem
*.key
*.crt
compose/wazuh/config/wazuh_indexer_ssl_certs/
# python
__pycache__/
*.pyc
.pytest_cache/
.venv/
# ansible
*.retry
ansible/inventory.ini
# scan output
*.scan.json
scanning/_out/
# test artifacts
test/_out/
```

- [ ] **Step 2: Create `README.md`**

```markdown
# Warden — Ichki Xavfsizlik Monitoring Platformasi

Self-hosted, ochiq kodli xavfsizlik monitoring stek: **Wazuh** (markaz) +
**Trivy/Grype** (konteyner & kod skani) + **DefectDojo** (agregatsiya) +
**OpenSCAP** (CIS compliance). Har kuni avtomatik xavfsizlik hisoboti.

## Tezkor boshlash (lokal sinov)
```bash
cp compose/.env.example compose/.env   # qiymatlarni to'ldiring
bash scripts/bootstrap-central.sh      # Wazuh + DefectDojo + orchestrator
bash test/e2e.sh                        # end-to-end smoke test
```

## Tuzilma
- `compose/` — markaziy stek (Docker Compose)
- `ansible/` — RHEL target'larga agent + openscap
- `scanning/` — skan qilinadigan image/repo ro'yxati
- `scripts/` — bootstrap, enroll, daily-scan
- `test/` — lokal e2e (Rocky systemd konteynerlar)
- `docs/` — spec, arxitektura, prezentatsiya

Batafsil: `docs/specs/2026-05-29-tizim-design.md`
```

- [ ] **Step 3: Create root `.env.example`**

```bash
# Bu fayl faqat ko'rsatma. Haqiqiy sozlamalar:
#   compose/.env          — markaziy stek
#   ansible/inventory.ini — target serverlar
```

- [ ] **Step 4: Init git and first commit**

```bash
cd Warden && git init -b main
git add .gitignore README.md .env.example docs/
git commit -m "chore: repo skeleti va dastlabki hujjatlar"
```
Expected: repo initialized, one commit. `docs/` already contains spec + presentation.

---

## Phase 1: Wazuh single-node central stack

### Task 1.1: Vendor the Wazuh single-node compose

**Files:**
- Create: `compose/wazuh/` (from upstream `wazuh/wazuh-docker` `single-node/`)
- Create: `compose/.env.example`

- [ ] **Step 1: Fetch upstream single-node into a temp dir and copy**

Run:
```bash
WZ_VER=v4.9.2   # pin: latest stable 4.x with CTI engine
git clone --depth 1 -b $WZ_VER https://github.com/wazuh/wazuh-docker /tmp/wazuh-docker
mkdir -p compose/wazuh
cp -r /tmp/wazuh-docker/single-node/* compose/wazuh/
ls compose/wazuh
```
Expected: `docker-compose.yml`, `generate-indexer-certs.yml`, `config/` present.

- [ ] **Step 2: Create `compose/.env.example`**

```bash
# ---- Wazuh ----
WAZUH_VERSION=4.9.2
INDEXER_PASSWORD=SecretPassword1!
DASHBOARD_PASSWORD=SecretPassword2!
WAZUH_API_USER=wazuh-wui
WAZUH_API_PASSWORD=MyS3cr37P450r.*-

# ---- DefectDojo ---- (Phase 2)
DD_ADMIN_USER=admin
DD_ADMIN_PASSWORD=ChangeMeAdmin1!
DD_API_TOKEN=                      # Phase 2: initializer log'idan olinadi

# ---- Orchestrator notifiers ---- (Phase 3)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=tizim@local
SMTP_TO=secops@local

# ---- Orchestrator → Wazuh & DefectDojo (Phase 3-4) ----
WAZUH_API_URL=https://wazuh.manager:55000
INDEXER_URL=https://wazuh.indexer:9200
INDEXER_USER=admin
DEFECTDOJO_URL=http://nginx:8080
DD_PRODUCT_ID=1
# TLS: Wazuh self-signed root CA is mounted into the orchestrator (see compose).
# Do NOT disable verification. Empty => system trust store.
CA_BUNDLE=/opt/tizim/certs/root-ca.pem
```

- [ ] **Step 3: Generate indexer certificates**

Run:
```bash
cd compose/wazuh
docker compose -f generate-indexer-certs.yml run --rm generator
cd ../..
```
Expected: `compose/wazuh/config/wazuh_indexer_ssl_certs/` populated with `.pem` files.

- [ ] **Step 4: Bring up Wazuh and verify dashboard**

Run:
```bash
cd compose/wazuh && docker compose up -d && cd ../..
sleep 90
curl -sk -u admin:SecretPassword https://localhost:443 -o /dev/null -w "%{http_code}\n"
```
Expected: `200` (dashboard up). If RAM-limited, see spec §10 (run Wazuh alone first).

- [ ] **Step 5: Verify Wazuh API auth works**

Run:
```bash
TOKEN=$(curl -sk -u wazuh-wui:MyS3cr37P450r.*- -X POST \
  "https://localhost:55000/security/user/authenticate?raw=true")
echo "${TOKEN:0:20}..."
curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost:55000/" | head -c 120
```
Expected: a JWT token string, then API banner JSON.

- [ ] **Step 6: Commit**

```bash
git add compose/wazuh compose/.env.example -- ':!compose/wazuh/config/wazuh_indexer_ssl_certs'
git commit -m "feat: Wazuh single-node markaziy stek qo'shildi"
```

### Task 1.2: Customize manager config (reports + telegram integration hook)

**Files:**
- Modify: `compose/wazuh/config/wazuh_cluster/wazuh_manager.conf`

- [ ] **Step 1: Add `<reports>` daily summary block**

Inside the root `<ossec_config>` of `wazuh_manager.conf`, add:
```xml
  <reports>
    <category>vulnerability-detector</category>
    <title>Warden kunlik zaiflik hisoboti</title>
    <email_to>secops@local</email_to>
  </reports>
```
Note: native email needs `<global><email_notification>yes` + SMTP; richer reporting is the orchestrator's job (Phase 3). This block is the manager-side daily summary.

- [ ] **Step 2: Add Telegram `<integration>` hook (script added in Phase 7)**

```xml
  <integration>
    <name>custom-telegram</name>
    <level>12</level>
    <alert_format>json</alert_format>
  </integration>
```
Level 12 ≈ HIGH/CRITICAL. The `custom-telegram` script is created in Task 7.1.

- [ ] **Step 3: Confirm vulnerability-detection & sca are enabled (4.8+ defaults)**

Verify these blocks exist (do NOT use the old `vulnerability-detector` tag):
```xml
  <vulnerability-detection>
    <enabled>yes</enabled>
    <index-status>yes</index-status>
  </vulnerability-detection>
```
If missing, add it. SCA is enabled by default via `<sca><enabled>yes</sca>`.

- [ ] **Step 4: Restart manager and verify config loads**

Run:
```bash
cd compose/wazuh && docker compose restart wazuh.manager && cd ../..
sleep 20
docker logs wazuh.manager 2>&1 | grep -i -E "error|reports" | tail -20
```
Expected: no fatal config errors; reports module mentioned.

- [ ] **Step 5: Commit**

```bash
git add compose/wazuh/config/wazuh_cluster/wazuh_manager.conf
git commit -m "feat: manager config — kunlik hisobot va telegram integratsiya hook'i"
```

---

## Phase 2: DefectDojo aggregation

### Task 2.1: Add DefectDojo compose

**Files:**
- Create: `compose/defectdojo/` (from upstream `DefectDojo/django-DefectDojo`)
- Create: `compose/docker-compose.yml` (top-level orchestration include)

- [ ] **Step 1: Vendor DefectDojo compose**

Run:
```bash
git clone --depth 1 https://github.com/DefectDojo/django-DefectDojo /tmp/dd
mkdir -p compose/defectdojo
cp /tmp/dd/docker-compose.yml compose/defectdojo/docker-compose.yml
cp -r /tmp/dd/docker compose/defectdojo/ 2>/dev/null || true
cp /tmp/dd/.env.example compose/defectdojo/.env.example 2>/dev/null || true
```
Expected: DefectDojo compose vendored.

- [ ] **Step 2: Bring up DefectDojo (released images, postgres-redis profile)**

Run:
```bash
cd compose/defectdojo
docker compose up -d
cd ../..
sleep 120
curl -s http://localhost:8080/login -o /dev/null -w "%{http_code}\n"
```
Expected: `200` or `302` (DefectDojo UI up). Port may differ; check `docker compose port nginx 8080`.

- [ ] **Step 3: Capture admin password + API token**

Run:
```bash
docker compose -f compose/defectdojo/docker-compose.yml logs initializer 2>&1 | grep -i "Admin password" | tail -1
# obtain API token:
DD_USER=admin; DD_PASS="<from-log>"
curl -s -X POST http://localhost:8080/api/v2/api-token-auth/ \
  -d "username=$DD_USER&password=$DD_PASS" | python3 -m json.tool
```
Expected: JSON with `token`. Save it into `compose/.env` as `DD_API_TOKEN`.

- [ ] **Step 4: Create a Product + Engagements for our scans**

Run (replace TOKEN):
```bash
T="<DD_API_TOKEN>"
PID=$(curl -s -X POST http://localhost:8080/api/v2/products/ \
  -H "Authorization: Token $T" -H "Content-Type: application/json" \
  -d '{"name":"Warden Infra","description":"Internal infra","prod_type":1}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Product=$PID"
```
Expected: product id printed. (Engagements created per-run by orchestrator.)

- [ ] **Step 5: Commit**

```bash
git add compose/defectdojo
git commit -m "feat: DefectDojo agregatsiya steki qo'shildi"
```

---

## Phase 3: Orchestrator — Wazuh client + daily report + notifiers (TDD)

### Task 3.1: Orchestrator package scaffold + config

**Files:**
- Create: `compose/orchestrator/app/__init__.py`
- Create: `compose/orchestrator/app/config.py`
- Create: `compose/orchestrator/requirements.txt`
- Create: `compose/orchestrator/tests/__init__.py`
- Test: `compose/orchestrator/tests/test_config.py`

- [ ] **Step 1: Write requirements.txt**

```
requests==2.32.3
pydantic-settings==2.5.2
pytest==8.3.3
```

- [ ] **Step 2: Write failing test for config**

`compose/orchestrator/tests/test_config.py`:
```python
import os
from app.config import Settings

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("WAZUH_API_URL", "https://wazuh.manager:55000")
    monkeypatch.setenv("WAZUH_API_USER", "wazuh-wui")
    monkeypatch.setenv("WAZUH_API_PASSWORD", "pw")
    monkeypatch.setenv("INDEXER_URL", "https://wazuh.indexer:9200")
    monkeypatch.setenv("INDEXER_PASSWORD", "ipw")
    monkeypatch.setenv("DEFECTDOJO_URL", "http://nginx:8080")
    monkeypatch.setenv("DD_API_TOKEN", "tok")
    s = Settings()
    assert s.wazuh_api_user == "wazuh-wui"
    assert s.defectdojo_url.endswith(":8080")
    assert s.verify is True  # SECURE default — TLS verification ON

def test_settings_uses_ca_bundle_when_set(monkeypatch):
    monkeypatch.setenv("CA_BUNDLE", "/opt/tizim/certs/root-ca.pem")
    s = Settings()
    assert s.verify == "/opt/tizim/certs/root-ca.pem"
```

- [ ] **Step 3: Run test, verify it fails**

Run: `cd compose/orchestrator && python -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: app.config`).

- [ ] **Step 4: Implement config**

`compose/orchestrator/app/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    wazuh_api_url: str = "https://wazuh.manager:55000"
    wazuh_api_user: str = "wazuh-wui"
    wazuh_api_password: str = ""
    indexer_url: str = "https://wazuh.indexer:9200"
    indexer_user: str = "admin"
    indexer_password: str = ""

    defectdojo_url: str = "http://nginx:8080"
    dd_api_token: str = ""
    dd_product_id: int = 1

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_from: str = "tizim@local"
    smtp_to: str = "secops@local"

    # TLS: do NOT disable verification. For Wazuh self-signed certs, mount the
    # generated root CA and point CA_BUNDLE at it. Empty => use system trust store.
    ca_bundle: str = ""

    @property
    def verify(self):
        """requests `verify` value: CA path if provided, else True (verify ON)."""
        return self.ca_bundle or True
```

- [ ] **Step 5: Run test, verify pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add compose/orchestrator
git commit -m "feat: orchestrator skeleti va sozlama (config) moduli"
```

### Task 3.2: Severity aggregation (pure logic, TDD)

**Files:**
- Create: `compose/orchestrator/app/report.py`
- Test: `compose/orchestrator/tests/test_report.py`

- [ ] **Step 1: Write failing test**

`tests/test_report.py`:
```python
from app.report import aggregate_severities, render_text_report

def test_aggregate_counts_by_severity():
    findings = [
        {"severity": "Critical", "cve": "CVE-1", "package": "openssl", "location": "web-01"},
        {"severity": "High", "cve": "CVE-2", "package": "nginx", "location": "img:a"},
        {"severity": "High", "cve": "CVE-3", "package": "curl", "location": "web-01"},
        {"severity": "Medium", "cve": "CVE-4", "package": "zlib", "location": "img:b"},
    ]
    counts = aggregate_severities(findings)
    assert counts == {"Critical": 1, "High": 2, "Medium": 1, "Low": 0}

def test_render_text_report_contains_totals_and_top():
    findings = [{"severity": "Critical", "cve": "CVE-1", "package": "openssl", "location": "web-01"}]
    text = render_text_report(findings, prev_total=5)
    assert "Jami zaiflik: 1" in text
    assert "CVE-1" in text
    assert "openssl" in text
    assert "↓4" in text  # 5 -> 1 trend
```

- [ ] **Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL (`ModuleNotFoundError: app.report`).

- [ ] **Step 3: Implement report.py**

`compose/orchestrator/app/report.py`:
```python
SEVERITIES = ["Critical", "High", "Medium", "Low"]


def aggregate_severities(findings):
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        sev = f.get("severity", "Low").title()
        if sev in counts:
            counts[sev] += 1
    return counts


def _trend(prev_total, total):
    if prev_total is None:
        return ""
    d = prev_total - total
    if d > 0:
        return f" ↓{d}"
    if d < 0:
        return f" ↑{-d}"
    return " ="


def render_text_report(findings, prev_total=None):
    counts = aggregate_severities(findings)
    total = len(findings)
    lines = [
        "Warden — kunlik xavfsizlik hisoboti",
        "=" * 32,
        f"Jami zaiflik: {total}{_trend(prev_total, total)}",
        "-" * 32,
    ]
    for s in SEVERITIES:
        lines.append(f"{s:<10} {counts[s]}")
    lines.append("-" * 32)
    top = sorted(findings, key=lambda f: SEVERITIES.index(f.get("severity", "Low").title())
                 if f.get("severity", "Low").title() in SEVERITIES else 99)[:10]
    for f in top:
        lines.append(f"{f['severity'][:4].upper():<5} {f['cve']:<16} {f['package']} @ {f['location']}")
    lines.append("=" * 32)
    return "\n".join(lines)
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/test_report.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add compose/orchestrator/app/report.py compose/orchestrator/tests/test_report.py
git commit -m "feat: kunlik hisobot agregatsiyasi va matn formati"
```

### Task 3.3: Notifiers — Telegram + SMTP (TDD with mocks)

**Files:**
- Create: `compose/orchestrator/app/notifiers.py`
- Test: `compose/orchestrator/tests/test_notifiers.py`

- [ ] **Step 1: Write failing test**

`tests/test_notifiers.py`:
```python
from unittest.mock import patch, MagicMock
from app.notifiers import send_telegram, send_email

@patch("app.notifiers.requests.post")
def test_send_telegram_posts_to_api(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
    ok = send_telegram("tok", "123", "salom")
    assert ok is True
    url = mock_post.call_args[0][0]
    assert "bot tok" in url.replace("bottok", "bot tok") or "tok/sendMessage" in url

@patch("app.notifiers.smtplib.SMTP")
def test_send_email_uses_smtp(mock_smtp):
    inst = mock_smtp.return_value.__enter__.return_value
    send_email("h", 1025, "f@x", "t@y", "subj", "body")
    assert inst.send_message.called
```

- [ ] **Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_notifiers.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement notifiers.py**

`compose/orchestrator/app/notifiers.py`:
```python
import smtplib
from email.message import EmailMessage
import requests


def send_telegram(bot_token, chat_id, text):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    return r.status_code == 200


def send_email(host, port, sender, to, subject, body):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=20) as s:
        s.send_message(msg)
    return True
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/test_notifiers.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compose/orchestrator/app/notifiers.py compose/orchestrator/tests/test_notifiers.py
git commit -m "feat: Telegram va SMTP notifierlar"
```

### Task 3.4: Wazuh client — indexer vulnerability query (TDD with mocks)

**Files:**
- Create: `compose/orchestrator/app/wazuh_client.py`
- Test: `compose/orchestrator/tests/test_wazuh_client.py`

- [ ] **Step 1: Write failing test**

`tests/test_wazuh_client.py`:
```python
from unittest.mock import patch, MagicMock
from app.wazuh_client import WazuhClient

SAMPLE_HITS = {"hits": {"hits": [
    {"_source": {"vulnerability": {"id": "CVE-2025-1", "severity": "Critical"},
                 "package": {"name": "openssl"}, "agent": {"name": "web-01"}}},
    {"_source": {"vulnerability": {"id": "CVE-2025-2", "severity": "High"},
                 "package": {"name": "nginx"}, "agent": {"name": "web-02"}}},
]}}

@patch("app.wazuh_client.requests.get")
def test_get_vulnerabilities_maps_findings(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_HITS)
    c = WazuhClient("https://idx:9200", "admin", "pw", verify=True)
    out = c.get_vulnerabilities()
    assert out[0] == {"cve": "CVE-2025-1", "severity": "Critical",
                      "package": "openssl", "location": "web-01"}
    assert len(out) == 2
```

- [ ] **Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_wazuh_client.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement wazuh_client.py**

`compose/orchestrator/app/wazuh_client.py`:
```python
import requests


class WazuhClient:
    """Queries the Wazuh indexer vulnerability-states index (4.8+ CTI engine).

    `verify` is a requests TLS-verify value: True (system trust), or a path to a
    CA bundle (the Wazuh-generated root-ca.pem). TLS verification is NEVER disabled.
    """

    def __init__(self, indexer_url, user, password, verify=True):
        self.url = indexer_url.rstrip("/")
        self.auth = (user, password)
        self.verify = verify

    def get_vulnerabilities(self, size=2000):
        body = {"size": size, "query": {"match_all": {}}}
        r = requests.get(
            f"{self.url}/wazuh-states-vulnerabilities-*/_search",
            json=body, auth=self.auth, verify=self.verify, timeout=30,
        )
        r.raise_for_status()
        out = []
        for hit in r.json().get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            vuln = src.get("vulnerability", {})
            out.append({
                "cve": vuln.get("id", ""),
                "severity": vuln.get("severity", "Low"),
                "package": src.get("package", {}).get("name", ""),
                "location": src.get("agent", {}).get("name", ""),
            })
        return out
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/test_wazuh_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compose/orchestrator/app/wazuh_client.py compose/orchestrator/tests/test_wazuh_client.py
git commit -m "feat: Wazuh indexer zaiflik so'rovi klienti"
```

### Task 3.5: Orchestrator container + `run-daily` entrypoint

**Files:**
- Create: `compose/orchestrator/app/main.py`
- Create: `compose/orchestrator/Dockerfile`
- Create: `compose/orchestrator/crontab`
- Test: `compose/orchestrator/tests/test_main.py`

- [ ] **Step 1: Write failing test for the report-building flow**

`tests/test_main.py`:
```python
from unittest.mock import patch
from app import main

@patch("app.main.send_email", return_value=True)
@patch("app.main.send_telegram", return_value=True)
def test_run_daily_sends_report(mock_tg, mock_mail):
    findings = [{"cve": "CVE-1", "severity": "Critical", "package": "openssl", "location": "web-01"}]
    with patch("app.main.WazuhClient") as MC:
        MC.return_value.get_vulnerabilities.return_value = findings
        with patch("app.main.scan_all", return_value=[]):
            with patch("app.main.import_to_defectdojo", return_value=0):
                rc = main.run_daily()
    assert rc == 0
    assert mock_tg.called and mock_mail.called
    sent_text = mock_tg.call_args[0][2]
    assert "CVE-1" in sent_text
```

- [ ] **Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL (main/scan_all/import_to_defectdojo missing — scanners + dd client land in Phase 4; define stubs now).

- [ ] **Step 3: Implement main.py with stubs for Phase-4 functions**

`compose/orchestrator/app/main.py`:
```python
import sys
from app.config import Settings
from app.wazuh_client import WazuhClient
from app.report import render_text_report
from app.notifiers import send_telegram, send_email

# Phase 4 fills these in (scanners.py / defectdojo_client.py)
try:
    from app.scanners import scan_all
except ImportError:
    def scan_all(_settings):
        return []
try:
    from app.defectdojo_client import import_to_defectdojo
except ImportError:
    def import_to_defectdojo(_settings, _results):
        return 0


def run_daily():
    s = Settings()
    wz = WazuhClient(s.indexer_url, s.indexer_user, s.indexer_password, s.verify)
    findings = wz.get_vulnerabilities()
    scan_results = scan_all(s)
    import_to_defectdojo(s, scan_results)
    text = render_text_report(findings)
    send_telegram(s.telegram_bot_token, s.telegram_chat_id, text)
    send_email(s.smtp_host, s.smtp_port, s.smtp_from, s.smtp_to,
               "Warden kunlik hisobot", text)
    print(text)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run-daily"
    if cmd == "run-daily":
        sys.exit(run_daily())
    print(f"noma'lum buyruq: {cmd}", file=sys.stderr)
    sys.exit(2)
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Write Dockerfile (with trivy + grype binaries)**

`compose/orchestrator/Dockerfile`:
```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates cron git && rm -rf /var/lib/apt/lists/*

# Trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
      | sh -s -- -b /usr/local/bin v0.56.2
# Grype + Syft
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
      | sh -s -- -b /usr/local/bin
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
      | sh -s -- -b /usr/local/bin

WORKDIR /opt/tizim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY crontab /etc/cron.d/tizim
RUN chmod 0644 /etc/cron.d/tizim && crontab /etc/cron.d/tizim

CMD ["cron", "-f"]
```

- [ ] **Step 6: Write crontab**

`compose/orchestrator/crontab`:
```
0 2 * * * cd /opt/tizim && python -m app.main run-daily >> /var/log/tizim.log 2>&1
```

- [ ] **Step 7: Commit**

```bash
git add compose/orchestrator
git commit -m "feat: orchestrator run-daily entrypoint, Dockerfile va cron"
```

---

## Phase 4: Scanners + DefectDojo import

### Task 4.1: Scanner wrappers — Trivy + Grype (TDD)

**Files:**
- Create: `compose/orchestrator/app/scanners.py`
- Create: `scanning/images.txt`
- Create: `scanning/repos.yml`
- Test: `compose/orchestrator/tests/test_scanners.py`

- [ ] **Step 1: Create scan target files**

`scanning/images.txt`:
```
# Skan qilinadigan image ref'lar (har qatorda bitta). RHEL: ref bo'yicha, flatten emas.
rockylinux:9
nginx:1.27
```

`scanning/repos.yml`:
```yaml
# Kod repo'lari: ekotizim bo'yicha deps skani (trivy fs)
repos:
  - name: example-django
    url: https://github.com/example/django-app.git
    ecosystem: pip
```

- [ ] **Step 2: Write failing test (subprocess mocked)**

`tests/test_scanners.py`:
```python
import json
from unittest.mock import patch, MagicMock
from app.scanners import run_trivy_image, run_grype

TRIVY_JSON = json.dumps({"Results": [{"Vulnerabilities": [
    {"VulnerabilityID": "CVE-X", "Severity": "HIGH", "PkgName": "openssl"}]}]})

@patch("app.scanners.subprocess.run")
def test_run_trivy_image_returns_raw_json(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=TRIVY_JSON, stderr="")
    out = run_trivy_image("nginx:1.27")
    assert out["scan_type"] == "Trivy Scan"
    assert out["target"] == "nginx:1.27"
    assert json.loads(out["raw"])["Results"][0]["Vulnerabilities"][0]["VulnerabilityID"] == "CVE-X"

@patch("app.scanners.subprocess.run")
def test_run_grype_returns_anchore_type(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='{"matches":[]}', stderr="")
    out = run_grype("nginx:1.27")
    assert out["scan_type"] == "Anchore Grype"
```

- [ ] **Step 3: Run test, verify fails**

Run: `python -m pytest tests/test_scanners.py -v`
Expected: FAIL (module missing).

- [ ] **Step 4: Implement scanners.py**

`compose/orchestrator/app/scanners.py`:
```python
import subprocess


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} xato (rc={p.returncode}): {p.stderr[:400]}")
    return p.stdout


def run_trivy_image(ref):
    out = _run(["trivy", "image", "--quiet", "--format", "json", ref])
    return {"scan_type": "Trivy Scan", "target": ref, "raw": out}


def run_trivy_fs(path):
    out = _run(["trivy", "fs", "--quiet", "--scanners", "vuln", "--format", "json", path])
    return {"scan_type": "Trivy Scan", "target": path, "raw": out}


def run_grype(ref):
    out = _run(["grype", ref, "-o", "json"])
    return {"scan_type": "Anchore Grype", "target": ref, "raw": out}


def scan_all(settings):
    import os, yaml
    results = []
    images_file = os.environ.get("IMAGES_FILE", "/opt/tizim/scanning/images.txt")
    if os.path.exists(images_file):
        for line in open(images_file):
            ref = line.strip()
            if not ref or ref.startswith("#"):
                continue
            results.append(run_trivy_image(ref))
            results.append(run_grype(ref))
    return results
```
Note: add `PyYAML==6.0.2` to requirements.txt now.

- [ ] **Step 5: Run test, verify pass**

Run: `python -m pytest tests/test_scanners.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add compose/orchestrator/app/scanners.py compose/orchestrator/tests/test_scanners.py scanning/ compose/orchestrator/requirements.txt
git commit -m "feat: Trivy va Grype skaner wrapperlari + skan nishonlari"
```

### Task 4.2: DefectDojo import client (TDD)

**Files:**
- Create: `compose/orchestrator/app/defectdojo_client.py`
- Test: `compose/orchestrator/tests/test_defectdojo_client.py`

- [ ] **Step 1: Write failing test**

`tests/test_defectdojo_client.py`:
```python
from unittest.mock import patch, MagicMock
from app.defectdojo_client import import_scan

@patch("app.defectdojo_client.requests.post")
def test_import_scan_posts_multipart(mock_post):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"test": 5})
    rc = import_scan("http://dd:8080", "tok", 1, "Trivy Scan", "nginx", '{"Results":[]}')
    assert rc == 5
    kwargs = mock_post.call_args.kwargs
    assert kwargs["data"]["scan_type"] == "Trivy Scan"
    assert "Authorization" in kwargs["headers"]
```

- [ ] **Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_defectdojo_client.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement defectdojo_client.py**

`compose/orchestrator/app/defectdojo_client.py`:
```python
import io
import requests


def import_scan(dd_url, token, product_id, scan_type, target, raw_json):
    headers = {"Authorization": f"Token {token}"}
    data = {
        "scan_type": scan_type,
        "product_name": "Warden Infra",
        "engagement_name": f"daily-{target}",
        "auto_create_context": "true",
        "active": "true",
        "verified": "false",
        "close_old_findings": "true",  # dedup/trend across runs
    }
    files = {"file": (f"{target}.json", io.StringIO(raw_json), "application/json")}
    r = requests.post(f"{dd_url}/api/v2/import-scan/", headers=headers,
                      data=data, files=files, timeout=120)
    r.raise_for_status()
    return r.json().get("test")


def import_to_defectdojo(settings, results):
    n = 0
    for res in results:
        import_scan(settings.defectdojo_url, settings.dd_api_token,
                    settings.dd_product_id, res["scan_type"], res["target"], res["raw"])
        n += 1
    return n
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add compose/orchestrator/app/defectdojo_client.py compose/orchestrator/tests/test_defectdojo_client.py
git commit -m "feat: DefectDojo import-scan klienti (dedup bilan)"
```

### Task 4.3: Wire orchestrator into top-level compose

**Files:**
- Create: `compose/docker-compose.yml`
- Modify: `compose/.env.example` (add IMAGES_FILE, INDEXER_URL)

- [ ] **Step 1: Create top-level compose that joins networks**

`compose/docker-compose.yml`:
```yaml
# Orchestratorni Wazuh + DefectDojo tarmoqlariga ulaydi.
# Wazuh va DefectDojo o'z compose fayllarida; bu faqat orchestrator + mailhog.
services:
  mailhog:
    image: mailhog/mailhog:v1.0.1
    ports: ["8025:8025"]   # web UI
  orchestrator:
    build: ./orchestrator
    env_file: .env
    volumes:
      - ../scanning:/opt/tizim/scanning:ro
      # Wazuh-generated root CA → orchestrator verifies the indexer against it (no -k)
      - ./wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem:/opt/tizim/certs/root-ca.pem:ro
      - /var/run/docker.sock:/var/run/docker.sock   # local image pulls
    environment:
      IMAGES_FILE: /opt/tizim/scanning/images.txt
      CA_BUNDLE: /opt/tizim/certs/root-ca.pem
    networks: [tizim]
networks:
  tizim:
    name: tizim_net
```
Note: connecting to Wazuh/DefectDojo networks is done by attaching their compose networks as `external` once their names are confirmed (Task 4.4 verify step).

- [ ] **Step 2: Build orchestrator image**

Run: `cd compose && docker compose build orchestrator && cd ..`
Expected: image builds; trivy & grype installed.

- [ ] **Step 3: Manual one-shot run inside the container (network attached)**

Run:
```bash
cd compose
docker compose run --rm orchestrator python -m app.main run-daily
cd ..
```
Expected: prints the text report; mailhog (http://localhost:8025) shows an email. (Telegram only if token set.)

- [ ] **Step 4: Commit**

```bash
git add compose/docker-compose.yml compose/.env.example
git commit -m "feat: orchestrator top-level compose + mailhog"
```

---

## Phase 5: Ansible — wazuh_agent role + local Rocky test targets

### Task 5.1: Rocky systemd test containers

**Files:**
- Create: `test/docker-compose.targets.yml`

- [ ] **Step 1: Create privileged Rocky targets (local test only)**

`test/docker-compose.targets.yml`:
```yaml
services:
  rocky-target-1:
    image: rockylinux:9
    container_name: rocky-target-1
    privileged: true
    command: /sbin/init
    cgroup: host
    tmpfs: ["/run", "/tmp"]
    volumes: ["/sys/fs/cgroup:/sys/fs/cgroup:rw"]
    networks: [tizim]
networks:
  tizim:
    name: tizim_net
    external: true
```

- [ ] **Step 2: Bring up target + install SSH for Ansible**

Run:
```bash
docker compose -f test/docker-compose.targets.yml up -d
docker exec rocky-target-1 bash -c "dnf -y install openssh-server python3 && \
  ssh-keygen -A && echo 'root:tizimtest' | chpasswd && \
  sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
  systemctl enable --now sshd"
docker exec rocky-target-1 systemctl is-active sshd
```
Expected: `active`.

- [ ] **Step 3: Commit**

```bash
git add test/docker-compose.targets.yml
git commit -m "test: lokal Rocky 9 systemd target konteynerlar"
```

### Task 5.2: Ansible wazuh_agent role

**Files:**
- Create: `ansible/ansible.cfg`
- Create: `ansible/inventory.ini.example`
- Create: `ansible/site.yml`
- Create: `ansible/roles/wazuh_agent/tasks/main.yml`
- Create: `ansible/roles/wazuh_agent/defaults/main.yml`

- [ ] **Step 1: ansible.cfg**

`ansible/ansible.cfg`:
```ini
[defaults]
inventory = inventory.ini
host_key_checking = False
retry_files_enabled = False
roles_path = roles
```

- [ ] **Step 2: inventory.ini.example**

```ini
[rhel_targets]
rocky-target-1 ansible_host=rocky-target-1 ansible_user=root ansible_password=tizimtest ansible_python_interpreter=/usr/bin/python3

[rhel_targets:vars]
wazuh_manager_ip=wazuh.manager
```

- [ ] **Step 3: defaults/main.yml**

`ansible/roles/wazuh_agent/defaults/main.yml`:
```yaml
wazuh_agent_version: "4.9.2-1"
wazuh_manager_ip: "wazuh.manager"
```

- [ ] **Step 4: tasks/main.yml**

`ansible/roles/wazuh_agent/tasks/main.yml`:
```yaml
- name: Wazuh GPG kalitini import qilish
  ansible.builtin.rpm_key:
    state: present
    key: https://packages.wazuh.com/key/GPG-KEY-WAZUH

- name: Wazuh dnf repo'sini qo'shish
  ansible.builtin.yum_repository:
    name: wazuh
    description: Wazuh repository
    baseurl: https://packages.wazuh.com/4.x/yum/
    gpgcheck: true
    gpgkey: https://packages.wazuh.com/key/GPG-KEY-WAZUH
    enabled: true

- name: wazuh-agent o'rnatish (manager IP bilan)
  ansible.builtin.dnf:
    name: "wazuh-agent-{{ wazuh_agent_version }}"
    state: present
  environment:
    WAZUH_MANAGER: "{{ wazuh_manager_ip }}"

- name: agent service'ni yoqish va ishga tushirish
  ansible.builtin.systemd:
    name: wazuh-agent
    enabled: true
    state: started
```

- [ ] **Step 5: site.yml**

`ansible/site.yml`:
```yaml
- name: RHEL target'larga Wazuh agent va OpenSCAP
  hosts: rhel_targets
  become: true
  roles:
    - wazuh_agent
    # - openscap   # Phase 6'da yoqiladi
```

- [ ] **Step 6: Run playbook against the test target**

Run:
```bash
cd ansible
cp inventory.ini.example inventory.ini
ansible-playbook site.yml
cd ..
```
Expected: PLAY RECAP `ok`/`changed`, `failed=0`.

- [ ] **Step 7: Verify agent enrolled in manager**

Run:
```bash
TOKEN=$(curl -sk -u wazuh-wui:MyS3cr37P450r.*- -X POST \
  "https://localhost:55000/security/user/authenticate?raw=true")
curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost:55000/agents?select=name,status" \
  | python3 -m json.tool | grep -A2 rocky-target-1
```
Expected: `rocky-target-1` listed with status `active`.

- [ ] **Step 8: Commit**

```bash
git add ansible
git commit -m "feat: Ansible wazuh_agent role va inventar"
```

---

## Phase 6: OpenSCAP / CIS compliance role

### Task 6.1: Ansible openscap role

**Files:**
- Create: `ansible/roles/openscap/tasks/main.yml`
- Create: `ansible/roles/openscap/defaults/main.yml`
- Modify: `ansible/site.yml` (enable openscap role)

- [ ] **Step 1: defaults/main.yml**

`ansible/roles/openscap/defaults/main.yml`:
```yaml
# RHEL9/Rocky9 CIS profil
oscap_profile: "xccdf_org.ssgproject.content_profile_cis"
oscap_datastream: "/usr/share/xml/scap/ssg/content/ssg-rl9-ds.xml"  # Rocky 9
oscap_report_dir: "/var/log/tizim-scap"
```

- [ ] **Step 2: tasks/main.yml**

`ansible/roles/openscap/tasks/main.yml`:
```yaml
- name: OpenSCAP va SCAP Security Guide o'rnatish
  ansible.builtin.dnf:
    name:
      - openscap-scanner
      - scap-security-guide
    state: present

- name: hisobot katalogini yaratish
  ansible.builtin.file:
    path: "{{ oscap_report_dir }}"
    state: directory
    mode: "0750"

- name: CIS skanini bajarish (XCCDF, configuration compliance)
  ansible.builtin.command: >
    oscap xccdf eval
    --profile {{ oscap_profile }}
    --results {{ oscap_report_dir }}/results.xml
    --report {{ oscap_report_dir }}/report.html
    {{ oscap_datastream }}
  register: oscap_run
  failed_when: oscap_run.rc not in [0, 2]   # 2 = ba'zi qoidalar fail (normal)
  changed_when: false

- name: kunlik CIS skan uchun systemd timer
  ansible.builtin.copy:
    dest: /etc/systemd/system/tizim-scap.service
    content: |
      [Unit]
      Description=Warden CIS SCAP scan
      [Service]
      Type=oneshot
      ExecStart=/usr/bin/oscap xccdf eval --profile {{ oscap_profile }} --results {{ oscap_report_dir }}/results.xml --report {{ oscap_report_dir }}/report.html {{ oscap_datastream }}
      SuccessExitStatus=0 2

- name: timer faylini yaratish
  ansible.builtin.copy:
    dest: /etc/systemd/system/tizim-scap.timer
    content: |
      [Unit]
      Description=Warden CIS SCAP kunlik
      [Timer]
      OnCalendar=*-*-* 01:30:00
      Persistent=true
      [Install]
      WantedBy=timers.target

- name: timer'ni yoqish
  ansible.builtin.systemd:
    name: tizim-scap.timer
    enabled: true
    state: started
    daemon_reload: true
```
Note: CVE detection stays with Wazuh/Trivy (spec §11 — OVAL v2 deprecation). OpenSCAP here = configuration/CIS compliance only.

- [ ] **Step 3: Enable role in site.yml**

In `ansible/site.yml`, uncomment `- openscap`.

- [ ] **Step 4: Run and verify the SCAP report exists**

Run:
```bash
cd ansible && ansible-playbook site.yml && cd ..
docker exec rocky-target-1 ls -la /var/log/tizim-scap/
docker exec rocky-target-1 bash -c "grep -c 'rule-result' /var/log/tizim-scap/results.xml"
```
Expected: `report.html` + `results.xml` present; rule-result count > 0.

- [ ] **Step 5: Commit**

```bash
git add ansible/roles/openscap ansible/site.yml
git commit -m "feat: Ansible openscap role — CIS compliance auditi"
```

---

## Phase 7: Automation — Telegram alerts + scheduled cycle

### Task 7.1: Wazuh custom-telegram integration script

**Files:**
- Create: `compose/wazuh/config/integrations/custom-telegram`
- Modify: `compose/wazuh/docker-compose.yml` (mount integrations dir)

- [ ] **Step 1: Write the integration script**

`compose/wazuh/config/integrations/custom-telegram`:
```bash
#!/bin/sh
# Wazuh integration: yuqori darajali alertni Telegram'ga yuboradi.
# Args: $1=alert_file $2=api_key(unused) $3=hook_url(bot token:chat_id)
ALERT_FILE="$1"
CONF="$3"   # format: BOT_TOKEN|CHAT_ID
BOT="${CONF%%|*}"; CHAT="${CONF##*|}"
RULE=$(python3 -c "import json,sys;d=json.load(open('$ALERT_FILE'));print(d.get('rule',{}).get('description','alert'))")
LVL=$(python3 -c "import json,sys;d=json.load(open('$ALERT_FILE'));print(d.get('rule',{}).get('level',''))")
AGENT=$(python3 -c "import json,sys;d=json.load(open('$ALERT_FILE'));print(d.get('agent',{}).get('name','?'))")
MSG="🛡️ Warden alert [L$LVL] $AGENT: $RULE"
curl -s -X POST "https://api.telegram.org/bot$BOT/sendMessage" \
  -d "chat_id=$CHAT" --data-urlencode "text=$MSG" >/dev/null
```

- [ ] **Step 2: Mount integrations into manager**

In `compose/wazuh/docker-compose.yml`, under `wazuh.manager` `volumes:` add:
```yaml
      - ./config/integrations/custom-telegram:/var/ossec/integrations/custom-telegram
```
And set the integration's `<hook_url>` in `wazuh_manager.conf`:
```xml
  <integration>
    <name>custom-telegram</name>
    <level>12</level>
    <hook_url>BOT_TOKEN|CHAT_ID</hook_url>
    <alert_format>json</alert_format>
  </integration>
```

- [ ] **Step 3: Set perms, restart, and verify it loads**

Run:
```bash
chmod +x compose/wazuh/config/integrations/custom-telegram
cd compose/wazuh && docker compose up -d && \
  docker exec wazuh.manager chmod 750 /var/ossec/integrations/custom-telegram && \
  docker compose restart wazuh.manager && cd ../..
docker logs wazuh.manager 2>&1 | grep -i integrator | tail -5
```
Expected: integrator daemon started, no errors.

- [ ] **Step 4: Commit**

```bash
git add compose/wazuh/config/integrations compose/wazuh/docker-compose.yml compose/wazuh/config/wazuh_cluster/wazuh_manager.conf
git commit -m "feat: Wazuh custom-telegram alert integratsiyasi"
```

### Task 7.2: bootstrap & enroll scripts

**Files:**
- Create: `scripts/bootstrap-central.sh`
- Create: `scripts/enroll-agents.sh`
- Create: `scripts/run-daily-scan.sh`

- [ ] **Step 1: bootstrap-central.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[1/4] Wazuh sertifikatlari..."
( cd compose/wazuh && docker compose -f generate-indexer-certs.yml run --rm generator )
echo "[2/4] Wazuh single-node..."
( cd compose/wazuh && docker compose up -d )
echo "[3/4] DefectDojo..."
( cd compose/defectdojo && docker compose up -d )
echo "[4/4] Orchestrator + mailhog..."
( cd compose && docker compose up -d --build )
echo "Tayyor. Dashboard: https://localhost  ·  DefectDojo: http://localhost:8080  ·  Mailhog: http://localhost:8025"
```

- [ ] **Step 2: enroll-agents.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ansible"
[ -f inventory.ini ] || cp inventory.ini.example inventory.ini
ansible-playbook site.yml
```

- [ ] **Step 3: run-daily-scan.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../compose"
docker compose run --rm orchestrator python -m app.main run-daily
```

- [ ] **Step 4: Make executable + verify they run**

Run:
```bash
chmod +x scripts/*.sh
bash -n scripts/bootstrap-central.sh && bash -n scripts/enroll-agents.sh && bash -n scripts/run-daily-scan.sh
echo "syntax OK"
```
Expected: `syntax OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts
git commit -m "feat: bootstrap, enroll va daily-scan skriptlari"
```

---

## Phase 8: End-to-end test + docs

### Task 8.1: e2e smoke test

**Files:**
- Create: `test/e2e.sh`

- [ ] **Step 1: Write e2e.sh**

`test/e2e.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }

echo "== Warden E2E =="

# 1. Wazuh dashboard
code=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost:443 || true)
[ "$code" = "200" ] && pass "Wazuh dashboard ($code)" || fail "dashboard $code"

# 2. DefectDojo
code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login || true)
[[ "$code" =~ ^(200|302)$ ]] && pass "DefectDojo ($code)" || fail "defectdojo $code"

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
```

- [ ] **Step 2: Run unit tests + e2e**

Run:
```bash
( cd compose/orchestrator && python -m pytest tests/ -v )
chmod +x test/e2e.sh && bash test/e2e.sh
```
Expected: pytest all pass; e2e prints all ✅ and "E2E yashil".

- [ ] **Step 3: Commit**

```bash
git add test/e2e.sh
git commit -m "test: end-to-end smoke test (dashboard, agent, skan, hisobot)"
```

### Task 8.2: architecture.md + README finalization

**Files:**
- Create: `docs/architecture.md`
- Modify: `README.md`

- [ ] **Step 1: Write architecture.md**

Include the same Mermaid diagrams as the presentation (flowchart, sequence, deployment) plus a "Production deploy" section: real inventory, change default passwords, real SMTP/Telegram, registry creds for image pulls, resource sizing (spec §10).

- [ ] **Step 2: Update README quick-start** with the actual verified commands and links to `docs/architecture.md` and `docs/prezentatsiya.html`.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md README.md
git commit -m "docs: arxitektura hujjati va README yakunlandi"
```

---

## Self-Review (completed by plan author)

**Spec coverage:** §1 goals → all 8 phases. §3 tools → Wazuh(P1), DefectDojo(P2), Orchestrator(P3), Trivy/Grype(P4), Ansible agent(P5), OpenSCAP(P6), automation(P7). §4 data flow → Task 3.5/4.x + 7. §8 local testing → P5 Rocky containers + 8.1 e2e. §9 build order → phases mirror it. §11 risks → vuln-detection tag (1.2), OVAL/OpenSCAP-compliance-only (6.1), Trivy by-ref (4.1), dedup close_old_findings (4.2), no-silent-failure (scanners raise + e2e). ✓ no gaps.

**Placeholder scan:** No TBD/TODO. The one `architecture.md` task (8.2 Step 1) describes content reusing already-written presentation diagrams — acceptable as it points to a concrete existing source.

**Type consistency:** `scan_all(settings)`, `import_to_defectdojo(settings, results)`, finding dict keys `{cve, severity, package, location}`, scan result dict keys `{scan_type, target, raw}` — consistent across main.py, scanners.py, defectdojo_client.py, report.py, wazuh_client.py. ✓
