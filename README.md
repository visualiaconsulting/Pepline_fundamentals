# Pepline Fundamentals

> **Sistema modular de análisis fundamental de equity** para investigación de oportunidades de inversión en tecnología, semiconductores, energía, defensa, minería e industria.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.44+-red?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

---

## ¿Qué hace este proyecto?

1. **Descarga datos financieros** de hasta 65+ empresas vía yfinance (ingresos, márgenes, ROIC, deuda, FCF, valuación, exchange, precios y target de consenso cuando existe)
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
- **Informe Enriquecido por Ticker**: Cada reporte individual incluye ficha de empresa, fecha de elaboración, cierre previo con fecha, lectura de noticias y target de consenso cuando el dato existe

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
| `data/company_ranking.csv` | Ranking completo con métricas, metadatos de mercado y columnas narrativas enriquecidas |
| `data/top10_opportunities.csv` | Top 10 filtrado |
| `data/reports/{TICKER}_report.txt` | Reporte individual por empresa con 6 secciones, fecha de elaboración y contexto de mercado |
| `data/discovery_log.csv` | Auditoría del proceso de descubrimiento |
| `logs/pipeline.log` | Log detallado de ejecución |

### Formato del Informe por Ticker

Cada archivo `data/reports/{TICKER}_report.txt` se genera en español y ahora contiene estas secciones:

1. **Identificación**: ticker, nombre de empresa, exchange, sector/industria, rank, score, clasificación y fecha de elaboración.
2. **Negocio**: descripción breve de la empresa y lectura resumida del negocio.
3. **Mercado y Valuación**: precio actual de referencia, cierre previo con fecha, precio objetivo de consenso, cantidad de analistas, market cap, múltiplos y moneda.
4. **Fundamentales**: crecimiento YoY, ROIC, márgenes, deuda/capital, free cash flow, flag de alto potencial y tesis preliminar.
5. **Lectura de Noticias**: titular principal, outlook próximo y hasta `EMAIL_REPORT_NEWS_PER_TICKER` noticias con fuente, fecha y link.
6. **Resumen AI**: tesis de inversión, riesgos clave y estado del proveedor LLM.

### Columnas Nuevas en `company_ranking.csv`

El ranking consolidado ahora incluye, además de las métricas previas, estas columnas nuevas:

- `company_name`
- `business_summary`
- `exchange`
- `previous_close`
- `previous_close_date`
- `current_price`
- `target_price`
- `analyst_count`
- `business_overview`
- `near_term_outlook`

Notas:

- `previous_close_date` usa formato `YYYY-MM-DD`.
- `target_price` y `analyst_count` pueden quedar como `N/D` en el informe final si Yahoo Finance no ofrece cobertura para ese ticker.
- `business_summary` proviene del diccionario `info` de yfinance y puede ser más extenso que la versión compacta mostrada en el `.txt`.

### Reglas de Formato y Fallback

- El informe usa `N/D` para campos faltantes en lugar de `0` o cadenas vacías.
- Valores monetarios se muestran con moneda y escala compacta cuando aplica, por ejemplo `4.47T USD` o `96.68B USD`.
- Flags booleanos del reporte se muestran como `Si` o `No`.
- Si el proveedor LLM no responde o está deshabilitado, el pipeline usa un fallback determinista para `business_overview`, `investment_thesis`, `key_risks`, `executive_summary` y `near_term_outlook`.
- El precio objetivo es estrictamente informativo: solo se muestra si existe un dato real de consenso (`targetMeanPrice` o equivalente) en Yahoo Finance.

### Fuentes de Enriquecimiento de Mercado

Los nuevos campos de mercado se extraen principalmente de `yfinance.Ticker.info`, `fast_info` y del historial reciente de precios:

- `fullExchangeName` / `exchange` -> exchange de cotización
- `previousClose` o historial reciente -> cierre previo y fecha
- `currentPrice` / `lastPrice` -> precio de referencia actual
- `targetMeanPrice` / `targetMedianPrice` -> target de consenso
- `numberOfAnalystOpinions` / `numberOfAnalysts` -> cantidad de analistas
- `longBusinessSummary` -> resumen descriptivo base del negocio

La cobertura de estos campos depende del ticker y del mercado. Empresas fuera de EE. UU. o de baja cobertura pueden no traer target o número de analistas.

### Lanzar el Dashboard

```bash
cd project
python -m streamlit run dashboard/app.py --server.port 8500
```

Acceso: **http://localhost:8500**

El dashboard se actualiza automáticamente con el último CSV generado por el pipeline.

### Descarga de Documento en Dashboard (Tab IA Reports)

En la sección **Documento diario** del tab IA Reports ahora puedes:

