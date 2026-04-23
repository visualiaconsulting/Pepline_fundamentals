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
- **LLM Integrado**: Análisis de noticias y narrativa con **Gemini CLI** (por defecto) u Ollama local
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
│   │   ├── gemini_cli_client.py     # Integración con Gemini CLI (Primario)
│   │   └── llm_summary.py           # Narrativas LLM (Gemini/Ollama)
│   ├── models/
│   │   └── ranking_model.py         # Ordenamiento y exportación
│   ├── dashboard/
│   │   ├── app.py                   # App Streamlit principal (5 tabs)
...
```

---

## Instalación Rápida

### Requisitos

- Python 3.10+
- Conexión a internet (para yfinance y Finviz)
- **Gemini CLI** instalado y configurado en el PATH (opcional para reportes IA)

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
source .venv/activate

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

...

## Integración de LLM (Gemini CLI / Ollama)

El proyecto utiliza LLMs para generar narrativas de inversión automáticas.

### Gemini CLI (Por Defecto)
1. Instalar Gemini CLI en tu sistema.
2. Asegurarse de que el comando `gemini` sea ejecutable desde la terminal.
3. En `.env`:
   - `ENABLE_LLM_SUMMARY=true`
   - `LLM_PROVIDER=gemini`
   - `GEMINI_CLI_COMMAND=gemini`

### Ollama (Fallback / Segunda Opción)
Si Gemini CLI falla o prefieres usar modelos locales:
1. Instalar y levantar Ollama.
2. `ollama run gemma4:e2b`
3. En `.env`:
   - `LLM_PROVIDER=ollama` (o dejar `gemini` y el sistema usará Ollama como fallback automático si está configurado)
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `OLLAMA_MODEL=gemma4:e2b`

---

## Licencia

MIT License — ver [`LICENSE`](LICENSE) para detalles.

---

## Contacto

**Visualia Consulting**
- Issues y sugerencias: [GitHub Issues](https://github.com/visualiaconsulting/Pepline_fundamentals/issues)

---

*Última actualización: Abril 2026 · Versión 1.1.0*
