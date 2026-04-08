# Pepline Fundamentals

> **Sistema modular de análisis fundamental de equity** para investigación de oportunidades de inversión en tecnología, semiconductores, energía, defensa, minería e industria.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.44+-red?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

---

## ¿Qué hace este proyecto?

1. **Descarga datos financieros** de hasta 65+ empresas vía yfinance (ingresos, márgenes, ROIC, deuda, FCF, valuación)
2. **Calcula 14+ métricas** y aplica un scoring de 5 componentes ponderados
3. **Rankea** las empresas de mejor a peor oportunidad con clasificación (Excelente / Buena / Neutral / Riesgosa)
4. **Descubre nuevas oportunidades** automáticamente vía screener Finviz (opcional)
5. **Visualiza** todo en un dashboard interactivo tipo Power BI con tema oscuro

---

## Características Principales

- **Pipeline Modular**: 6 etapas independientes — ingesta → procesamiento → análisis → scoring → ranking → exportación
- **Scoring Transparente**: 5 componentes con pesos explícitos (Calidad 30%, Crecimiento 25%, Rentabilidad 20%, Riesgo 15%, Valuación 10%)
- **Descubrimiento Automático**: Encuentra nuevas oportunidades vía screener Finviz con filtros configurables
- **Dashboard Oscuro**: Streamlit + Plotly con 5 tabs, filtros globales y múltiples tipos de gráficos
- **100% Configurable**: Todos los parámetros en `.env` — sin hardcoding
- **Auditería Completa**: `discovery_log.csv` y `pipeline.log` para trazabilidad total
- **LLM Opcional**: Análisis de noticias y narrativa con proveedor configurable (OpenAI u Ollama local)

---

## Estructura del Proyecto

```
Pepline_fundamentals/
├── project/
│   ├── config/
│   │   └── settings.py              # Configuración centralizada (dataclass)
│   ├── ingestion/
│   │   ├── financial_data.py        # yfinance + Alpha Vantage fallback
│   │   ├── news_data.py             # Recopilación de noticias
│   │   └── ticker_discovery.py      # Finviz screener con mapeo de sectores
│   ├── processing/
│   │   ├── ratios.py                # 14+ métricas financieras
│   │   └── feature_engineering.py   # Flags y características derivadas
│   ├── analysis/
│   │   ├── fundamental_analysis.py  # Scoring por componente (5 dimensiones)
│   │   ├── scoring.py               # Agregación ponderada → total_score
│   │   └── llm_summary.py           # Narrativas LLM (OpenAI/Ollama)
│   ├── models/
│   │   └── ranking_model.py         # Ordenamiento y exportación
│   ├── dashboard/
│   │   ├── app.py                   # App Streamlit principal (5 tabs)
│   │   ├── config.py                # Paleta de colores y pesos visuales
│   │   ├── data_loader.py           # Carga con caché @st.cache_data
│   │   ├── .streamlit/
│   │   │   └── config.toml          # Tema oscuro
│   │   └── components/
│   │       ├── charts.py            # 6 gráficos Plotly reutilizables
│   │       ├── kpis.py              # 4 tarjetas métricas
│   │       └── news.py              # Noticias Top 20, impacto y alertas
│   ├── utils/
│   │   ├── logger.py                # Logging con rotación de archivos
│   │   ├── helpers.py               # Funciones auxiliares (safe_float, clamp, etc.)
│   │   └── ticker_universe.py       # Fusión manual + descubrimiento + dedup
│   ├── data/                        # Salidas del pipeline (gitignored)
│   │   ├── company_ranking.csv
│   │   ├── top10_opportunities.csv
│   │   ├── discovery_log.csv
│   │   └── reports/
│   ├── logs/                        # Logs de ejecución (gitignored)
│   ├── main.py                      # Orquestador principal del pipeline
│   ├── requirements.txt             # Dependencias del pipeline
│   ├── .env                         # Configuración local (gitignored — NO subir)
│   └── .env.example                 # Plantilla de configuración
├── .gitignore
└── README.md
```

---

## Instalación Rápida

### Requisitos

- Python 3.10+
- Conexión a internet (para yfinance y Finviz)

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/visualiaconsulting/Pepline_fundamentals.git
cd Pepline_fundamentals

# 2. Crear entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r project/requirements.txt
pip install -r project/dashboard/requirements-dashboard.txt

