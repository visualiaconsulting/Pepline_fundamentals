param(
    [switch]$SkipPipeline,
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

function Clear-LogFile {
    param([string]$Path)
    if (Test-Path $Path) {
        try {
            Remove-Item $Path -Force -ErrorAction Stop
        }
        catch {
            try {
                # Si no se puede borrar, intentamos vaciarlo
                Clear-Content $Path -ErrorAction Stop
            }
            catch {
                Write-Log "WARNING: No se pudo limpiar $Path. Puede que este bloqueado por otro proceso."
            }
        }
    }
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
    $ollamaBaseUrl = Get-EnvValue -Key "OLLAMA_BASE_URL" -DefaultValue "http://localhost:11434"
    $ollamaApiKey = Get-EnvValue -Key "OLLAMA_API_KEY" -DefaultValue ""

    Write-Log "[1/6] Git pull..."
    git checkout main | Out-Null
    git pull origin main | Out-Null

    Write-Log "[2/6] Instalar dependencias pipeline..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "requirements.txt") | Out-Null

    Write-Log "[3/6] Instalar dependencias dashboard..."
    & $VenvPy -m pip install -r (Join-Path $ProjectDir "dashboard\requirements-dashboard.txt") | Out-Null

    Write-Log "[4/6] Preflight Gemini CLI..."
    if ($llmProvider -eq "gemini") {
        Write-Log "LLM_PROVIDER=gemini detectado. Verificando comando '$geminiCliCommand'..."
        $geminiCheck = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $geminiCliCommand --version" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
        if ($geminiCheck -and $geminiCheck.ExitCode -eq 0) {
            Write-Log "OK: Gemini CLI encontrado."
        }
        else {
            Write-Log "WARNING: Gemini CLI no encontrado o no respondio. Se intentara Ollama como fallback."
        }
    }

    Write-Log "[5/6] Ejecutar pipeline..."
    if ($SkipPipeline) {
        Write-Log "SKIP: pipeline omitido por parametro -SkipPipeline"
    }
    else {
        Set-Location $ProjectDir
        Clear-LogFile $PipelineRunLog
        Clear-LogFile $PipelineErrLog

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
        
        try {
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
            Write-Log "OK: Pipeline finalizado correctamente."
        }
        catch {
            if ($_.Exception.Message -match "utilizado en otro proceso") {
                throw "ERROR: Los archivos de log estan bloqueados. Por favor cierra cualquier editor o proceso que los use y reintenta."
            }
            throw
        }
    }

    Write-Log "[6/6] Verificacion de salida e inicio de Dashboard..."
    $rankingFile = Join-Path $ProjectDir "data\company_ranking.csv"
    if (Test-Path $rankingFile) {
        Write-Log "OK: company_ranking.csv encontrado."
    }
    else {
        throw "No se genero company_ranking.csv"
    }

    Write-Log "[Extra] Iniciando dashboard Streamlit..."
    
    $dashboardArgs = @(
        "-m",
        "streamlit",
        "run",
        "dashboard/app.py",
        "--server.port",
        "$DashboardPort"
    )

    # Iniciamos el dashboard en una nueva ventana para que sea visible al usuario
    Start-Process -FilePath $VenvPy -ArgumentList $dashboardArgs -WorkingDirectory $ProjectDir

    Write-Log "OK: Comando Streamlit enviado."
    Write-Log "Dashboard disponible en http://localhost:$DashboardPort"

    Write-Log "Fin de update_all.ps1"
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    throw
}
