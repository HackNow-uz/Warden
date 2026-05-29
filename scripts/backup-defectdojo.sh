#!/usr/bin/env bash
# DefectDojo Postgres DB + media backup. Cron tavsiya: 0 3 * * * (kunlik).
# Retention: BACKUP_KEEP_DAYS (default 14) kun.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${TIZIM_BACKUP_DIR:-/var/backups/tizim}"
KEEP="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$OUT"
TS=$(date +%Y%m%d-%H%M)

DBPASS=$(grep '^DD_DATABASE_PASSWORD=' compose/defectdojo/.env 2>/dev/null | cut -d= -f2-)
DBUSER=$(grep '^DD_DATABASE_USER=' compose/defectdojo/.env 2>/dev/null | cut -d= -f2-); DBUSER="${DBUSER:-defectdojo}"
DBNAME=$(grep '^DD_DATABASE_NAME=' compose/defectdojo/.env 2>/dev/null | cut -d= -f2-); DBNAME="${DBNAME:-defectdojo}"

PG=$(cd compose/defectdojo && docker compose ps -q postgres)
[ -n "$PG" ] || { echo "XATO: defectdojo postgres konteyneri topilmadi" >&2; exit 1; }

echo "[1/3] DB dump..."
docker exec -e PGPASSWORD="$DBPASS" "$PG" pg_dump -U "$DBUSER" "$DBNAME" | gzip > "$OUT/defectdojo-db-$TS.sql.gz"

echo "[2/3] media volume..."
docker run --rm -v defectdojo_media:/m:ro -v "$OUT":/b alpine \
  tar czf "/b/defectdojo-media-$TS.tgz" -C /m . 2>/dev/null || echo "  (media volume bo'sh yoki yo'q)"

echo "[3/3] ${KEEP} kundan eski backuplarni tozalash..."
find "$OUT" -name "defectdojo-*" -mtime +"$KEEP" -delete

echo "✓ Backup tayyor: $OUT (db + media), ${KEEP} kun rotation"
ls -lh "$OUT" | tail -4
