"""
Trader Dashboard
====================
Alpha Trader 戰情室 - Professional Trading Dashboard

A comprehensive market analysis dashboard featuring:
- Multi-source data integration (Yahoo Finance, FRED, CNN)
- Technical analysis indicators (RSI, MACD, Bollinger Bands)
- Risk analytics (Dual-Beta, VaR, Sharpe/Sortino Ratios)
- Market regime detection
- Credit & liquidity monitoring
- Global correlation analysis

Usage:
    streamlit run app.py
"""

import logging
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import config
from src.data import DataManager
from src.ui import UIManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=config.app_name,
    layout="wide",
    page_icon="📈"
)


def render_sidebar(dm: DataManager) -> None:
    """Render sidebar with controls and shortcuts."""
    with st.sidebar:
        st.header("⚙️ Data Control")
        
        if st.button("🔄 Force Update Data", key="force_update_btn"):
            with st.spinner("Updating..."):
                dm.fetch_data(force_update=True)
            st.success("Updated!")
            st.rerun()
        
        st.divider()
        st.subheader("🔗 Shortcuts")
        shortcuts = [
            ("👉 CNN Fear & Greed", "https://www.cnn.com/markets/fear-and-greed"),
            ("👉 WallstreetCN", "https://wallstreetcn.com/"),
            ("👉 FX678", "https://www.fx678.com/"),
            ("👉 Financial Juice", "https://www.financialjuice.com/"),
            ("👉 CME FedWatch", "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"),
            ("👉 VIX Central", "http://vixcentral.com/"),
            ("👉 Unusual Options", "https://www.barchart.com/options/unusual-activity/stocks"),
            ("👉 MacroMicro", "https://www.macromicro.me/")
        ]
        for label, url in shortcuts:
            st.markdown(f"[{label}]({url})")


def render_rates_bonds_tab(df, ui) -> None:
    """Render Rates & Bonds tab."""
    yields = [('US2Y', '2Y'), ('US10Y', '10Y'), ('US20Y', '20Y'), ('US30Y', '30Y')]
    colors = ['#90EE90', '#FFD700', '#FFA500', '#FF4500']
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        row_heights=[0.7, 0.3], subplot_titles=["US Treasury Yields", "Bond Volatility"])
    
    for i, (col, name) in enumerate(yields):
        if col in df.columns:
            series = df[col].dropna()
            if not series.empty:
                fig.add_trace(go.Scatter(x=series.index, y=series, name=name, 
                                        line=dict(color=colors[i], width=1.5)), row=1, col=1)
    
    if 'MOVE_Final' in df.columns:
        move = df['MOVE_Final'].dropna()
        if not move.empty:
            fig.add_trace(go.Scatter(x=move.index, y=move, name='MOVE', 
                                    line=dict(color='teal'), fill='tozeroy'), row=2, col=1)
    
    fig.update_layout(title="US Treasury Yields & Bond Volatility", height=600, 
                     template="plotly_dark", hovermode="x unified")
    
    # Curve inversion check
    if 'US2Y' in df.columns and 'US10Y' in df.columns:
        s2 = df['US2Y'].iloc[-1]
        s10 = df['US10Y'].iloc[-1]
        spread = s10 - s2
        if spread < 0:
            st.error(f"🚨 **Yield Curve Inverted**: {spread:.2f}%")
        else:
            st.success(f"✅ Yield Curve Normal: +{spread:.2f}%")
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("ℹ️ Inverted Curve (10Y < 2Y) = Recession Signal. MOVE Spike = Systemic Distress.")


