# Install Hebrew-first agent skills on Windows.
# Same engine as install.sh (script/install_apply.py): timestamped backups,
# managed blocks instead of clobbering CLAUDE.md / AGENTS.md, and tool paths.
# Global Claude instructions go to $HOME/.claude/CLAUDE.md, never $HOME/CLAUDE.md.

$ErrorActionPreference = "Stop"

function Show-Usage {
  @"
Usage: install.ps1 [options]

Options:
  --mode project|global
  --tools cursor,claude,copilot,windsurf,agents
  --profile full|web|backend|kids-hebrew
  --target DIR
  --dry-run
  --uninstall
  --no-dedupe
  -h, --help
"@
}

$Mode = "project"
$Tools = "cursor,claude,copilot,windsurf,agents"
$Profile = "full"
$Target = ""
$DryRun = $false
$Uninstall = $false
$NoDedupe = $false

function Take-Value([int]$index, [string]$flag) {
  if (($index + 1) -ge $script:args.Count) {
    Write-Error "$flag needs a value"
  }
  return $script:args[$index + 1]
}

for ($i = 0; $i -lt $args.Count; $i++) {
  $arg = [string]$args[$i]
  if ($arg -eq "--help" -or $arg -eq "-h") { Show-Usage; exit 0 }
  if ($arg -eq "--dry-run") { $DryRun = $true; continue }
  if ($arg -eq "--uninstall") { $Uninstall = $true; continue }
  if ($arg -eq "--no-dedupe") { $NoDedupe = $true; continue }
  if ($arg.StartsWith("--mode=")) { $Mode = $arg.Substring(7); continue }
  if ($arg.StartsWith("--tools=")) { $Tools = $arg.Substring(8); continue }
  if ($arg.StartsWith("--profile=")) { $Profile = $arg.Substring(10); continue }
  if ($arg.StartsWith("--target=")) { $Target = $arg.Substring(9); continue }
  if ($arg -eq "--mode") { $Mode = Take-Value $i "--mode"; $i++; continue }
  if ($arg -eq "--tools") { $Tools = Take-Value $i "--tools"; $i++; continue }
  if ($arg -eq "--profile") { $Profile = Take-Value $i "--profile"; $i++; continue }
  if ($arg -eq "--target") { $Target = Take-Value $i "--target"; $i++; continue }
  Write-Error "Unknown argument: $arg"
}

# PowerShell treats an unquoted comma as an array, so --tools cursor,claude
# arrives as two values. Join them before they are passed to Python.
if ($Tools -is [System.Array]) {
  $Tools = ($Tools -join ",")
}
$Tools = [string]$Tools

if ($Mode -notin @("project", "global")) { Write-Error "Invalid mode: $Mode" }
if ($Profile -notin @("full", "web", "backend", "kids-hebrew")) { Write-Error "Invalid profile: $Profile" }
if ([string]::IsNullOrWhiteSpace($Tools)) { Write-Error "--tools must list at least one tool" }
foreach ($part in $Tools.Split(",")) {
  if ($part -notin @("cursor", "claude", "copilot", "windsurf", "agents")) {
    Write-Error "unknown tool: $part"
  }
}

if ([string]::IsNullOrWhiteSpace($env:HOME) -and [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
  Write-Error "HOME or USERPROFILE is required"
}
$HomeDir = if (-not [string]::IsNullOrWhiteSpace($env:HOME)) { $env:HOME } else { $env:USERPROFILE }
if ([string]::IsNullOrWhiteSpace($Target)) {
  $Target = (Get-Location).Path
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = $null
foreach ($candidate in @("python3", "python", "py")) {
  if (Get-Command $candidate -ErrorAction SilentlyContinue) {
    $Python = $candidate
    break
  }
}
if (-not $Python) { Write-Error "python3 is required" }

$pyArgs = @(
  (Join-Path $Root "script/install_apply.py"),
  "--repo", $Root,
  "--mode", $Mode,
  "--tools", $Tools,
  "--profile", $Profile,
  "--target", $Target,
  "--home", $HomeDir
)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($Uninstall) { $pyArgs += "--uninstall" }
if ($NoDedupe) { $pyArgs += "--no-dedupe" }

& $Python @pyArgs
exit $LASTEXITCODE
