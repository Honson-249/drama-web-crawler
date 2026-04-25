#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> pulling latest code..."
git pull origin master

echo "==> rebuilding and starting containers..."
docker compose -f docker-compose.test.yml build --pull
docker compose -f docker-compose.test.yml up -d

echo "==> done. verify:"
docker compose -f docker-compose.test.yml ps
echo "==> logs: docker compose -f docker-compose.test.yml logs -f"
