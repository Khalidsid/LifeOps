$ErrorActionPreference = "Stop"

$containerName = "lifeops-postgres-step-1-2"
$image = "postgres:16"
$port = 54329
$database = "lifeops"
$username = "lifeops"
$password = "lifeops"
$dsn = "postgresql://${username}:${password}@localhost:${port}/${database}"

function Test-PsycopgInstalled {
    @'
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("psycopg") else 1)
'@ | python -
    return $LASTEXITCODE -eq 0
}

function Remove-TestContainer {
    $existing = docker ps -a --filter "name=^/${containerName}$" --format "{{.Names}}"
    if ($existing) {
        docker rm -f $containerName | Out-Null
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required to verify Phase 1 Step 1.2."
}

if (-not (Test-PsycopgInstalled)) {
    throw "psycopg is not installed. Run: python -m pip install `"psycopg[binary]`""
}

Remove-TestContainer

try {
    docker run `
        --name $containerName `
        -e POSTGRES_DB=$database `
        -e POSTGRES_USER=$username `
        -e POSTGRES_PASSWORD=$password `
        -p "${port}:5432" `
        -d $image | Out-Null

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $null = docker exec $containerName pg_isready -U $username -d $database
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        throw "PostgreSQL container did not become ready in time."
    }

    $env:LIFEOPS_TEST_DSN = $dsn

    python scripts/validate_task_schema.py
    if ($LASTEXITCODE -ne 0) {
        throw "Schema validation failed."
    }

    python -m unittest tests.test_task_storage
    if ($LASTEXITCODE -ne 0) {
        throw "Contract tests failed."
    }

    python -m unittest tests.test_task_storage_postgres_integration
    if ($LASTEXITCODE -ne 0) {
        throw "Live PostgreSQL integration tests failed."
    }
}
finally {
    Remove-Item Env:\LIFEOPS_TEST_DSN -ErrorAction SilentlyContinue
    Remove-TestContainer
}
