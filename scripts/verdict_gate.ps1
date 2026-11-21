<#
.SYNOPSIS
    verdict-on-file hard gate (AGENTS.md 4.2 item 8, EVO-20261113-001).
    Run BEFORE git merge / gh pr merge / direct push to main.

.DESCRIPTION
    Exit 0  = gate PASS (most recent non-design stage verdict is PASS with 0 blockers)
    Exit 1  = gate FAILED; merge without sir's "sir direct: merge without verdict" in the merge message is a process violation.

    Verdict discovery (EVO-20261116-001 hardening, EVO-20261117-001 single source):
      - Optional -VerdictDir override; otherwise scans every project verdicts dir,
        the shared EVO handoff dir, and <current dir>\verdicts
      - Candidate suffixes for <BASE><suffix>.verdict.json must match one entry of
        tools/verdict_suffixes.json (canonical / stage / single-letter / topic).
        That file is the SINGLE source: it also carries the design-only pattern.
      - Any OTHER suffix is FAIL-CLOSED (exit 1) unless explicitly allowed via
        -AllowSubVerdict <glob> (merge message must disclose it).
      - Selection: latest ts among non-design candidates; on identical ts the
        canonical filename wins (deterministic tie-break). A disagreement between
        the canonical verdict and a newer sub-verdict is audited loudly, not
        blocked: the dangerous direction (canonical PASS, newer sub FAIL) is
        already fail-closed by newest-wins.
      - Always audits: chosen path, sha256, ts, ts source, provenance, this
        script's own sha256, and the contract file it read (4.2 item 8 provenance).

    -RequireExact: only canonical <BASE>.verdict.json may authorize. Effective
    only when -AllowSubVerdict is absent; release-level merges only, must be
    registered in the merge message.

    Design/spec-only verdicts are EXCLUDED: a verdict is design-only iff its raw
    JSON matches the design_only_pattern in tools/verdict_suffixes.json (the
    pattern is deliberately NOT repeated here -- see the 5->6 PROTECTED drift).
    Stage verdicts with a non-empty 'checkpoint' are code verdicts.

    Blockers schema: int (0) or array (length 0). Fail-closed otherwise.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$CardId,
    [string]$VerdictDir,
    [string[]]$AllowSubVerdict = @(),
    [switch]$RequireExact
)

$ErrorActionPreference = 'Stop'

# Single source of truth for verdict file-name semantics (EVO-20261117-001).
# Resolved from $PSScriptRoot, never the current working directory: this gate is
# documented as runnable from any repo. A missing or unreadable contract is
# fail-closed -- a gate that cannot tell which verdicts count must not pass.
$repoRoot = Split-Path -Parent $PSScriptRoot
$contractPath = Join-Path $repoRoot 'tools\verdict_suffixes.json'
if (-not (Test-Path $contractPath)) {
    Write-Host "[verdict_gate] FAIL-CLOSED: verdict contract not found at $contractPath (tools/verdict_suffixes.json is the single source for suffix + design-only semantics)."
    exit 1
}
try {
    $contract = (Get-Content -Raw -Encoding UTF8 $contractPath) | ConvertFrom-Json
} catch {
    Write-Host "[verdict_gate] FAIL-CLOSED: verdict contract at $contractPath is unreadable ($($_.Exception.Message))."
    exit 1
}
$allowedSuffixPatterns = @($contract.suffixes | ForEach-Object { $_.pattern } | Where-Object { $_ })
$designPattern = $contract.design_only_pattern
$designCaseSensitive = $contract.design_only_case_sensitive
if (-not $allowedSuffixPatterns -or $allowedSuffixPatterns.Count -eq 0 -or -not $designPattern) {
    Write-Host "[verdict_gate] FAIL-CLOSED: verdict contract at $contractPath is incomplete (need suffixes[] and design_only_pattern)."
    exit 1
}
# EVO-20261121-001 A2/A5: the case switch is required and must be a bool. A
# missing/non-bool key is fail-closed, never silently defaulted (co-versioned
# with both consumers). -cmatch is case-sensitive; -match is case-insensitive.
if ($null -eq $designCaseSensitive -or ($designCaseSensitive -isnot [bool])) {
    Write-Host "[verdict_gate] FAIL-CLOSED: verdict contract at $contractPath needs boolean design_only_case_sensitive (EVO-20261121-001)."
    exit 1
}
$designMatchScript = if ($designCaseSensitive) { { param($s) $s -cmatch $designPattern } } else { { param($s) $s -match $designPattern } }
$topicSuffixPattern = '^\.[a-z0-9]+$'
$verdictSuffix = '.verdict.json'

