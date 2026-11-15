# Exercise install.ps1 in temporary directories. Requires PowerShell 7.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("hebrew-ps1-" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
  $homeDir = Join-Path $tmp "home"
  $target = Join-Path $tmp "proj"
  New-Item -ItemType Directory -Path $homeDir, $target | Out-Null
  $env:HOME = $homeDir
  $env:USERPROFILE = $homeDir

  & "$root/install.ps1" --dry-run --mode project --target $target --profile web --tools cursor
  if ($LASTEXITCODE -ne 0) { throw "dry-run exit $LASTEXITCODE" }
  $files = @(Get-ChildItem -Recurse -File -LiteralPath $target, $homeDir -ErrorAction SilentlyContinue)
  if ($files.Count -gt 0) { throw "dry-run wrote files" }

  & "$root/install.ps1" --mode project --target $target --profile kids-hebrew --tools cursor,claude
  if ($LASTEXITCODE -ne 0) { throw "install exit $LASTEXITCODE" }
  foreach ($rel in @(
      "CLAUDE.md",
      ".claude/skills/kids-edtech-a11y/SKILL.md",
      ".cursor/rules/ui-rtl-system.mdc"
    )) {
    if (-not (Test-Path -LiteralPath (Join-Path $target $rel))) { throw "missing $rel" }
  }
  if (Test-Path -LiteralPath (Join-Path $homeDir "CLAUDE.md")) { throw "wrote HOME/CLAUDE.md" }
  $homeFiles = @(Get-ChildItem -Recurse -File -LiteralPath $homeDir -ErrorAction SilentlyContinue)
  if ($homeFiles.Count -gt 0) { throw "project install wrote into HOME" }

  $claude = Join-Path $target "CLAUDE.md"
  & "$root/install.ps1" --mode project --target $target --profile kids-hebrew --tools cursor,claude
  if ($LASTEXITCODE -ne 0) { throw "second install exit $LASTEXITCODE" }
  $markers = @(Select-String -Path $claude -Pattern "hebrew-pro-agent-skills:begin" -SimpleMatch)
  if ($markers.Count -ne 1) { throw "marker count $($markers.Count)" }

  $ghome = Join-Path $tmp "ghome"
  $gtarget = Join-Path $tmp "gtarget"
  New-Item -ItemType Directory -Path $ghome, $gtarget | Out-Null
  $env:HOME = $ghome
  $env:USERPROFILE = $ghome
  & "$root/install.ps1" --mode global --target $gtarget --profile full --tools claude,copilot,windsurf,agents
  if ($LASTEXITCODE -ne 0) { throw "global exit $LASTEXITCODE" }
  foreach ($rel in @(
      ".claude/CLAUDE.md",
      ".devin/rules/ui-rtl-system.md",
      ".copilot/copilot-instructions.md",
      ".codex/AGENTS.md"
    )) {
    if (-not (Test-Path -LiteralPath (Join-Path $ghome $rel))) { throw "missing ~/$rel" }
  }
  if (Test-Path -LiteralPath (Join-Path $ghome "CLAUDE.md")) { throw "wrote ~/CLAUDE.md" }
  $gfiles = @(Get-ChildItem -Recurse -File -LiteralPath $gtarget -ErrorAction SilentlyContinue)
  if ($gfiles.Count -gt 0) { throw "global install wrote target" }

  & "$root/install.ps1" --mode global --target $gtarget --uninstall
  if ($LASTEXITCODE -ne 0) { throw "uninstall exit $LASTEXITCODE" }
  if (Test-Path -LiteralPath (Join-Path $ghome ".claude/CLAUDE.md")) {
    throw "global CLAUDE.md survived uninstall"
  }
  Write-Output "install.ps1 tests passed"
}
finally {
  if (Test-Path -LiteralPath $tmp) {
    Remove-Item -Recurse -Force -LiteralPath $tmp
  }
}
