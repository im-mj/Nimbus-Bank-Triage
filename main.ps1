param(
    [string]$PythonExe = "python",
    [switch]$RebuildIndex,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode {
    param([string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements.txt"
$appPath = Join-Path $projectRoot "src\app.py"
$indexPath = Join-Path $projectRoot "src\kb\build_index.py"
$envPath = Join-Path $projectRoot ".env"
$envExamplePath = Join-Path $projectRoot ".env.example"
$chromaDbPath = Join-Path $projectRoot "data\chroma\chroma.sqlite3"
$tempDir = Join-Path $projectRoot ".tmp"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TEMP = $tempDir
$env:TMP = $tempDir

Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force $tempDir | Out-Null

    if (-not (Test-Path $envPath)) {
        if (Test-Path $envExamplePath) {
            Copy-Item -LiteralPath $envExamplePath -Destination $envPath
        }

        throw "Created .env from .env.example. Add your API keys to $envPath, then rerun this script."
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating Windows virtual environment in .venv ..."
        & $PythonExe -m venv $venvDir
        Assert-LastExitCode "Virtual environment creation"
    }

    & $venvPython -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pip') else 1)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Bootstrapping pip inside .venv ..."
        & $venvPython -m ensurepip --upgrade
        Assert-LastExitCode "pip bootstrap"
    }

    Write-Host "Checking project dependencies ..."
    & $venvPython -c "import importlib.util, sys; required = ('streamlit', 'langgraph', 'chromadb'); sys.exit(0 if all(importlib.util.find_spec(name) for name in required) else 1)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing project dependencies ..."
        & $venvPython -m pip install --upgrade pip
        Assert-LastExitCode "pip upgrade"
        & $venvPython -m pip install -r $requirementsPath
        Assert-LastExitCode "Dependency installation"
    }

    if ($RebuildIndex -or -not (Test-Path $chromaDbPath)) {
        Write-Host "Building the Chroma knowledge base index ..."
        & $venvPython $indexPath
        Assert-LastExitCode "Knowledge base indexing"
    }

    if ($SetupOnly) {
        Write-Host "Windows setup completed."
        return
    }

    Write-Host "Starting Streamlit ..."
    & $venvPython -m streamlit run $appPath
    Assert-LastExitCode "Streamlit startup"
}
finally {
    Pop-Location
}
