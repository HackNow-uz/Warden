# TIZIM — Ichki Xavfsizlik Monitoring Platformasi

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
