from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "company_ranking.csv"
TOP10_FILE = ROOT_DIR / "data" / "top10_opportunities.csv"

CLASSIFICATION_ORDER = ["Excelente", "Buena", "Neutral", "Riesgosa"]
CLASSIFICATION_COLORS = {
    "Excelente": "#58a6ff",
    "Buena": "#3fb950",
    "Neutral": "#d29922",
    "Riesgosa": "#f85149",
}

SCORE_COMPONENTS = [
    "quality_score",
    "growth_score",
    "profitability_score",
    "risk_score",
    "valuation_score",
]

WEIGHT_MAP = {
    "quality_score": 0.30,
    "growth_score": 0.25,
    "profitability_score": 0.20,
    "risk_score": 0.15,
    "valuation_score": 0.10,
}
