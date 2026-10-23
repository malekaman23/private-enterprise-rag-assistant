#!/usr/bin/env sh
set -eu
output_dir="${1:-backups}"
mkdir -p "$output_dir"
stamp="$(date -u +%Y%m%d-%H%M%S)"
target="$output_dir/assistant-$stamp.dump"
docker-compose -f deploy/docker-compose.yml exec -T postgres pg_dump -U assistant -d assistant --format=custom > "$target"
echo "Backup written to $target"
