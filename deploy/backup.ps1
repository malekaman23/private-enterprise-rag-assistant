param(
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutputDirectory "assistant-$stamp.sql"

docker-compose -f deploy/docker-compose.yml exec -T postgres pg_dump -U assistant -d assistant --format=custom | Set-Content -Encoding Byte -Path $target
Write-Output "Backup written to $target"
