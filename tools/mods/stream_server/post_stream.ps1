param([Parameter(Mandatory)][string]$Path)

$bytes = [System.IO.File]::ReadAllBytes($Path)
Invoke-WebRequest -Uri "http://127.0.0.1:6742/stream" -Method Post -Body $bytes -ContentType "application/octet-stream"