def main():
    """Main application entry point."""
    logger.info(f"Starting {config.app_name} v{config.version}")
    
    # Initialize data manager
    dm = DataManager()
    
    # Render sidebar
    render_sidebar(dm)
    
    # Load data
    with st.spinner("Loading Market Data..."):
        df, source = dm.fetch_data()
        fg_data = dm.fetch_fear_greed_index()
    
    # Initialize UI manager
    ui = UIManager(df)
    
    # Title and caption
    st.title(config.app_name)
    st.caption(f"Data Source: {source} | Last Update: {dm.get_last_update_time()} | v{config.version}")
    
    # KPI Cards
    ui.render_kpi_cards()
    st.divider()
    
    # Tab navigation
    tabs = st.tabs([
        "📈 Market Overview",
        "⚙️ Market Internals",
        "📉 Equity Volatility",
        "💧 Credit & Liquidity",
        "🛡️ Safe Havens",
        "🏛️ Rates & Bonds",
        "🏦 Macro & Fed",
        "🌐 Global Markets",
        "🔍 Deep Dive"
    ])
    
    # Tab 0: Market Overview
    with tabs[0]:
        ui.render_market_overview(fg_data)
    
    # Tab 1: Market Internals
    with tabs[1]:
        ui.render_market_internals()
    
    # Tab 2: Equity Volatility
    with tabs[2]:
        ui.render_volatility_summary()
        ui.render_synced_subplots([
            {'col': 'VIX', 'name': 'VIX Index', 'color': '#FF4B4B', 
             'hlines': [{'val': 20, 'color': 'gray', 'text': 'Fear'}]},
            {'col': 'VVIX', 'name': 'VVIX Index', 'color': '#1E88E5'},
            {'col': 'SKEW', 'name': 'SKEW Index', 'color': '#9C27B0',
             'hlines': [{'val': 140, 'color': 'orange', 'text': 'Tail Risk'}]}
        ], "Equity Volatility Structure", "volatility_structure")
        st.caption("ℹ️ VIX: Fear Gauge. SKEW >140 = High Crash Risk.")
        st.divider()
        ui.render_vix_term_structure()
    
    # Tab 3: Credit & Liquidity
    with tabs[3]:
        ui.render_credit_liquidity_summary()
        ui.render_smart_money_chart()
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if 'HY_OAS' in df.columns:
                hy = df['HY_OAS'].dropna()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hy.index, y=hy, name='HY OAS', 
                                        line=dict(color='#FF5252'), fill='tozeroy'))
                fig.add_hline(y=5, line_dash="dash", line_color="yellow", annotation_text="Stress")
                fig.add_hline(y=8, line_dash="dash", line_color="red", annotation_text="Crisis")
                fig.update_layout(title="High Yield OAS", height=350, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Liquidity_Spread' in df.columns:
                liq = df['Liquidity_Spread'].dropna()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=liq.index, y=liq, name='CP-TBill', 
                                        line=dict(color='#00E676'), fill='tozeroy'))
                fig.update_layout(title="Liquidity Spread", height=350, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        ui.render_synced_subplots([
            {'col': 'NFCI', 'name': 'Chicago Fed NFCI', 'color': 'darkred',
             'hlines': [{'val': 0, 'color': 'gray', 'text': 'Tightening'}]},
            {'col': 'STLFSI', 'name': 'St. Louis FSI', 'color': '#D32F2F'}
        ], "Financial Stress Indices", "financial_stress")
    
    # Tab 4: Safe Havens
    with tabs[4]:
        ui.render_safe_havens()
    
    # Tab 5: Rates & Bonds
    with tabs[5]:
        render_rates_bonds_tab(df, ui)
    
    # Tab 6: Macro & Fed
    with tabs[6]:
        ui.render_macro_summary()
        ui.render_macro_data()
    
    # Tab 7: Global Markets
    with tabs[7]:
        ui.render_global_markets()
    
    # Tab 8: Deep Dive
    with tabs[8]:
        st.subheader("🔎 Dynamic Asset Analysis")
        ticker_input = st.text_input("Enter Ticker (e.g., NVDA, TSLA, AAPL)", value="NVDA").upper()
        
        if ticker_input:
            with st.spinner(f"Fetching {ticker_input}..."):
                df_ticker = dm.fetch_ticker_data(ticker_input)
                ticker_info = dm.fetch_ticker_info(ticker_input)
            
            if not df_ticker.empty:
                ui.render_deep_dive_chart(df_ticker, ticker_input, ticker_info)
            else:
                st.error(f"Could not fetch data for {ticker_input}.")


if __name__ == "__main__":
    main()
