param(
    [switch]$SkipPipeline,
    [switch]$OpenDashboard,
    [int]$DashboardPort = 8500
)

$ErrorActionPreference = 'Stop'

$RootDir = $PSScriptRoot
$ProjectDir = Join-Path $RootDir "project"
$VenvPy = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    $VenvPy = Join-Path $RootDir ".venv\Scripts\python.exe"
}
$LogDir = Join-Path $ProjectDir "logs"
$RunLog = Join-Path $LogDir "daily_update.log"
$PipelineRunLog = Join-Path $LogDir "pipeline_last_run.log"
$PipelineErrLog = Join-Path $LogDir "pipeline_last_run.err.log"
$EmailRunLog = Join-Path $LogDir "email_digest_last_run.log"
$EmailErrLog = Join-Path $LogDir "email_digest_last_run.err.log"
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

    $llmProvider = Get-EnvValue -Key "LLM_PROVIDER" -DefaultValue "gemini"
    $geminiCliCommand = Get-EnvValue -Key "GEMINI_CLI_COMMAND" -DefaultValue "gemini"
    $lmstudioBaseUrl = Get-EnvValue -Key "LMSTUDIO_BASE_URL" -DefaultValue "http://localhost:1234/v1"
    $lmstudioModel = Get-EnvValue -Key "LMSTUDIO_MODEL" -DefaultValue "gemma-4-e2b-it"
    $ollamaBaseUrl = Get-EnvValue -Key "OLLAMA_BASE_URL" -DefaultValue "http://localhost:11434"
    $ollamaApiKey = Get-EnvValue -Key "OLLAMA_API_KEY" -DefaultValue ""
    $ollamaModel = Get-EnvValue -Key "OLLAMA_MODEL" -DefaultValue "minimax-m2.7:cloud"
    $emailReportEnabled = (Get-EnvValue -Key "EMAIL_REPORT_ENABLED" -DefaultValue "false").ToLower()

    Write-Log "[1/7] Git pull..."
    git checkout main | Out-Null
    git pull origin main | Out-Null

    Write-Log "[2/7] Instalar dependencias pipeline..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "requirements.txt") | Out-Null

    Write-Log "[3/7] Instalar dependencias dashboard..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "dashboard\requirements-dashboard.txt") | Out-Null

    Write-Log "[4/7] Preflight Gemini CLI..."
    if ($llmProvider -eq "gemini") {
        Write-Log "LLM_PROVIDER=gemini detectado. Verificando comando '$geminiCliCommand'..."
        $geminiCheck = Get-Command $geminiCliCommand -ErrorAction SilentlyContinue
        if ($geminiCheck) {
            Write-Log "OK: Gemini CLI encontrado."
        }
        else {
            Write-Log "WARNING: Gemini CLI no encontrado en el PATH. Se intentara Ollama como fallback."
        }
    }
    else {
        Write-Log "LLM_PROVIDER=$llmProvider. Se omite preflight de Gemini CLI."
    }

    Write-Log "[5/7] Preflight Ollama / Fallbacks..."
    if ($llmProvider -eq "ollama" -or $llmProvider -eq "gemini") {
        Write-Log "Verificando configuracion de Ollama para uso principal o fallback..."
        try {
            $tagsUrl = "$($ollamaBaseUrl.TrimEnd('/'))/api/tags"
            $headers = @{}
            if ($ollamaApiKey) {
                 $headers = @{ "Authorization" = "Bearer $ollamaApiKey" }
            }
            $response = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 15 -Headers $headers
            Write-Log "OK: Ollama accesible en $ollamaBaseUrl"
        }
        catch {
            Write-Log "WARNING: Ollama no respondio: $($_.Exception.Message)"
        }
    }

    Write-Log "[6/7] Ejecutar pipeline..."
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

    Write-Log "[7/7] Verificacion de salida..."
    $rankingFile = Join-Path $ProjectDir "data\company_ranking.csv"
    if (Test-Path $rankingFile) {
        Write-Log "OK: company_ranking.csv generado."
    }
    else {
        throw "No se genero company_ranking.csv"
    }

    if ($OpenDashboard) {
        Write-Log "[Extra] Iniciando dashboard Streamlit..."
        $StreamlitRunLog = Join-Path $LogDir "streamlit_dashboard.log"
        $StreamlitErrLog = Join-Path $LogDir "streamlit_dashboard.err.log"

        if (Test-Path $StreamlitRunLog) { Remove-Item $StreamlitRunLog -Force }
        if (Test-Path $StreamlitErrLog) { Remove-Item $StreamlitErrLog -Force }

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

        $dashboardProcess = Start-Process -FilePath $VenvPy -ArgumentList $dashboardArgs -WorkingDirectory $ProjectDir -NoNewWindow -PassThru -RedirectStandardOutput $StreamlitRunLog -RedirectStandardError $StreamlitErrLog

        Start-Sleep -Seconds 3

        if ($dashboardProcess.HasExited) {
            $errorMsg = "Streamlit proceso murio con exit code: $($dashboardProcess.ExitCode)"
            Write-Log "ERROR: $errorMsg"
            if (Test-Path $StreamlitErrLog) {
                $errorContent = Get-Content $StreamlitErrLog -Raw
                if ($errorContent) {
                    Write-Log "Streamlit stderr: $errorContent"
                }
            }
            if (Test-Path $StreamlitRunLog) {
                $runContent = Get-Content $StreamlitRunLog -Raw
                if ($runContent) {
                    Write-Log "Streamlit stdout: $runContent"
                }
            }
            throw $errorMsg
        } else {
            Write-Log "OK: Streamlit proceso iniciado (PID: $($dashboardProcess.Id))"
            Write-Log "Dashboard disponible en http://localhost:$DashboardPort"
        }
    }

    if ($emailReportEnabled -eq "true") {
        Write-Log "[Extra] Enviando digest por correo..."
        try {
            Set-Location $ProjectDir

            if (Test-Path $EmailRunLog) {
                Remove-Item $EmailRunLog -Force
            }
            if (Test-Path $EmailErrLog) {
                Remove-Item $EmailErrLog -Force
            }

            $emailProcessArgs = @{
                FilePath = $VenvPy
                ArgumentList = "-m reporting.email_digest"
                WorkingDirectory = $ProjectDir
                NoNewWindow = $true
                Wait = $true
                PassThru = $true
                RedirectStandardOutput = $EmailRunLog
                RedirectStandardError = $EmailErrLog
            }
            $emailProc = Start-Process @emailProcessArgs

            if (Test-Path $EmailRunLog) {
                Get-Content $EmailRunLog | Out-File -FilePath $RunLog -Append -Encoding utf8
            }
            if (Test-Path $EmailErrLog) {
                Get-Content $EmailErrLog | Out-File -FilePath $RunLog -Append -Encoding utf8
            }

            if ($emailProc.ExitCode -ne 0) {
                Write-Log "WARNING: El digest de correo terminó con código $($emailProc.ExitCode). Revisa $EmailErrLog"
            }
            else {
                Write-Log "OK: Digest de correo enviado o gestionado correctamente."
            }
        }
        catch {
            Write-Log "WARNING: No se pudo enviar el digest por correo: $($_.Exception.Message). Revisa $EmailErrLog"
        }
    }

    Write-Log "Fin de update_all.ps1"
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    throw
}
