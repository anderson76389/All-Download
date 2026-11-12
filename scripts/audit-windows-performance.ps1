# Read-only resource profiling for All-Download Windows.
# Run once at idle and again while a public, authorized test download is active.
param(
    [ValidateRange(2, 120)][int]$Samples = 18,
    [ValidateRange(2, 60)][int]$IntervalSeconds = 10,
    [ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$ProcessName = "All_Media_Download"
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$directory = Join-Path $root "Donnees\diagnostics"
New-Item -Path $directory -ItemType Directory -Force | Out-Null
$destination = Join-Path $directory ("windows-performance-{0}.csv" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$results = [System.Collections.Generic.List[object]]::new()
$lastPid = -1
$lastCpuSeconds = $null
for ($i = 1; $i -le $Samples; $i++) {
    $target = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Sort-Object WorkingSet64 -Descending | Select-Object -First 1
    $children = @()
    $cpuPercent = $null
    if ($null -ne $target) {
        try {
            # Parent and direct child processes, for detecting lingering tools.
            $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($target.Id)" -ErrorAction Stop |
                Select-Object -ExpandProperty Name)
        } catch {
            $children = @()
        }
        $cpuSeconds = if ($null -ne $target.CPU) { [double]$target.CPU } else { $null }
        if ($target.Id -eq $lastPid -and $null -ne $cpuSeconds -and $null -ne $lastCpuSeconds) {
            $cpuPercent = [Math]::Round(
                [Math]::Max(0, ($cpuSeconds - $lastCpuSeconds)) /
                ($IntervalSeconds * [Environment]::ProcessorCount) * 100, 2)
        }
        $lastPid = $target.Id
        $lastCpuSeconds = $cpuSeconds
    } else {
        $lastPid = -1
        $lastCpuSeconds = $null
    }
    $result = [pscustomobject]@{
        timestamp = (Get-Date).ToString("o")
        app_process_id = if ($target) { $target.Id } else { $null }
        private_memory_mib = if ($target) {
            [Math]::Round($target.PrivateMemorySize64 / 1MB, 2)
        } else { $null }
        working_set_mib = if ($target) {
            [Math]::Round($target.WorkingSet64 / 1MB, 2)
        } else { $null }
        cpu_percent_of_total = $cpuPercent
        handles = if ($target) { $target.HandleCount } else { $null }
        threads = if ($target) { $target.Threads.Count } else { $null }
        direct_children = ($children -join ", ")
    }
    $results.Add($result)
    Write-Host ("{0}/{1}: PID={2}, RAM={3} MiB, CPU={4}%, handles={5}, outils={6}" -f
        $i, $Samples, $result.app_process_id, $result.private_memory_mib,
        $result.cpu_percent_of_total, $result.handles, $result.direct_children)
    if ($i -lt $Samples) { Start-Sleep -Seconds $IntervalSeconds }
}
$results | Export-Csv -Path $destination -NoTypeInformation -Encoding UTF8
Write-Host "Rapport local CSV: $destination"
Write-Host "Comparez une session au repos, une session active et une session apres fermeture."