# 4. Configurar variables de entorno
cd project
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
# Editar .env con tus tickers y parámetros preferidos
```

---

## Uso

### Ejecutar el Pipeline

```bash
cd project
python main.py
```

**Tiempo típico**: 3-5 minutos (principalmente latencia de red con yfinance)

**Salidas generadas**:
| Archivo | Descripción |
|---------|-------------|
| `data/company_ranking.csv` | Ranking completo (65 tickers × 32 columnas) |
| `data/top10_opportunities.csv` | Top 10 filtrado |
| `data/reports/{TICKER}_report.txt` | Reporte individual por empresa |
| `data/discovery_log.csv` | Auditoría del proceso de descubrimiento |
| `logs/pipeline.log` | Log detallado de ejecución |

### Lanzar el Dashboard

```bash
cd project
python -m streamlit run dashboard/app.py
```

Acceso: **http://localhost:8501**

El dashboard se actualiza automáticamente con el último CSV generado por el pipeline.

### Actualizacion automatica (Windows PowerShell)

Se incluye script nativo para Windows en [update_all.ps1](update_all.ps1):

```powershell
cd C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals
powershell -ExecutionPolicy Bypass -File .\update_all.ps1
```

Opcional para validar sin correr pipeline completo:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1 -SkipPipeline
```

Automatizacion diaria con Task Scheduler:

1. Abrir **Task Scheduler** -> **Create Task**.
2. Trigger: **Daily** (ej. 08:00) y activar "Run task as soon as possible after a scheduled start is missed".
3. Action:
     - Program/script: `powershell.exe`
     - Add arguments:
         `-ExecutionPolicy Bypass -File "C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals\update_all.ps1"`
     - Start in:
         `C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals`
4. General: activar **Run with highest privileges**.
5. Validar logs en `project/logs/daily_update.log`.

---

## Dashboard

5 tabs con tema oscuro optimizado:

| Tab | Contenido |
|-----|-----------|
| **Resumen Ejecutivo** | KPIs globales, Top 25 oportunidades, distribución por clasificación, treemap por sector |
| **Fundamentales** | Scatter Crecimiento vs ROIC (burbuja = market cap), tabla top 15 márgenes |
| **Riesgo y Valuación** | Matriz calidad vs riesgo (color = valuación), tabla top deuda/equity |
| **Scoring** | Heatmap de componentes Top 20, gráfico de contribución ponderada |
| **Noticias** | Noticias Top 20, sentimiento, catalizadores, impacto +1d/+5d, alertas y top movers |

**Filtros globales en sidebar**: Sector · Clasificación · Origen (manual/descubierto) · Rango de score · Market cap

---

## Metodología de Scoring

### Fórmula

```
total_score = (quality × 0.30) + (growth × 0.25) + (profitability × 0.20)
            + (risk × 0.15)   + (valuation × 0.10)
```

### Reglas por Componente

| Componente | Peso | Criterios clave |
|-----------|------|-----------------|
| **Calidad** | 30% | ROIC > 15% (+45pts), Márgenes > 50% (+35pts), FCF > 0 (+20pts) |
| **Crecimiento** | 25% | Revenue YoY normalizado 0–100 |
| **Rentabilidad** | 20% | Operating margin + ROE normalizados |
| **Riesgo** | 15% | D/E > 2 (-55pts), D/E > 1 (-30pts) |
| **Valuación** | 10% | P/E < 15 (90pts), < 25 (70pts), < 40 (50pts) |

### Clasificaciones

| Etiqueta | Rango | Significado |
|---------|-------|-------------|
| ⭐ **Excelente** | 80–100 | Fundamentales de primer nivel |
| ✅ **Buena** | 65–79 | Sólida con potencial |
| ⚠️ **Neutral** | 50–64 | Requiere análisis adicional |
| ❌ **Riesgosa** | < 50 | Evitar o due diligence profundo |

---

## Descubrimiento Automático de Tickers

Activar en `.env`:
```env
TICKER_DISCOVERY_ENABLED=true
DISCOVERY_MAX_NEW_TICKERS=10
DISCOVERY_MIN_SALES_GROWTH=15
DISCOVERY_MIN_MARKET_CAP=100000000    # $100M
DISCOVERY_MAX_MARKET_CAP=10000000000  # $10B
```

