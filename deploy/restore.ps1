param(
    [Parameter(Mandatory=$true)][string]$BackupFile,
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) {
    throw "Restore is destructive. Re-run with -ConfirmRestore after verifying the backup and target environment."
}
if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
    throw "Backup file does not exist"
}

Get-Content -LiteralPath $BackupFile -Encoding Byte | docker-compose -f deploy/docker-compose.yml exec -T postgres pg_restore -U assistant -d assistant --clean --if-exists
Write-Output "Restore completed from $BackupFile"
