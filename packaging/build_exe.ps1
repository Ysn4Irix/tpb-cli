<#
.SYNOPSIS
    Builds standalone Windows executable (dist/tpb-gui.exe) using PyInstaller.
#>

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Push-Location $RootDir

try {
    Write-Host "Checking PySide6 and PyInstaller..." -ForegroundColor Cyan
    python -c "import PySide6, PyInstaller; print('PySide6:', PySide6.__version__)"

    Write-Host "Building standalone tpb-gui.exe..." -ForegroundColor Cyan
    pyinstaller --clean --noconfirm "packaging/tpb-gui.spec"

    $ExePath = Join-Path $RootDir "dist\tpb-gui.exe"
    if (-Not (Test-Path $ExePath)) {
        throw "Build succeeded but $ExePath was not produced."
    }

    $SizeMB = [Math]::Round((Get-Item $ExePath).Length / 1MB, 2)
    Write-Host "[OK] Standalone executable built: $ExePath ($SizeMB MB)" -ForegroundColor Green
}
finally {
    Pop-Location
}
