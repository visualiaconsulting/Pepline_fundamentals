# Pipeline Automático de Equity Research Fundamental

Pipeline modular en Python para análisis fundamental y ranking de oportunidades en sectores estratégicos:
- IA / Semiconductores
- Energía
- Defensa / Aeroespacial
- Minería
- Automatización / Industriales
- Small & Mid Caps de alto crecimiento

## 1) Instalación

```bash
cd project
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configuración

El proyecto usa variables en `.env`.
Puedes partir de `.env.example`.

Variables clave:
- `UNIVERSE_TICKERS`: universo de empresas
- `TARGET_SECTORS`: keywords de sectores objetivo
- `SMALL_MID_CAP_THRESHOLD`: umbral de market cap (default 10B)
- `HIGH_GROWTH_THRESHOLD`: umbral de crecimiento YoY (default 15)
- `TICKER_DISCOVERY_ENABLED`: activa discovery aditivo de nuevos tickers
- `DISCOVERY_SOURCE`: fuente de discovery (`finviz`)
- `DISCOVERY_MAX_NEW_TICKERS`: máximo de nuevos tickers por corrida
- `DISCOVERY_MIN_MARKET_CAP` / `DISCOVERY_MAX_MARKET_CAP`: rango inicial del screener
- `DISCOVERY_MIN_SALES_GROWTH`: filtro de crecimiento de ventas para discovery
- `DISCOVERY_SECTORS`: sectores que alimentan el discovery
- `TICKER_BLOCKLIST`: tickers que nunca deben entrar por discovery
- `ENABLE_LLM_SUMMARY`: activar resumen opcional LLM (`true/false`)
- `LLM_PROVIDER`: proveedor LLM (`openai` u `ollama`)
- `OPENAI_API_KEY`: solo si usas OpenAI
- `OPENAI_MODEL`: modelo OpenAI
- `OLLAMA_BASE_URL`: endpoint local/remoto de Ollama
- `OLLAMA_API_KEY`: token para Ollama cloud (vacío en local)
- `OLLAMA_MODEL`: modelo Ollama (ejemplo: `gemma4:e2b`)
- `OLLAMA_TIMEOUT_SECONDS`: timeout por request al modelo
- `OLLAMA_MAX_HEADLINES_PER_TICKER`: limite de titulares por ticker para analisis

Recomendado para cloud con bajo consumo:
- `OLLAMA_MODEL=minimax-m2.7:cloud`
- `OLLAMA_MAX_HEADLINES_PER_TICKER=3`

### Modo Híbrido: Portafolio Preferido + Nuevas Oportunidades

El sistema soporta dos capas de universo:
- `UNIVERSE_TICKERS`: tu portafolio preferido o watchlist base. Siempre se incluye.
- Discovery automático: agrega hasta `DISCOVERY_MAX_NEW_TICKERS` candidatos adicionales usando un screener externo.

Flujo del discovery:
1. Lee tus sectores estratégicos desde `DISCOVERY_SECTORS`.
2. Los mapea a sectores del screener externo.
3. Filtra por crecimiento de ventas y capitalización.
4. Descarta duplicados y tickers de `TICKER_BLOCKLIST`.
5. Une el universo manual con los nuevos descubiertos.
6. Guarda trazabilidad en `data/discovery_log.csv`.

Ejemplo de configuración:

```env
UNIVERSE_TICKERS=NVDA,AMD,TSM,ASML,PLTR
TICKER_DISCOVERY_ENABLED=true
DISCOVERY_SOURCE=finviz
DISCOVERY_MAX_NEW_TICKERS=10
DISCOVERY_MIN_MARKET_CAP=100000000
DISCOVERY_MAX_MARKET_CAP=10000000000
DISCOVERY_MIN_SALES_GROWTH=15
DISCOVERY_SECTORS=semiconductors,energy,defense,mining,industrials
TICKER_BLOCKLIST=TSLA,BRK.B
```

## 3) Ejecución

```bash
python main.py
```

## Dashboard Ejecutivo (Tipo Power BI)

Visualizacion profesional sobre `data/company_ranking.csv` con:
- KPIs ejecutivos
- filtros globales (sector, clasificacion, origen ticker, score, market cap)
- tabs de resumen, fundamentales, riesgo/valuacion, scoring y noticias

Tab de noticias incluye:
- sentimiento por titular
- clasificacion de catalizadores
- impacto estimado +1d / +5d
- alertas negativas severas
- top noticias que mas movieron precio en Top 20

### Instalacion dashboard

```bash
pip install -r dashboard/requirements-dashboard.txt
```

### Ejecucion dashboard

```bash
streamlit run dashboard/app.py --server.port 8500
```

Al ejecutar una nueva corrida de `python main.py`, el dashboard refleja automaticamente los nuevos resultados del pipeline.

## 4) Outputs

Se generan automáticamente:
- `data/company_ranking.csv`
- `data/top10_opportunities.csv`
- `data/discovery_log.csv` (si discovery está activado)
- `data/reports/{TICKER}_report.txt`
- logs en `logs/pipeline.log`

## 5) Flujo del Pipeline

1. Ingesta financiera y noticias (`ingestion/`)
2. Discovery opcional y construcción del universo (`ingestion/ticker_discovery.py`, `utils/ticker_universe.py`)
3. Feature engineering y ratios (`processing/`)
4. Reglas de análisis fundamental (`analysis/fundamental_analysis.py`)
5. Scoring ponderado 0-100 (`analysis/scoring.py`)
6. Ranking y export de reportes (`models/ranking_model.py`)
7. Narrativa de tesis/riesgos/resumen opcional con LLM (`analysis/llm_summary.py`)

## 6) Flujo de Trabajo Recomendado

1. Actualiza codigo: `git pull origin main`
2. Verifica dependencias: `pip install -r requirements.txt`
3. Si usaras Ollama, confirma servicio y modelo (`ollama list`)
4. Si usaras cloud, confirma que `OLLAMA_API_KEY` este cargada en `.env`
5. Ejecuta pipeline: `python main.py`
6. Abre dashboard: `python -m streamlit run dashboard/app.py --server.port 8500`
7. En tab Noticias, pulsa actualizar para refrescar feed y analisis

### Ejecucion diaria automatizada (Windows)

Desde la raiz del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1
```

Si quieres ejecutar update y abrir dashboard automaticamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1 -OpenDashboard -DashboardPort 8500
```

Este script actualiza codigo, dependencias, valida Ollama (si `LLM_PROVIDER=ollama`) y ejecuta el pipeline.