function Get-FileSha256([string]$Path) {
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        $hash = $sha.ComputeHash($bytes)
        $sha.Dispose()
        return ([System.BitConverter]::ToString($hash) -replace '-', '').ToLowerInvariant()
    } catch { return 'unreadable' }
}

$selfPath = $PSCommandPath
if (-not $selfPath) { $selfPath = $MyInvocation.MyCommand.Path }
$selfSha = if ($selfPath -and (Test-Path $selfPath)) { Get-FileSha256 $selfPath } else { 'unknown' }

function Get-VerdictsRoots {
    $roots = @()
    if ($VerdictDir) { $roots += $VerdictDir }
    if (Test-Path 'D:\15812\projects') {
        $roots += Get-ChildItem 'D:\15812\projects' -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'verdicts' } |
            Where-Object { Test-Path $_ }
    }
    $roots += 'D:\15812\projects\_handoffs\evo'
    $roots += (Join-Path (Get-Location) 'verdicts')
    return $roots | Where-Object { Test-Path $_ } | Select-Object -Unique
}

function Test-SuffixAllowed([string]$Suffix) {
    foreach ($p in $allowedSuffixPatterns) {
        if ($Suffix -match $p) { return $true }
    }
    foreach ($g in $AllowSubVerdict) {
        if ($g -and $Suffix -like $g) { return $true }
    }
    return $false
}

function Get-Candidates([string]$Base, [string]$Root) {
    $files = Get-ChildItem -Path $Root -Recurse -File -Filter "$Base*.verdict.json" -ErrorAction SilentlyContinue
    if (-not $files) { return @() }
    $items = foreach ($f in $files) {
        $name = $f.Name
        $suffix = $name.Substring($Base.Length, $name.Length - $Base.Length - $verdictSuffix.Length)
        $raw = $null
        try { $raw = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8) } catch { continue }
        $j = $null
        try { $j = $raw | ConvertFrom-Json } catch { continue }
        # EVO-20261121-001: design-only is dual-track. An explicit boolean
        # `design_only` field on the verdict is AUTHORITATIVE (present => wins);
        # only when the field is absent do we fall back to the content scan.
        # This breaks the self-deadlock where a verdict that merely DISCUSSES
        # design-only concepts was itself marked design-only by the scan.
        $designProp = $j.PSObject.Properties['design_only']
        if ($null -ne $designProp) {
            if ($designProp.Value -isnot [bool]) {
                Write-Host "[verdict_gate] FAIL-CLOSED: explicit design_only on $($f.Name) must be a bool (true/false)."
                exit 1
            }
            $isDesign = [bool]$designProp.Value
        } else {
            $isDesign = & $designMatchScript $raw
        }
        $ts = $null
        $tsSource = 'json'
        $tsParsed = [DateTimeOffset]::MinValue
        if ($j.ts -and [DateTimeOffset]::TryParse($j.ts, [ref]$tsParsed)) { $ts = $tsParsed }
        if (-not $ts) { $ts = $f.LastWriteTime; $tsSource = 'mtime' }
        [PSCustomObject]@{
            File        = $f.FullName
            Raw         = $raw
            Json        = $j
            IsDesign    = $isDesign
            Ts          = $ts
            TsSource    = $tsSource
            Suffix      = $suffix
            IsCanonical = ($suffix -eq '')
            IsTopic     = ($suffix -match $topicSuffixPattern)
            Sha256      = (Get-FileSha256 $f.FullName)
            Allowed     = (Test-SuffixAllowed $suffix)
        }
    }
    return $items
}

function Get-BlockersCount($j) {
    $b = $j.blockers
    if ($null -eq $b) { return $null }
    if ($b -is [int] -or $b -is [long]) { return [int]$b }
    if ($b -is [array]) { return $b.Count }
    return $null
}

$base = $CardId
if ($CardId -match '^(?<head>EVO-\d{8}-\d{3}|OC-\d{8}-\d{3}|DFB-\d{8}-\d{3}|XJ-\d{8}-\d{3}|GLASSSUITE-\d{8}-\d{3})-') {
    $base = $Matches['head']
}

