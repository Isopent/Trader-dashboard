# 📈 Alpha Trader Dashboard V5

> 一站式市場戰情分析平台 — 從宏觀經濟到個股深度剖析

A professional-grade market analysis dashboard that brings together **quantitative analysis**, **risk metrics**, **credit monitoring**, and **global macro indicators** in a single, real-time Streamlit interface.

---

## ✨ Key Features

| Tab | What It Does |
|-----|--------------|
| **📈 Market Overview** | CNN Fear & Greed gauge · Sector rotation (1M/3M) · Cross-asset performance |
| **⚙️ Market Internals** | Copper/Gold ratio · Cyclical vs Defensive · Market breadth (SPY vs RSP) |
| **📉 Equity Volatility** | VIX term structure (1D → 9D → Spot → 3M) · VVIX · SKEW · Backwardation alerts |
| **💧 Credit & Liquidity** | HY OAS · Liquidity spread · NFCI/STLFSI stress indices · Smart money flow |
| **🛡️ Safe Havens** | Gold/Silver ratio · USD/JPY · USD/CHF · XLU/SPY · TLT/SPY |
| **🏛️ Rates & Bonds** | US Treasury yield curve · MOVE bond volatility · Inversion alerts |
| **🏦 Macro & Fed** | CPI · Unemployment · Sahm Rule · Equity Risk Premium · BOJ data |
| **🌐 Global Markets** | Cross-market correlation · Global relative strength · Dual-Beta dashboard |
| **🔍 Deep Dive** | Single-ticker analysis: RSI, MACD, Bollinger Bands, Sharpe, Sortino, VaR, Seasonality |

### Data Sources
- **Yahoo Finance** — Equities, ETFs, Commodities, Forex, Crypto
- **FRED** — Treasury Yields, CPI, Unemployment, Financial Stress Indices
- **CNN** — Fear & Greed Index

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** (Anaconda recommended)
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Isopent/Trader-dashboard.git
cd Trader-dashboard

# 2. Create a virtual environment
conda create -n fin python=3.10
conda activate fin

# 3. Install dependencies
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at [http://localhost:8501](http://localhost:8501).

---

## ⚙️ Configuration

### Environment Variables (Optional)

Copy the example file and customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_EXPIRY_SECONDS` | `900` | How long cached data stays fresh (seconds) |
| `FULL_REFRESH_DAYS` | `7` | Days before a full data re-download |
| `RISK_FREE_RATE` | `0.04` | Annual risk-free rate for Sharpe/Sortino |

### User Preferences

Time range selections for each chart are automatically saved to `user_config.json`. This file is created on first use and excluded from version control.

---

## 🏗️ Architecture

```
Trader-dashboard/
├── app.py                      # Entry point & tab routing
├── src/
│   ├── config.py               # Centralized config (dataclasses + env vars)
│   ├── data/
│   │   ├── cache.py            # Smart CSV cache with atomic writes
│   │   └── manager.py          # Multi-source data fetching
│   ├── analytics/
│   │   ├── technical.py        # RSI, MACD, Bollinger, Z-Score, Volatility
│   │   └── risk.py             # Sharpe, Sortino, VaR, Dual-Beta, Drawdown
│   └── ui/
│       ├── components.py       # Reusable chart & KPI components
│       └── pages/
│           └── manager.py      # All tab rendering logic
├── tests/
│   └── test_analytics.py       # Unit tests (pytest)
├── .github/workflows/
│   └── python-app.yml          # CI: flake8 + pytest
├── .env.example                # Environment variable reference
├── requirements.txt            # Dependencies (with version bounds)
├── requirements-lock.txt       # Pinned versions for reproducibility
├── CONTRIBUTING.md             # Development & contribution guide
├── CHANGELOG.md                # Version history
└── LICENSE                     # MIT License
```

### How Data Flows

```
Yahoo Finance ─┐
FRED API ──────┤──▶ DataManager ──▶ CacheManager (CSV)
CNN API ───────┘         │
                         ▼
                  TechnicalAnalyzer
                  RiskAnalyzer
                         │
                         ▼
                    UIManager ──▶ Streamlit Tabs
```

**Caching Strategy:**
1. **Fresh** (< 15 min) → Return cached data instantly
2. **Stale** (< 7 days) → Incremental update (fetch only new data)
3. **Expired** (≥ 7 days) → Full refresh from all sources

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage (requires pytest-cov)
pytest tests/ -v --cov=src
```

---

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development environment setup
- Code style guidelines
- Commit message conventions
- Pull request process

---

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This tool is for **educational and informational purposes only**. It does not constitute financial advice. Always conduct your own research and consult qualified professionals before making investment decisions.
