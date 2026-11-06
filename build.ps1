$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$releaseDir = Join-Path $projectRoot "release"

python -m pip install --disable-pip-version-check -r (Join-Path $projectRoot "requirements.txt")
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name application `
    --add-data "assets;assets" `
    --distpath $releaseDir `
    --workpath (Join-Path $projectRoot "build") `
    --specpath $projectRoot `
    (Join-Path $projectRoot "game.py")

Write-Host "Built $releaseDir\application.exe"
