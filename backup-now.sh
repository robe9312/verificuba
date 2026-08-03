#!/bin/bash
cd "$(dirname "$0")/.."
docker compose exec -T postgres pg_dump -U nocodb verificuba | gzip > "backups/verificuba-$(date +%F-%H%M).sql.gz"
echo "Backup: backups/verificuba-$(date +%F-%H%M).sql.gz"
