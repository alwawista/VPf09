# Проверка Tor SOCKS для VPf09
param(
    [string]$SocksHost = "127.0.0.1",
    [int]$SocksPort = 9050,
    [int]$TimeoutSec = 20
)

$listening = netstat -ano | Select-String "LISTENING" | Select-String ":$SocksPort\s"
if (-not $listening) {
    Write-Host "Tor SOCKS is NOT listening on ${SocksHost}:$SocksPort"
    exit 1
}

Write-Host "Tor SOCKS is listening on ${SocksHost}:$SocksPort"
Write-Host "Checking https://check.torproject.org/api/ip via Tor ..."

$out = curl.exe -s --socks5-hostname "${SocksHost}:${SocksPort}" `
    "https://check.torproject.org/api/ip" --max-time $TimeoutSec 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL (exit $LASTEXITCODE): $out"
    Write-Host "Bootstrap likely incomplete. Check Tor log for Bootstrapped 100%."
    exit 2
}

Write-Host "OK: $out"
exit 0
