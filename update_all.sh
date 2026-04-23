#!/usr/bin/env bash
set -euo pipefail

# Detecta automáticamente la raíz del repositorio según la ubicación del script
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$ROOT_DIR/project"
VENV_PY="$ROOT_DIR/.venv/Scripts/python.exe"
LOG_DIR="$ROOT_DIR/project/logs"
RUN_LOG="$LOG_DIR/daily_update.log"
PIPELINE_RUN_LOG="$LOG_DIR/pipeline_last_run.log"
ENV_FILE="$PROJECT_DIR/.env"

read_env() {
  local key="$1"
  local default_value="$2"
  if [ ! -f "$ENV_FILE" ]; then
    echo "$default_value"
    return
  fi

  local line
  line=$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)
  if [ -z "$line" ]; then
    echo "$default_value"
    return
  fi

  local value
  value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%$'\r'}"
  if [ -z "$value" ]; then
    echo "$default_value"
  else
    echo "$value"
  fi
}

mkdir -p "$LOG_DIR"

{
  echo "========================================"
  echo "Inicio: $(date '+%Y-%m-%d %H:%M:%S')"

  cd "$ROOT_DIR"

  LLM_PROVIDER=$(read_env "LLM_PROVIDER" "gemini")
  GEMINI_CLI_COMMAND=$(read_env "GEMINI_CLI_COMMAND" "gemini")
  OLLAMA_BASE_URL=$(read_env "OLLAMA_BASE_URL" "http://localhost:11434")
  OLLAMA_API_KEY=$(read_env "OLLAMA_API_KEY" "")
  OLLAMA_MODEL=$(read_env "OLLAMA_MODEL" "gemma4:e2b")

  echo "[1/5] Git pull..."
  git checkout main
  git pull origin main

  echo "[2/5] Instalar dependencias pipeline..."
  "$VENV_PY" -m pip install -r "$PROJECT_DIR/requirements.txt"

  echo "[3/5] Instalar dependencias dashboard..."
  "$VENV_PY" -m pip install -r "$PROJECT_DIR/dashboard/requirements-dashboard.txt"

  echo "[4/5] Preflight LLM..."
  if [ "$LLM_PROVIDER" = "gemini" ]; then
    echo "LLM_PROVIDER=gemini detectado. Verificando comando '$GEMINI_CLI_COMMAND'..."
    if command -v "$GEMINI_CLI_COMMAND" >/dev/null 2>&1 || "$GEMINI_CLI_COMMAND" --help >/dev/null 2>&1; then
      echo "OK: Gemini CLI encontrado."
    else
      echo "WARNING: Gemini CLI no encontrado. Se intentara Ollama como fallback en el pipeline."
    fi
  elif [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "LLM_PROVIDER=ollama detectado. Verificando endpoint y modelo..."
    CURL_AUTH_ARGS=()
    if [ -n "$OLLAMA_API_KEY" ]; then
      CURL_AUTH_ARGS=(-H "Authorization: Bearer $OLLAMA_API_KEY")
    fi
    if curl -fsS "${CURL_AUTH_ARGS[@]}" "$OLLAMA_BASE_URL/api/tags" > /tmp/ollama_tags.json 2>/dev/null; then
      if grep -qi "$OLLAMA_MODEL" /tmp/ollama_tags.json; then
        echo "OK: Modelo Ollama encontrado ($OLLAMA_MODEL)."
      else
        echo "WARNING: Modelo no encontrado en Ollama ($OLLAMA_MODEL)."
        echo "WARNING: Ejecuta: ollama run $OLLAMA_MODEL"
      fi
    else
      echo "WARNING: Ollama endpoint no disponible en $OLLAMA_BASE_URL"
      echo "WARNING: Ejecuta: ollama serve"
    fi
  else
    echo "LLM_PROVIDER=$LLM_PROVIDER. Se omite preflight de LLM local."
  fi

  echo "[5/5] Ejecutar pipeline..."
  cd "$PROJECT_DIR"
  "$VENV_PY" main.py 2>&1 | tee "$PIPELINE_RUN_LOG"

  echo "[Data Quality] Validación de tickers..."
  invalid_tickers=$(grep -Eo "Quote not found for symbol: [A-Z0-9.\-]+" "$PIPELINE_RUN_LOG" | sed "s/.*: //" | sort -u | tr '\n' ',' | sed 's/,$//' || true)
  incomplete_tickers=$(grep -Eo "Incomplete financial statements for [A-Z0-9.\-]+" "$PIPELINE_RUN_LOG" | sed "s/.* for //" | sort -u | tr '\n' ',' | sed 's/,$//' || true)

  if [ -n "$invalid_tickers" ]; then
    echo "WARNING: Tickers inválidos detectados: $invalid_tickers"
  else
    echo "OK: No se detectaron tickers inválidos."
  fi

  if [ -n "$incomplete_tickers" ]; then
    echo "WARNING: Tickers con estados financieros incompletos: $incomplete_tickers"
  else
    echo "OK: No se detectaron estados financieros incompletos."
  fi

  echo "Verificación rápida de salida..."
  if [ -f "$PROJECT_DIR/data/company_ranking.csv" ]; then
    echo "OK: company_ranking.csv generado."
  else
    echo "ERROR: no se generó company_ranking.csv"
    exit 1
  fi

  echo "Fin: $(date '+%Y-%m-%d %H:%M:%S')"
} >> "$RUN_LOG" 2>&1
