#!/usr/bin/env bash
# Kunlik skan + hisobot siklini qo'lda ishga tushiradi.
set -euo pipefail
cd "$(dirname "$0")/../compose"
docker compose run --rm orchestrator python -m app.main run-daily
