# TIZIM — Ichki Xavfsizlik Monitoring Platformasi

Self-hosted, ochiq kodli xavfsizlik monitoring stek: **Wazuh** (markaz) +
**Trivy/Grype** (konteyner & kod skani) + **DefectDojo** (agregatsiya) +
**OpenSCAP** (CIS compliance). Har kuni avtomatik xavfsizlik hisoboti.

## Tezkor boshlash (lokal sinov)
```bash
cp compose/.env.example compose/.env                          # orchestrator sozlamalari
cp compose/defectdojo/.env.example compose/defectdojo/.env    # MAJBURIY maxfiy kalitlarni to'ldiring
bash scripts/bootstrap-central.sh      # Wazuh + DefectDojo + orchestrator (tizim_net)
docker compose -f test/docker-compose.targets.yml up -d       # soxta Rocky agent (sinov)
bash scripts/enroll-agents.sh          # Ansible: agent + openscap
bash test/e2e.sh                        # end-to-end smoke test
```
⚠️ To'liq stek ~10–12 GB RAM talab qiladi. Kam RAM'da Wazuh va DefectDojo navbatma-navbat.

## Tuzilma
- `compose/` — markaziy stek (Docker Compose)
- `ansible/` — RHEL target'larga agent + openscap
- `scanning/` — skan qilinadigan image/repo ro'yxati
- `scripts/` — bootstrap, enroll, daily-scan
- `test/` — lokal e2e (Rocky systemd konteynerlar)
- `docs/` — spec, arxitektura, prezentatsiya

## Hujjatlar
- **Production readiness + deploy runbook + checklist**: [`docs/PROD-READINESS.md`](docs/PROD-READINESS.md)
- Arxitektura + diagrammalar: [`docs/architecture.md`](docs/architecture.md)
- To'liq spetsifikatsiya: [`docs/specs/2026-05-29-tizim-design.md`](docs/specs/2026-05-29-tizim-design.md)
- Implementatsiya rejasi: [`docs/plans/2026-05-29-tizim-build.md`](docs/plans/2026-05-29-tizim-build.md)
- Rahbariyat taqdimoti: [`docs/prezentatsiya.html`](docs/prezentatsiya.html)

## Test
```bash
cd compose/orchestrator && python -m pytest tests/ -q   # orchestrator unit testlar (11)
```