**Flujo**:
1. Consulta el screener de Finviz para los sectores configurados
2. Aplica filtros de market cap y crecimiento de ventas
3. Deduplica contra el universo manual y la blocklist
4. Acepta hasta `DISCOVERY_MAX_NEW_TICKERS` candidatos
5. Registra cada decisión en `discovery_log.csv` con motivo

---

## Configuración (.env)

```env
# === UNIVERSO ===
UNIVERSE_TICKERS=NVDA,AMD,TSM,ASML,...

# === SECTORES ===
TARGET_SECTORS=technology,semiconductors,energy,...

# === THRESHOLDS ===
SMALL_MID_CAP_THRESHOLD=10000000000
HIGH_GROWTH_THRESHOLD=15

# === DESCUBRIMIENTO (opcional) ===
TICKER_DISCOVERY_ENABLED=false
DISCOVERY_MAX_NEW_TICKERS=10

# === LLM (opcional) ===
ENABLE_LLM_SUMMARY=false
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_MAX_HEADLINES_PER_TICKER=8
OLLAMA_ENABLE_DASHBOARD_SUMMARY=true
```

Ver [`project/.env.example`](project/.env.example) para referencia completa.

---

## Dependencias

### Pipeline (`requirements.txt`)
```
pandas >= 2.2.0
numpy >= 1.26.0
yfinance >= 0.2.54
python-dotenv >= 1.0.1
requests >= 2.31.0
openai >= 1.45.0       # opcional
finvizfinance >= 1.3.0  # opcional, para descubrimiento
```

## Integracion Ollama Local

1. Instalar y levantar Ollama en tu equipo.
2. Descargar el modelo ligero recomendado:
    - `ollama run gemma4:e2b`
3. Configurar proveedor en `project/.env`:
    - `ENABLE_LLM_SUMMARY=true`
    - `LLM_PROVIDER=ollama`
    - `OLLAMA_BASE_URL=http://localhost:11434`
    - `OLLAMA_MODEL=gemma4:e2b`
4. Ejecutar pipeline normalmente con `python main.py`.

Flujo recomendado:
- Pipeline diario para refrescar ranking y features.
- Dashboard on-demand para revisar noticias Top 20 y alertas.
- Si Ollama no esta disponible, el sistema debe degradar a fallback sin romper ejecucion.

### Dashboard (`dashboard/requirements-dashboard.txt`)
```
streamlit >= 1.44.0
plotly >= 5.24.0
pandas >= 2.2.0
numpy >= 1.26.0
```

---

## Troubleshooting

| Problema | Solución |
|---------|----------|
| `ModuleNotFoundError: No module named 'dashboard'` | Ejecutar desde `project/`: `python -m streamlit run dashboard/app.py` |
| `chmod +x update_all.sh` falla en PowerShell | Normal en Windows PowerShell. Ejecuta el script con Git Bash: `bash update_all.sh` |
| Quiero automatizar en Windows sin Git Bash | Usa `update_all.ps1` con Task Scheduler |
| `No data from yfinance for TICKER` | Verificar ticker en Yahoo Finance; el pipeline continúa sin él |
| Dashboard vacío / sin datos | Ejecutar `python main.py` primero para generar los CSV |
| Discovery no encuentra candidatos | Aumentar `DISCOVERY_MIN_SALES_GROWTH` o expandir `DISCOVERY_SECTORS` |
| Ollama no responde | Verificar que `ollama serve` este activo y que el modelo exista en `ollama list` |

---

## Roadmap

- [ ] **Backtesting**: Validar poder predictivo del score vs retornos históricos (3M/6M forward)
- [ ] **PDF Export**: Exportar resumen ejecutivo desde el dashboard
- [ ] **Snapshots históricos**: Tracking semanal de cambios en el ranking
- [ ] **Alertas**: Notificaciones por email/Slack ante deterioro de score
- [ ] **Integración trading**: Interactive Brokers, Alpaca API

---

## Licencia

MIT License — ver [`LICENSE`](LICENSE) para detalles.

---

## Contacto

**Visualia Consulting**
- Issues y sugerencias: [GitHub Issues](https://github.com/visualiaconsulting/Pepline_fundamentals/issues)

---

*Última actualización: Abril 2026 · Versión 1.0.0*