Write-Host "[verdict_gate] audit: script=$selfSha card=$base allowSub=$(@($AllowSubVerdict) -join ',') requireExact=$($RequireExact.IsPresent)"

$roots = Get-VerdictsRoots
if (-not $roots) {
    Write-Host '[verdict_gate] no verdicts root found. Gate FAILED (fail-closed).'
    exit 1
}

$all = @()
foreach ($r in $roots) { $all += Get-Candidates -Base $base -Root $r }
$all = @($all | Where-Object { $_ -ne $null })

# ---- fail-closed on unknown suffixes ----
$unknown = @($all | Where-Object { -not $_.Allowed })
if ($unknown.Count -gt 0) {
    Write-Host "[verdict_gate] FAIL-CLOSED: unrecognized verdict suffix (EVO-20261116-001). $($unknown.Count) file(s):"
    foreach ($u in $unknown) { Write-Host "  - $($u.File)" }
    Write-Host "[verdict_gate] if intentional, re-run with -AllowSubVerdict '<glob>' and disclose it in the merge message."
    exit 1
}

if (-not $all -or $all.Count -eq 0) {
    Write-Host "[verdict_gate] no verdict on file for '$base' under: $($roots -join ', '). Gate FAILED."
    exit 1
}

$codeVerdicts = @($all | Where-Object { -not $_.IsDesign })
if (-not $codeVerdicts -or $codeVerdicts.Count -eq 0) {
    Write-Host "[verdict_gate] only design/spec-only verdicts on file for '$base' (not usable to authorize a code merge). Gate FAILED."
    exit 1
}

if ($RequireExact.IsPresent -and $AllowSubVerdict.Count -eq 0) {
    $canon = @($codeVerdicts | Where-Object { $_.IsCanonical })
    if ($canon.Count -eq 0) {
        Write-Host "[verdict_gate] -RequireExact: no canonical '$base.verdict.json'. Gate FAILED."
        exit 1
    }
    $codeVerdicts = $canon
    Write-Host "[verdict_gate] -RequireExact active: only the canonical verdict may authorize (release-level)."
}

$sorted = @($codeVerdicts | Sort-Object -Property @{ Expression = 'Ts'; Descending = $true }, @{ Expression = 'IsCanonical'; Descending = $true })
$latest = $sorted[0]
$canonicalItem = @($codeVerdicts | Where-Object { $_.IsCanonical }) | Select-Object -First 1

# ---- disagreement audit (never silent; newest ts wins per 4.2 item 8) ----
# NOTE (2026-11-17): an earlier revision failed closed whenever a topic-style
# sub-verdict shadowed a non-PASS canonical. The 138-card regression proved that
# WRONG: it blocks the legitimate round-1 CONDITIONAL -> round-2 PASS supersede
# (EVO-20261114-002). Direction analysis: the dangerous direction (canonical PASS
# vs newer sub FAIL) is already fail-closed by newest-wins, so no extra rule is
# needed. Disagreement is therefore audited loudly, not blocked.
if (-not $latest.IsCanonical -and $canonicalItem) {
    $v1 = "$($latest.Json.verdict)"; $v2 = "$($canonicalItem.Json.verdict)"
    if ($v1 -ne $v2) {
        Write-Host "[verdict_gate] WARNING: canonical and sub-verdict disagree; newest ts wins (4.2 item 8 stage semantics)."
        Write-Host "  chosen : $($latest.File) verdict=$v1 sha=$($latest.Sha256) ts=$($latest.Ts.ToUniversalTime().ToString('s'))Z"
        Write-Host "  canon  : $($canonicalItem.File) verdict=$v2 sha=$($canonicalItem.Sha256) ts=$($canonicalItem.Ts.ToUniversalTime().ToString('s'))Z"
    }
}

$provenance = if ($latest.IsCanonical) { 'canonical' } elseif ($latest.IsTopic) { 'topic-sub' } else { 'stage' }
Write-Host "[verdict_gate] audit: chosen=$($latest.File) sha=$($latest.Sha256) ts=$($latest.Ts.ToUniversalTime().ToString('s'))Z tsSource=$($latest.TsSource) suffix='$($latest.Suffix)' provenance=$provenance candidates=$($codeVerdicts.Count)"

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