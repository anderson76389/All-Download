# Comparatif A/B PyInstaller sur Windows : 8 demarrages froids par edition.
$ErrorActionPreference = "Stop"
$workspace = (Get-Location).Path
$out = Join-Path $workspace "startup-comparison"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class StartupProbe {
 [DllImport("user32.dll", SetLastError=true)]
 public static extern IntPtr SendMessageTimeout(IntPtr hwnd, uint msg, IntPtr w, IntPtr l,
     uint flags, uint timeout, out IntPtr result);
}
"@
$exes = @{
  onefile = Join-Path $workspace "dist/onefile/All_Media_Download.exe"
  onedir = Join-Path $workspace "dist/onedir/All_Media_Download/All_Media_Download.exe"
}
foreach ($mode in @("onefile","onedir")) {
  if (-not (Test-Path $exes[$mode] -PathType Leaf)) { throw "EXE $mode absent" }
}
function Stop-App {
  Get-Process -Name All_Media_Download -ErrorAction SilentlyContinue | ForEach-Object {
    try { if ($_.MainWindowHandle -ne [IntPtr]::Zero) { [void]$_.CloseMainWindow() } } catch {}
  }
  Start-Sleep -Milliseconds 900
  Get-Process -Name All_Media_Download -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
}
$results = [System.Collections.Generic.List[object]]::new()
try {
  for ($n=1; $n -le 8; $n++) {
    $order = if (($n % 2) -eq 1) { @("onefile","onedir") } else { @("onedir","onefile") }
    foreach ($mode in $order) {
      Stop-App
      $label = "$mode-$n"
      $exe = $exes[$mode]
      $root = Split-Path $exe -Parent
      $data = Join-Path $root "Donnees"
      $profile = Join-Path $out "profile-$label"
      $trace = Join-Path $data "startup_log.txt"
      if (Test-Path $data) { Remove-Item -Recurse -Force $data }
      New-Item -ItemType Directory -Force -Path (Join-Path $data "bin") | Out-Null
      New-Item -ItemType Directory -Force -Path $profile | Out-Null
      # Outils tests factices pour isoler exclusivement le premier affichage.
      foreach ($name in @("yt-dlp.exe","ffmpeg.exe","ffprobe.exe")) {
        [IO.File]::WriteAllBytes((Join-Path $data "bin/$name"), [byte[]]@(77,90))
      }
      $oldLocal = $env:LOCALAPPDATA
      $env:LOCALAPPDATA = $profile
      $timer = [System.Diagnostics.Stopwatch]::StartNew()
      $loaded = $false; $responsive = $false; $restarted = $false
      $loadedPid = 0; $errorDetail = ""
      Write-Output "START $label"
      try {
        $proc = Start-Process -FilePath $exe -WorkingDirectory $root -PassThru
        while ($timer.Elapsed.TotalSeconds -lt 52) {
          Start-Sleep -Milliseconds 400
          if (-not (Test-Path $trace)) { continue }
          $entries = @(Get-Content $trace -Tail 90 -ErrorAction SilentlyContinue)
          if (@($entries | Where-Object { $_ -match "WebView2 bloque: nouvelle tentative automatique unique" }).Count -gt 0) {
            $restarted = $true
          }
          $loadedEntries = @($entries | Where-Object { $_ -match "PID=\d+ Interface HTML chargee" })
          if ($loadedEntries.Count -eq 0) { continue }
          $loadedPid = [int]([regex]::Match($loadedEntries[-1], "PID=(\d+) Interface HTML chargee").Groups[1].Value)
          $loaded = $true
          $gui = Get-Process -Id $loadedPid -ErrorAction SilentlyContinue
          if ($gui -and $gui.MainWindowHandle -ne [IntPtr]::Zero) {
            $probeResult = [IntPtr]::Zero
            $probe = [StartupProbe]::SendMessageTimeout(
              $gui.MainWindowHandle, 0, [IntPtr]::Zero, [IntPtr]::Zero,
              2, 3000, [ref]$probeResult)
            $responsive = $probe -ne [IntPtr]::Zero
          }
          break
        }
        if (-not $loaded) { $errorDetail = "HTML absent apres 52s" }
        elseif (-not $responsive) { $errorDetail = "Fenetre ne repond pas a WM_NULL" }
        elseif ($restarted) { $errorDetail = "Relance automatique necessaire" }
      } catch {
        $errorDetail = $_.Exception.Message
      } finally {
        $timer.Stop()
        $env:LOCALAPPDATA = $oldLocal
        if (Test-Path $trace) { Copy-Item $trace (Join-Path $out "startup-$label.txt") -Force }
        $crash = Join-Path $data "crash_log.txt"
        if (Test-Path $crash) { Copy-Item $crash (Join-Path $out "crash-$label.txt") -Force }
        Stop-App
      }
      $success = $loaded -and $responsive -and (-not $restarted) -and (-not $errorDetail)
      $result = [pscustomobject]@{
        mode=$mode; number=$n; success_first_launch=$success
        loaded=$loaded; responsive=$responsive; restarted=$restarted
        seconds=[math]::Round($timer.Elapsed.TotalSeconds,1)
        html_pid=$loadedPid; error=$errorDetail
      }
      $results.Add($result)
      Write-Output ("RESULT " + ($result | ConvertTo-Json -Compress))
      Start-Sleep -Seconds 2
    }
  }
} finally {
  Stop-App
  $results | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $out "results.json")
}
foreach ($mode in @("onefile","onedir")) {
  $items = @($results | Where-Object { $_.mode -eq $mode })
  $passed = @($items | Where-Object { $_.success_first_launch })
  $mean = if ($passed.Count) { [math]::Round(($passed | Measure-Object -Property seconds -Average).Average,1) } else { "N/A" }
  $statement = "$mode : $($passed.Count)/$($items.Count) demarrages froids reussis ; moyenne succes $mean secondes"
  Write-Output "SUMMARY $statement"
  "### $statement" | Out-File -Append -Encoding UTF8 $env:GITHUB_STEP_SUMMARY
}
if ($results.Count -ne 16) { throw "Protocole incomplet: seulement $($results.Count) essais" }
