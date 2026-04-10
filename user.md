# User Guide (Local Run)

Guia rapida para ejecutar el pipeline y usar el dashboard en local.

## 1) Preparar entorno

Windows PowerShell:

```powershell
cd C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\project\requirements.txt
pip install -r .\project\dashboard\requirements-dashboard.txt
```

## 2) Configurar variables

```powershell
cd .\project
copy .env.example .env
```

Edita `.env` y ajusta como minimo:

- `UNIVERSE_TICKERS`
- `ENABLE_LLM_SUMMARY`
- `LLM_PROVIDER` (`openai`, `ollama` o `rule-based`)

## 3) Ejecutar pipeline

```powershell
cd C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals\project
python .\main.py
```

Salidas principales:

- `project/data/company_ranking.csv`
- `project/data/top20_news.csv`
- `project/data/reports/{TICKER}_report.txt`

## 4) Abrir dashboard

```powershell
cd C:\Users\ekrde\OneDrive\ML2025\Pepline_fundamentals\project
python -m streamlit run dashboard/app.py --server.port 8500
```

Abrir en navegador: `http://localhost:8500`

## 5) Descargar documento desde IA Reports

En el tab IA Reports, seccion Documento diario:

- Elige `Top 2`, `Top 5`, `Top 10` o `Top 20`.
- Descarga `.md` o `.txt` con nombre:
  - `dashboard_top{N}_{MMDDYYYY}.md`
  - `dashboard_top{N}_{MMDDYYYY}.txt`
- Ejemplo: `dashboard_top2_04102026.txt`

## 6) Elegir carpeta exacta de guardado

Para controlar la ruta exacta en disco:

1. Completa el campo `Carpeta local para guardar snapshot`.
2. Haz clic en `Guardar snapshot del documento`.
3. El dashboard muestra la ruta completa guardada de ambos archivos (`.md` y `.txt`).

Nota: las descargas del navegador van a la carpeta configurada en tu navegador/SO.

## 7) Automatizacion diaria (opcional)

Desde la raiz del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_all.ps1
```

Opcional:

- `-SkipPipeline` para solo actualizar dependencias/codigo
- `-OpenDashboard -DashboardPort 8500` para abrir dashboard al finalizar
