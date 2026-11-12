# Read-only profiling on an Android phone connected through ADB.
# Run once at idle and again while All-Download downloads your own public test video.
param(
    [ValidateRange(2, 120)][int]$Samples = 18,
    [ValidateRange(2, 60)][int]$IntervalSeconds = 10,
    [string]$Package = "com.alldownload.android"
)
$ErrorActionPreference = "Stop"
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    throw "ADB introuvable. Installez Android Platform Tools et activez le debogage USB."
}
$devices = @(& adb devices | Select-String "^[^\s]+\s+device$")
if ($devices.Count -ne 1) {
    throw "Connectez et autorisez exactement un appareil avec adb devices."
}
$root = Split-Path $PSScriptRoot -Parent
$folder = Join-Path $root "Donnees\diagnostics"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$name = "android-performance-{0}.csv" -f (Get-Date -Format "yyyyMMdd-HHmmss")
$destination = Join-Path $folder $name
$results = [System.Collections.Generic.List[object]]::new()
for ($index = 1; $index -le $Samples; $index++) {
    $pidText = (& adb shell pidof $Package 2>$null | Out-String).Trim()
    $meminfo = (& adb shell dumpsys meminfo $Package 2>$null | Out-String)
    $match = [regex]::Match($meminfo, "(?m)^\s*TOTAL PSS:\s*(\d+)")
    $pss = if ($match.Success) { [int64]$match.Groups[1].Value } else { $null }
    $cpu = (& adb shell dumpsys cpuinfo 2>$null | Select-String -SimpleMatch $Package |
            Select-Object -First 1 | Out-String).Trim()
    $battery = (& adb shell dumpsys battery 2>$null | Out-String)
    $level = [regex]::Match($battery, "(?m)^\s*level:\s*(\d+)")
    $result = [pscustomobject]@{
        timestamp = (Get-Date).ToString("o")
        process_id = $pidText
        pss_kib = $pss
        cpuinfo_line = $cpu
        battery_level_percent = if ($level.Success) { [int]$level.Groups[1].Value } else { $null }
    }
    $results.Add($result)
    Write-Host ("{0}/{1}: PID={2} PSS={3} KiB Batterie={4}" -f
        $index, $Samples, $pidText, $pss, $result.battery_level_percent)
    if ($index -lt $Samples) { Start-Sleep -Seconds $IntervalSeconds }
}
$results | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $destination
Write-Host "Rapport local: $destination"
Write-Host "Comparez une session au repos et une session pendant un telechargement."