- Elegir cuántos tickers incluir (`Top 2`, `Top 5`, `Top 10`, `Top 20`)
- Descargar en navegador el `.md` y `.txt` con nombre dinámico
- Guardar un snapshot local en una carpeta elegible desde el propio dashboard

Convención de nombre de archivo:

- `dashboard_top{N}_{MMDDYYYY}.md`
- `dashboard_top{N}_{MMDDYYYY}.txt`

Ejemplo para 2 tickers el 10 de abril de 2026:

- `dashboard_top2_04102026.txt`

Notas operativas:

- La descarga por navegador usa la carpeta configurada en tu navegador/SO (normalmente `Downloads`).
- Si necesitas controlar la ruta exacta, usa **Guardar snapshot del documento** e indica la carpeta local en el campo de ruta.

### Actualizacion automatica (Windows PowerShell)

Se incluye script nativo para Windows en [update_all.ps1](update_all.ps1):

```powershell
cd <ruta-del-repo>
powershell -ExecutionPolicy Bypass -File .\update_all.ps1
```

Opcional para validar sin correr pipeline completo:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1 -SkipPipeline
```

Opcional para abrir dashboard automaticamente al finalizar:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1 -OpenDashboard -DashboardPort 8500
```

Automatizacion diaria con Task Scheduler:

1. Abrir **Task Scheduler** -> **Create Task**.
2. Trigger: **Daily** (ej. 08:00) y activar "Run task as soon as possible after a scheduled start is missed".
3. Action:
     - Program/script: `powershell.exe`
     - Add arguments:
         `-ExecutionPolicy Bypass -File "<ruta-del-repo>\update_all.ps1"`
     - Start in:
         `<ruta-del-repo>`
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
OLLAMA_API_KEY=
OLLAMA_MODEL=gemma4:e2b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_MAX_HEADLINES_PER_TICKER=8
OLLAMA_BATCH_TOP_N=20
OLLAMA_ENABLE_DASHBOARD_SUMMARY=true

# === EMAIL DIGEST (opcional) ===
EMAIL_REPORT_ENABLED=false
EMAIL_REPORT_TOP_N=20
EMAIL_REPORT_NEWS_PER_TICKER=3
EMAIL_REPORT_SUBJECT_PREFIX=Top oportunidades
EMAIL_REPORT_FROM=
EMAIL_REPORT_TO=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_USE_TLS=true
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
    - `OLLAMA_API_KEY=` (solo para cloud)
    - `OLLAMA_MODEL=gemma4:e2b`
4. Ejecutar pipeline normalmente con `python main.py`.

Flujo recomendado:
- Pipeline diario para refrescar ranking y features.
- Dashboard on-demand para revisar noticias Top 20 y alertas.
- Digest opcional por correo en texto plano al terminar `update_all.ps1` o `update_all.sh`.
- Si Ollama no esta disponible, el sistema debe degradar a fallback sin romper ejecucion.

## Integracion Ollama Cloud (API key)

Para desplegar en servidor sin depender de GPU/RAM local:

1. Configura en `project/.env`:
    - `ENABLE_LLM_SUMMARY=true`
    - `LLM_PROVIDER=ollama`
    - `OLLAMA_BASE_URL=http://localhost:11434`
    - `OLLAMA_API_KEY=<tu_api_key_cloud>`
    - `OLLAMA_MODEL=minimax-m2.7:cloud`
    - `OLLAMA_MAX_HEADLINES_PER_TICKER=3`
2. Ejecuta `python main.py`.
3. Verifica trazabilidad en `data/company_ranking.csv` con columnas:
    - `llm_provider_used`
    - `llm_status`
    - `llm_fallback_reason`
4. Si quieres digest por correo de las primeras 20 empresas, agrega tambien:
    - `EMAIL_REPORT_ENABLED=true`
    - `EMAIL_REPORT_FROM=<tu_correo_gmail>`
    - `EMAIL_REPORT_TO=<destino1,destino2>`
    - `SMTP_USER=<tu_correo_gmail>`
    - `SMTP_PASS=<app_password_de_gmail>`
    - `OLLAMA_BATCH_TOP_N=20`

Seguridad:
- Nunca subas `project/.env` al repositorio.
- Si una key se expone, rotala de inmediato.

## Proyecto Futuro

Se agrego un plan para desplegar la plataforma como pagina web en una instancia de Google Compute Engine, con fases de infraestructura, seguridad y operacion:

- `PROYECTO_FUTURO.md`

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
| Ollama cloud devuelve 401/403 | Verificar `OLLAMA_API_KEY` en `project/.env` y rotar key si fue revocada |
| El correo no sale | Verificar `EMAIL_REPORT_ENABLED=true`, `SMTP_USER`, `SMTP_PASS` y usar app password de Gmail |

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
