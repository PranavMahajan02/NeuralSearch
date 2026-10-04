# CogniSeek developer commands.
# Usage: .\scripts\dev.ps1 <command>
#   infra-up       docker compose up -d (postgres + qdrant)
#   run-backend    uvicorn app.main:app --reload on 127.0.0.1:8000
#   run-frontend   vite dev server (frontend/)
#   test           pytest (all tests, including slow ones)
#   test-fast      pytest -m "not slow" (no AI models loaded)
#   lint           python byte-compile check + frontend tsc --noEmit

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("infra-up", "run-backend", "run-frontend", "test", "test-fast", "lint")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"

Push-Location $Root
try {
    switch ($Command) {
        "infra-up" {
            docker compose up -d
        }
        "run-backend" {
            & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
        }
        "run-frontend" {
            Push-Location frontend
            try { npm run dev } finally { Pop-Location }
        }
        "test" {
            & $Python -m pytest -q
        }
        "test-fast" {
            & $Python -m pytest -q -m "not slow"
        }
        "lint" {
            & $Python -m compileall -q app tests
            Push-Location frontend
            try { npx tsc --noEmit } finally { Pop-Location }
        }
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
