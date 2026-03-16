# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [5.1.0] - 2026-03-16

### Added
- `.env.example` for environment variable documentation
- `CONTRIBUTING.md` with development guidelines
- `CHANGELOG.md` (this file)
- `user_config.example.json` as a reference for user settings
- `requirements-lock.txt` for reproducible installs

### Changed
- Improved `README.md` with clearer setup instructions and feature previews
- Updated `requirements.txt` with version upper bounds for stability
- Enhanced `.gitignore` with IDE, OS, and packaging exclusions

### Removed
- `user_config.json` removed from version control (auto-generated on first run)

### Fixed
- `.gitignore` now correctly excludes user config and all cache files

---

## [5.0.0] - 2026-01-27

### Added
- Modular architecture: `src/config`, `src/data`, `src/analytics`, `src/ui`
- Smart caching with incremental updates and atomic writes
- CNN Fear & Greed Index integration
- 9 dashboard tabs: Market Overview, Internals, Volatility, Credit & Liquidity, Safe Havens, Rates & Bonds, Macro & Fed, Global Markets, Deep Dive
- Technical indicators: RSI, MACD, Bollinger Bands, SMA/EMA
- Risk analytics: Dual-Beta, Cornish-Fisher VaR, Sharpe/Sortino, Max Drawdown
- VIX full term structure (VIX1D → VIX9D → VIX → VIX3M)
- Sector rotation heatmaps (1M / 3M)
- Cross-asset normalized performance charts
- Dual-Beta asymmetric risk dashboard
- Seasonality heatmaps
- Historical move significance analysis
- Market regime detection
- GitHub Actions CI (flake8 + pytest)
- Unit tests for analytics modules

### Changed
- Refactored from single-file V4 to modular multi-package architecture
- Replaced standard Z-Score with Robust Z-Score (MAD-based)
- Data layer now supports both Yahoo Finance and FRED

---

## [4.x] - Pre-release

- Single-file Streamlit dashboard
- Basic charting and data fetching
