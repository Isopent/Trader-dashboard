# Alpha Trader Dashboard V5

A comprehensive, professional-grade market analysis dashboard built with Streamlit and Plotly. This tool provides quantitative insights, technical analysis, risk metrics, and macro indicators to assist traders and investors in navigating global financial markets.

## Features

- **Market Overview**: CNN Fear & Greed Index integration and key market gauges.
- **Market Internals**: Advance/Decline lines, New Highs/Lows, and broad market breath.
- **Equity Volatility**: VIX term structure, VVIX, SKEW index analysis.
- **Credit & Liquidity**: High Yield OAS, Liquidity Spreads, and Financial Stress Indices (NFCI, STLFSI).
- **Safe Havens**: Gold, USD, Swiss Franc, and Yen tracking.
- **Rates & Bonds**: US Treasury Yields (2Y to 30Y) and MOVE Index for bond volatility.
- **Macro & Fed**: Key macroeconomic indicators and Fed tracking.
- **Global Markets**: Major global indices performance.
- **Deep Dive**: Dynamic asset analysis with technical indicators (RSI, MACD, Bollinger Bands) and risk metrics (Beta, VaR, Sharpe/Sortino).

## Architecture

The project follows a modular architecture:
- `app.py`: Main Streamlit application entry point.
- `src/config.py`: Global configuration and parameters.
- `src/data/`: Data management and caching layer (fetching from Yahoo Finance, FRED, etc.).
- `src/ui/`: UI components, charts, and layout management.
- `src/analytics/`: Quantitative analysis and metric calculations.
- `tests/`: Automated unit tests.

## Installation

### Prerequisites
- Python 3.9+ (Anaconda environment recommended)
- Git

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Isopent/Trader-dashboard.git
   cd Trader-dashboard
   ```

2. **Create and activate a virtual environment (Anaconda example):**
   ```bash
   conda create -n fin python=3.10
   conda activate fin
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the dashboard locally using Streamlit:

```bash
streamlit run app.py
```

The application will open in your default web browser (typically at `http://localhost:8501`).

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
