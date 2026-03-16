# Contributing to Trader Dashboard

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Quick Start

### 1. Fork & Clone

```bash
git clone https://github.com/<your-username>/Trader-dashboard.git
cd Trader-dashboard
```

### 2. Set Up Environment

```bash
# Create virtual environment (Anaconda recommended)
conda create -n fin python=3.10
conda activate fin

# Install dependencies
pip install -r requirements.txt

# (Optional) Install dev tools
pip install pytest flake8 mypy
```

### 3. Verify setup

```bash
# Run tests
pytest tests/ -v

# Run the dashboard
streamlit run app.py
```

## 📂 Project Structure

```
Trader-dashboard/
├── app.py                  # Application entry point
├── src/
│   ├── config.py           # Configuration & settings
│   ├── data/
│   │   ├── cache.py        # CSV cache with atomic writes
│   │   └── manager.py      # Data fetching (Yahoo, FRED, CNN)
│   ├── analytics/
│   │   ├── technical.py    # RSI, MACD, Bollinger, Z-Score
│   │   └── risk.py         # Sharpe, Sortino, VaR, Dual-Beta
│   └── ui/
│       ├── components.py   # Reusable chart/KPI components
│       └── pages/
│           └── manager.py  # Tab rendering logic
├── tests/
│   └── test_analytics.py   # Unit tests
├── .github/workflows/
│   └── python-app.yml      # CI pipeline
└── requirements.txt
```

## 🔧 Development Guidelines

### Code Style

- **PEP 8** compliance (enforced by flake8 in CI)
- **Type hints** on all public functions
- **Docstrings** in Google style with `Args:` and `Returns:` sections
- Max line length: **127 characters**

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add VIX1D to term structure chart
fix: handle empty FRED response for CPI series
docs: update README installation steps
refactor: extract sector rotation logic
```

Prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`

### Testing

- Write tests for any new analytics functions
- Tests go in `tests/` using `pytest`
- Mock external API calls — don't hit real endpoints in tests
- Run `pytest tests/ -v` before submitting

### Branching

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and commit
3. Push and open a Pull Request against `main`

## 🐛 Reporting Bugs

Open an issue with:
- **Title**: Clear, one-line description
- **Steps to reproduce**: Exact steps or code to trigger the bug
- **Expected vs Actual**: What should happen vs what happens
- **Environment**: Python version, OS, and relevant package versions

## 💡 Feature Requests

Open an issue with the label `enhancement` and describe:
- **What** the feature does
- **Why** it's useful for traders/analysts
- **How** you envision the UI/UX

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
