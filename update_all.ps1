param(
    [switch]$SkipPipeline,
    [switch]$OpenDashboard,
    [int]$DashboardPort = 8500
)

$ErrorActionPreference = 'Stop'

$RootDir = $PSScriptRoot
$ProjectDir = Join-Path $RootDir "project"
$VenvPy = Join-Path $RootDir ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectDir "logs"
$RunLog = Join-Path $LogDir "daily_update.log"
$PipelineRunLog = Join-Path $LogDir "pipeline_last_run.log"
$PipelineErrLog = Join-Path $LogDir "pipeline_last_run.err.log"
$EnvFile = Join-Path $ProjectDir ".env"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    $line | Out-File -FilePath $RunLog -Append -Encoding utf8
    Write-Host $line
}

function Get-EnvValue {
    param(
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path $EnvFile)) {
        return $DefaultValue
    }

    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" } | Select-Object -Last 1
    if (-not $line) {
        return $DefaultValue
    }

    $value = $line.Substring($Key.Length + 1).Trim().Trim('"')
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

Write-Log "========================================"
Write-Log "Inicio de update_all.ps1"

try {
    Set-Location $RootDir

    if (-not (Test-Path $VenvPy)) {
        throw "No se encontro Python del entorno virtual: $VenvPy"
    }

    $llmProvider = Get-EnvValue -Key "LLM_PROVIDER" -DefaultValue "openai"
    $ollamaBaseUrl = Get-EnvValue -Key "OLLAMA_BASE_URL" -DefaultValue "http://localhost:11434"
    $ollamaApiKey = Get-EnvValue -Key "OLLAMA_API_KEY" -DefaultValue ""
    $ollamaModel = Get-EnvValue -Key "OLLAMA_MODEL" -DefaultValue "gemma4:e2b"

    Write-Log "[1/6] Git pull..."
    git checkout main | Out-Null
    git pull origin main | Out-Null

    Write-Log "[2/6] Instalar dependencias pipeline..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "requirements.txt") | Out-Null

    Write-Log "[3/6] Instalar dependencias dashboard..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "dashboard\requirements-dashboard.txt") | Out-Null

    Write-Log "[4/6] Preflight Ollama (si aplica)..."
    if ($llmProvider -eq "ollama") {
        Write-Log "LLM_PROVIDER=ollama detectado. Verificando endpoint y modelo..."
        try {
            $tagsUrl = "$($ollamaBaseUrl.TrimEnd('/'))/api/tags"
            $headers = @{}
            if (-not [string]::IsNullOrWhiteSpace($ollamaApiKey)) {
                $headers["Authorization"] = "Bearer $ollamaApiKey"
            }
            $response = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 15 -Headers $headers
            $models = @()
            if ($response.models) {
                $models = $response.models | ForEach-Object { $_.name }
            }

            if ($models -contains $ollamaModel) {
                Write-Log "OK: Modelo Ollama encontrado ($ollamaModel)."
            }
            else {
                Write-Log "WARNING: Modelo no encontrado en Ollama ($ollamaModel). Ejecuta: ollama run $ollamaModel"
            }
        }
        catch {
            Write-Log "WARNING: Ollama endpoint no disponible en $ollamaBaseUrl. Ejecuta: ollama serve"
        }
    }
    else {
        Write-Log "LLM_PROVIDER=$llmProvider. Se omite preflight de Ollama."
    }

    Write-Log "[5/6] Ejecutar pipeline..."
    if ($SkipPipeline) {
        Write-Log "SKIP: pipeline omitido por parametro -SkipPipeline"
    }
    else {
        Set-Location $ProjectDir
        if (Test-Path $PipelineRunLog) {
            Remove-Item $PipelineRunLog -Force
        }
        if (Test-Path $PipelineErrLog) {
            Remove-Item $PipelineErrLog -Force
        }

        $startProcessArgs = @{
            FilePath = $VenvPy
            ArgumentList = "main.py"
            WorkingDirectory = $ProjectDir
            NoNewWindow = $true
            Wait = $true
            PassThru = $true
            RedirectStandardOutput = $PipelineRunLog
            RedirectStandardError = $PipelineErrLog
        }
        $proc = Start-Process @startProcessArgs

        if (Test-Path $PipelineRunLog) {
            Get-Content $PipelineRunLog | Out-File -FilePath $RunLog -Append -Encoding utf8
        }
        if (Test-Path $PipelineErrLog) {
            Get-Content $PipelineErrLog | Out-File -FilePath $RunLog -Append -Encoding utf8
        }

        if ($proc.ExitCode -ne 0) {
            throw "Pipeline terminó con código de salida $($proc.ExitCode)"
        }

        Write-Log "[Data Quality] Validacion de tickers..."
        $invalidMatches = Select-String -Path $PipelineRunLog -Pattern "Quote not found for symbol: ([A-Z0-9.\-]+)" -AllMatches -ErrorAction SilentlyContinue
        $invalidTickers = @()
        foreach ($m in $invalidMatches) {
            foreach ($g in $m.Matches) {
                $invalidTickers += $g.Groups[1].Value
            }
        }
        $invalidTickers = $invalidTickers | Sort-Object -Unique

        $incompleteMatches = Select-String -Path $PipelineRunLog -Pattern "Incomplete financial statements for ([A-Z0-9.\-]+)" -AllMatches -ErrorAction SilentlyContinue
        $incompleteTickers = @()
        foreach ($m in $incompleteMatches) {
            foreach ($g in $m.Matches) {
                $incompleteTickers += $g.Groups[1].Value
            }
        }
        $incompleteTickers = $incompleteTickers | Sort-Object -Unique

        if ($invalidTickers.Count -gt 0) {
            Write-Log ("WARNING: Tickers invalidos detectados: " + ($invalidTickers -join ","))
        }
        else {
            Write-Log "OK: No se detectaron tickers invalidos."
        }

        if ($incompleteTickers.Count -gt 0) {
            Write-Log ("WARNING: Tickers con estados financieros incompletos: " + ($incompleteTickers -join ","))
        }
        else {
            Write-Log "OK: No se detectaron estados financieros incompletos."
        }
    }

    Write-Log "[6/6] Verificacion de salida..."
    $rankingFile = Join-Path $ProjectDir "data\company_ranking.csv"
    if (Test-Path $rankingFile) {
        Write-Log "OK: company_ranking.csv generado."
    }
    else {
        throw "No se genero company_ranking.csv"
    }

    if ($OpenDashboard) {
        Write-Log "[Extra] Iniciando dashboard Streamlit..."
        $dashboardArgs = @(
            "-m",
            "streamlit",
            "run",
            "dashboard/app.py",
            "--server.headless",
            "true",
            "--server.port",
            "$DashboardPort"
        )

        Start-Process -FilePath $VenvPy -ArgumentList $dashboardArgs -WorkingDirectory $ProjectDir | Out-Null
        Write-Log "Dashboard lanzado en http://localhost:$DashboardPort"
    }

    Write-Log "Fin de update_all.ps1"
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    throw
}
