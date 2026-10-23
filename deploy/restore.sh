#!/usr/bin/env sh
set -eu
if [ "${2:-}" != "--confirm-restore" ]; then
  echo "Destructive restore requires: $0 backup.dump --confirm-restore" >&2
  exit 2
fi
test -f "$1"
docker-compose -f deploy/docker-compose.yml exec -T postgres pg_restore -U assistant -d assistant --clean --if-exists < "$1"
echo "Restore completed from $1"
