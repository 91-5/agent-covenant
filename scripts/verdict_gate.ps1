<#
.SYNOPSIS
    verdict-on-file hard gate (AGENTS.md 4.2 item 8, EVO-20261113-001).
    Run BEFORE git merge / gh pr merge / direct push to main.

.DESCRIPTION
    Exit 0  = gate PASS (most recent non-design stage verdict is PASS with 0 blockers)
    Exit 1  = gate FAILED; merge without sir's "sir direct: merge without verdict" in the merge message is a process violation.

    Verdict discovery:
      - Optional -VerdictDir override; otherwise scans:
          D:\15812\projects\agent-covenant\verdicts
          D:\15812\projects\_handoffs\evo
          <current dir>\verdicts
      - Candidate files: <BASE>*.verdict.json (stage verdicts like OC-<id>-P3..., plus roundN EVO files)

    Design/spec-only verdicts are EXCLUDED: a verdict is design-only iff its raw JSON
    contains /规格级|设计门禁|不对已落地|design gate|spec-level/i (equivalent Unicode escapes are
    89C4 683C 7EA7 / 8BBE 8BA1 95E8 7981 / 4E0D 5BF9 5DF2 843D 5730). Stage verdicts with
    a non-empty 'checkpoint' are code verdicts.

    Blockers schema: int (0) or array (length 0). Fail-closed otherwise.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$CardId,
    [string]$VerdictDir
)

$ErrorActionPreference = 'Stop'
$designPattern = '\u89C4\u683C\u7EA7|\u8BBE\u8BA1\u95E8\u7981|\u4E0D\u5BF9\u5DF2\u843D\u5730|design gate|spec-level'

function Get-VerdictsRoots {
    $roots = @()
    if ($VerdictDir) { $roots += $VerdictDir }
    # Project verdict dirs: D:\15812\projects\*\verdicts (coldstore, agent-covenant, ...)
    if (Test-Path 'D:\15812\projects') {
        $roots += Get-ChildItem 'D:\15812\projects' -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'verdicts' } |
            Where-Object { Test-Path $_ }
    }
    $roots += 'D:\15812\projects\_handoffs\evo'
    $roots += (Join-Path (Get-Location) 'verdicts')
    return $roots | Where-Object { Test-Path $_ } | Select-Object -Unique
}

function Get-LatestVerdict([string]$Base, [string]$Root) {
    $files = Get-ChildItem -Path $Root -Recurse -File -Filter "$Base*.verdict.json" -ErrorAction SilentlyContinue
    if (-not $files) { return $null }
    $items = foreach ($f in $files) {
        $raw = $null
        try { $raw = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8) } catch { continue }
        $isDesign = $raw -match $designPattern
        $j = $null
        try { $j = $raw | ConvertFrom-Json } catch { continue }
        $ts = $null
        $tsParsed = [DateTimeOffset]::MinValue
        if ($j.ts -and [DateTimeOffset]::TryParse($j.ts, [ref]$tsParsed)) { $ts = $tsParsed }
        if (-not $ts) { $ts = $f.LastWriteTime }
        [PSCustomObject]@{ File = $f.FullName; Raw = $raw; Json = $j; IsDesign = $isDesign; Ts = $ts }
    }
    return $items | Sort-Object Ts -Descending
}

function Get-BlockersCount($j) {
    $b = $j.blockers
    if ($null -eq $b) { return $null }
    if ($b -is [int] -or $b -is [long]) { return [int]$b }
    if ($b -is [array]) { return $b.Count }
    return $null
}

$base = $CardId
if ($CardId -match '^(?<head>EVO-\d{8}-\d{3}|OC-\d{8}-\d{3}|DFB-\d{8}-\d{3}|XJ-\d{8}-\d{3})-') {
    $base = $Matches['head']
}

$roots = Get-VerdictsRoots
if (-not $roots) {
    Write-Host '[verdict_gate] no verdicts root found. Gate FAILED (fail-closed).'
    exit 1
}

$all = @()
foreach ($r in $roots) { $all += Get-LatestVerdict -Base $base -Root $r }
$all = @($all | Where-Object { $_ -ne $null })
if (-not $all -or $all.Count -eq 0) {
    Write-Host "[verdict_gate] no verdict on file for '$base' under: $($roots -join ', '). Gate FAILED."
    exit 1
}

$codeVerdicts = @($all | Where-Object { -not $_.IsDesign })
if (-not $codeVerdicts -or $codeVerdicts.Count -eq 0) {
    Write-Host "[verdict_gate] only design/spec-only verdicts on file for '$base' (not usable to authorize a code merge). Gate FAILED."
    exit 1
}

$latest = $codeVerdicts | Sort-Object Ts -Descending | Select-Object -First 1
$bc = Get-BlockersCount $latest.Json
if ($latest.Json.verdict -ne 'PASS') {
    Write-Host "[verdict_gate] most recent non-design verdict is not PASS: $($latest.File) (verdict=$($latest.Json.verdict)). Gate FAILED."
    exit 1
}
if ($null -eq $bc) {
    Write-Host "[verdict_gate] blockers field unreadable in $($latest.File) (fail-closed). Gate FAILED."
    exit 1
}
if ($bc -ne 0) {
    Write-Host "[verdict_gate] most recent non-design verdict has $bc blocker(s): $($latest.File). Gate FAILED."
    exit 1
}

Write-Host "[verdict_gate] OK: '$base' cleared by $($latest.File) (verdict=PASS, blockers=0, ts=$($latest.Ts.ToUniversalTime().ToString('s'))Z)"
exit 0
