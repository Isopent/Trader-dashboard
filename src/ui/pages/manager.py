"""
Trader Dashboard V5 - UI Manager
=================================
Main UI orchestration for all dashboard pages.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ...config import config, user_settings
from ...analytics.technical import TechnicalAnalyzer, MarketAnalyzer
from ...analytics.risk import RiskAnalyzer
from ..components import ChartComponents, KPIComponents, TimeControl, SeasonalityHeatmap

logger = logging.getLogger(__name__)


class UIManager:
    """
    Main UI Manager for the Trader Dashboard.
    Orchestrates rendering of all dashboard pages and components.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.tech_analyzer = TechnicalAnalyzer()
        self.market_analyzer = MarketAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
    
    # ==================== KPI Cards ====================
    
    def render_kpi_cards(self) -> None:
        """Render top-level KPI metric cards."""
        cols = st.columns(5)
        tickers = ['SPY', 'VIX', 'US10Y', 'BTC', 'GOLD']
        
        for i, ticker in enumerate(tickers):
            if ticker not in self.df.columns:
                continue
            
            series = self.df[ticker].dropna()
            if series.empty or len(series) < 2:
                continue
            
            current = series.iloc[-1]
            prev = series.iloc[-2]
            pct_change = (current - prev) / prev * 100
            z_score = self.tech_analyzer.calculate_z_score(series)
            pr = self.tech_analyzer.calculate_pr(series)
            
            with cols[i]:
                st.metric(label=ticker, value=f"{current:.2f}", delta=f"{pct_change:.2f}%")
                z_color = "orange" if abs(z_score) > 2 else "gray"
                st.markdown(f"""
                <div style='font-size: 0.8em; color: gray;'>
                    Z-Score: <span style='color:{z_color}'><b>{z_score:.2f}</b></span><br>
                    PR (1Y): <b>{pr:.0f}%</b>
                </div>
                """, unsafe_allow_html=True)
    
    # ==================== Time Control ====================
    
    def _render_time_control(self, key: str) -> datetime:
        """Render time range selector and return start date."""
        st.caption(f"📅 View Range")
        return TimeControl.render(key)
    
    def _filter_by_date(self, start_date: datetime) -> pd.DataFrame:
        """Filter DataFrame by start date."""
        return self.df[self.df.index >= start_date]
    
    # ==================== Synced Subplots ====================
    
    def render_synced_subplots(
        self, 
        chart_configs: List[Dict], 
        title: str, 
        key_suffix: str,
        height: int = 600
    ) -> None:
        """Render synchronized subplot charts with time control."""
        start_date = self._render_time_control(key_suffix)
        df_plot = self._filter_by_date(start_date)
        
        if df_plot.empty:
            st.warning("No data in selected range.")
            return
        
        fig = ChartComponents.create_subplot_chart(chart_configs, df_plot, title, height)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")
    
    # ==================== Market Overview ====================
    
    def render_market_overview(self, fg_data: Optional[Dict] = None) -> None:
        """Render Market Overview tab content."""
        # Fear & Greed Index
        if fg_data:
            self._render_fear_greed(fg_data)
            st.divider()
        
        # Sector Rotation
        self.render_sector_rotation()
        st.divider()
        
        # Cross-Asset Performance
        self._render_cross_asset_performance()
    
    def _render_fear_greed(self, fg_data: Dict) -> None:
        """Render Fear & Greed gauge."""
        score = fg_data.get('score', 50)
        rating = fg_data.get('rating', 'Neutral')
        
        st.subheader("😨 CNN Fear & Greed Index")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            fig = ChartComponents.create_gauge_chart(score, rating)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.info(f"Current Market Sentiment is **{rating.upper()}** ({score:.1f}).")
            st.caption("ℹ️ **Fear & Greed**: <25 = Extreme Fear (Buy). >75 = Extreme Greed (Sell).")
    
    def render_sector_rotation(self) -> None:
        """Render sector rotation charts."""
        st.subheader("🔄 Sector Rotation (1M & 3M)")
        
        sectors = {
            'XLK': 'Tech', 'XLF': 'Financials', 'XLE': 'Energy', 'XLV': 'Health',
            'XLY': 'Discretionary', 'XLP': 'Staples', 'XLI': 'Industrials',
            'XLB': 'Materials', 'XLRE': 'Real Estate', 'XLC': 'Comm.', 'XLU': 'Utilities'
        }
        
        data_1m, data_3m = {}, {}
        
        for ticker, name in sectors.items():
            col = f"{ticker}_Adj" if f"{ticker}_Adj" in self.df.columns else ticker
            if col not in self.df.columns:
                continue
            
            series = self.df[col].dropna()
            if len(series) < 63:
                continue
            
            data_1m[name] = series.pct_change(21).iloc[-1] * 100
            data_3m[name] = series.pct_change(63).iloc[-1] * 100
        
        if data_1m:
            tab1, tab2 = st.tabs(["1-Month", "3-Month"])
            with tab1:
                fig = ChartComponents.create_bar_chart(data_1m, "Sector Relative Strength (1M)")
                st.plotly_chart(fig, use_container_width=True)
            with tab2:
                fig = ChartComponents.create_bar_chart(data_3m, "Sector Relative Strength (3M)")
                st.plotly_chart(fig, use_container_width=True)
    
    def _render_cross_asset_performance(self) -> None:
        """Render cross-asset normalized performance chart."""
        st.subheader("🌍 Cross-Asset Performance (Normalized)")
        
        options = ["YTD", "6 Months", "1 Year", "3 Years", "5 Years", "Max"]
        default = user_settings.get_range_setting("cross_asset", "1 Year")
        if default not in options:
            default = "1 Year"
        
        selection = st.radio("Normalize From:", options, horizontal=True,
                            index=options.index(default), key="radio_cross_asset")
        
        if selection != default:
            user_settings.set_range_setting("cross_asset", selection)
        
        # Calculate start date
        now = datetime.now()
        start_map = {
            "YTD": datetime(now.year, 1, 1),
            "6 Months": now - timedelta(days=180),
            "1 Year": now - timedelta(days=365),
            "3 Years": now - timedelta(days=365*3),
            "5 Years": now - timedelta(days=365*5),
            "Max": datetime(2000, 1, 1)
        }
        start_date = start_map.get(selection, now - timedelta(days=365))
        
        assets = ['SPY', 'QQQ', 'IWM', 'TLT', 'GOLD', 'BTC']
        valid = [a for a in assets if a in self.df.columns]
        
        if valid:
            df_slice = self.df[valid].copy()
            df_slice = df_slice[df_slice.index >= start_date].dropna(how='all')
            
            if not df_slice.empty:
                fig = go.Figure()
                for asset in valid:
                    series = df_slice[asset].dropna()
                    if not series.empty and series.iloc[0] > 0:
                        normalized = (series / series.iloc[0]) * 100
                        fig.add_trace(go.Scatter(x=normalized.index, y=normalized, name=asset))
                
                fig.update_layout(
                    height=450, template="plotly_dark", hovermode="x unified",
                    yaxis_title=f"Return (Base=100)",
                    xaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== Market Internals ====================
    
    def render_market_internals(self) -> None:
        """Render Market Internals tab."""
        st.subheader("⚙️ Market Internals & Cyclical Indicators")
        
        start_date = self._render_time_control("market_internals")
        df_plot = self._filter_by_date(start_date)
        
        col1, col2 = st.columns(2)
        
        # Copper/Gold Ratio
        with col1:
            self._render_copper_gold_ratio(df_plot)
        
        # XLY/XLP Ratio
        with col2:
            self._render_cyclical_defensive(df_plot)
        
        st.divider()
        
        # Market Breadth
        self._render_market_breadth(df_plot)
    
    def _render_copper_gold_ratio(self, df: pd.DataFrame) -> None:
        """Render Copper/Gold ratio chart."""
        if 'COPPER' not in df.columns or 'GOLD' not in df.columns:
            return
        
        copper = df['COPPER'].dropna()
        gold = df['GOLD'].dropna()
        idx = copper.index.intersection(gold.index)
        
        if idx.empty:
            return
        
        ratio = (copper.loc[idx] / gold.loc[idx]) * 1000
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ratio.index, y=ratio, name='Copper/Gold', line=dict(color='orange')))
        fig.update_layout(title="Copper/Gold Ratio", height=350, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("ℹ️ Rising = Economic Recovery. Falling = Slowdown Risk.")
    
    def _render_cyclical_defensive(self, df: pd.DataFrame) -> None:
        """Render XLY/XLP ratio."""
        if 'XLY' not in df.columns or 'XLP' not in df.columns:
            return
        
        xly = df['XLY'].dropna()
        xlp = df['XLP'].dropna()
        idx = xly.index.intersection(xlp.index)
        
        if idx.empty:
            return
        
        ratio = xly.loc[idx] / xlp.loc[idx]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ratio.index, y=ratio, name='XLY/XLP', line=dict(color='#00E676')))
        if len(ratio) > 200:
            sma = ratio.rolling(200).mean()
            fig.add_trace(go.Scatter(x=sma.index, y=sma, name='200D SMA', line=dict(color='gray', width=1)))
        
        fig.update_layout(title="Cyclical vs Defensive", height=350, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("ℹ️ Rising = Risk On. Falling = Defensive Rotation.")
    
    def _render_market_breadth(self, df: pd.DataFrame) -> None:
        """Render market breadth (SPY vs RSP)."""
        if 'SPY' not in df.columns or 'RSP' not in df.columns:
            return
        
        spy = df['SPY'].dropna()
        rsp = df['RSP'].dropna()
        idx = spy.index.intersection(rsp.index)
        
        if idx.empty:
            return
        
        spy_norm = spy.loc[idx] / spy.loc[idx].iloc[0] * 100
        rsp_norm = rsp.loc[idx] / rsp.loc[idx].iloc[0] * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spy_norm.index, y=spy_norm, name='SPY (Cap Weight)', line=dict(color='#2962FF')))
        fig.add_trace(go.Scatter(x=rsp_norm.index, y=rsp_norm, name='RSP (Equal Weight)', line=dict(color='#FFD600')))
        fig.update_layout(title="Market Breadth (SPY vs RSP)", height=400, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("ℹ️ SPY > RSP = Mega-cap dominance. RSP > SPY = Healthy breadth.")
    
    # ==================== Volatility ====================
    
    def render_volatility_summary(self) -> None:
        """Render volatility health monitor."""
        st.markdown("### 🌪️ Volatility Health Monitor")
        cols = st.columns(5)
        
        indicators = [
            ('VIX', 'VIX (Fear)', [(30, 'Panic', 'red'), (20, 'Fear', 'orange')]),
            ('VVIX', 'VVIX', [(135, 'High', 'red'), (110, 'Elevated', 'orange')]),
            ('SKEW', 'SKEW (Tail)', [(145, 'Crash Risk', 'red'), (135, 'Tail Risk', 'orange')])
        ]
        
        for i, (col_name, label, thresholds) in enumerate(indicators):
            if col_name in self.df.columns:
                series = self.df[col_name].dropna()
                if not series.empty:
                    val = series.iloc[-1]
                    with cols[i]:
                        KPIComponents.render_status_indicator(label, val, thresholds)
        
        # Term Structure (3M)
        if 'VIX' in self.df.columns and 'VIX3M' in self.df.columns:
            v = self.df['VIX'].dropna()
            v3 = self.df['VIX3M'].dropna()
            idx = v.index.intersection(v3.index)
            if not idx.empty:
                spread = (v.loc[idx] - v3.loc[idx]).iloc[-1]
                with cols[3]:
                    thresholds = [(0, 'Backwardation', 'red'), (-2, 'Flattening', 'orange')]
                    KPIComponents.render_status_indicator("Term (3M)", spread, thresholds, "{:.2f}")
        
        # Short Term (9D) - NEW
        if 'VIX' in self.df.columns and 'VIX9D' in self.df.columns:
            v = self.df['VIX'].dropna()
            v9 = self.df['VIX9D'].dropna()
            idx = v.index.intersection(v9.index)
            if not idx.empty:
                val = (v9.loc[idx] - v.loc[idx]).iloc[-1]
                with cols[4]:
                    thresholds = [(2, 'Panic', 'red'), (0, 'Fear', 'orange')]
                    KPIComponents.render_status_indicator("Short (9D)", val, thresholds, "{:.2f}")
        
        st.divider()
    
    def render_vix_term_structure(self) -> None:
        """Render VIX term structure chart with VIX9D and VIX1D."""
        if 'VIX' not in self.df.columns or 'VIX3M' not in self.df.columns:
            return
        
        vix = self.df['VIX'].dropna()
        vix3m = self.df['VIX3M'].dropna()
        vix9d = self.df['VIX9D'].dropna() if 'VIX9D' in self.df.columns else None
        vix1d = self.df['VIX1D'].dropna() if 'VIX1D' in self.df.columns else None
        
        # Align all available series
        dfs = [vix, vix3m]
        if vix9d is not None: dfs.append(vix9d)
        if vix1d is not None: dfs.append(vix1d)
        
        common_idx = dfs[0].index
        for d in dfs[1:]:
            common_idx = common_idx.intersection(d.index)
        
        vix = vix.loc[common_idx]
        vix3m = vix3m.loc[common_idx]
        if vix9d is not None: vix9d = vix9d.loc[common_idx]
        if vix1d is not None: vix1d = vix1d.loc[common_idx]
        
        spread = vix - vix3m
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        
        # Main VIX traces
        fig.add_trace(go.Scatter(x=vix.index, y=vix, name='VIX (Spot)', line=dict(color='#FF4B4B', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=vix3m.index, y=vix3m, name='VIX3M (3-Month)', line=dict(color='#1E88E5')), row=1, col=1)
        
        # Add VIX9D and VIX1D if available
        if vix9d is not None:
            fig.add_trace(go.Scatter(x=vix9d.index, y=vix9d, name='VIX9D (9-Day)', line=dict(color='orange', width=1, dash='dot')), row=1, col=1)
        if vix1d is not None:
            fig.add_trace(go.Scatter(x=vix1d.index, y=vix1d, name='VIX1D (1-Day)', line=dict(color='yellow', width=1, dash='dot')), row=1, col=1)
        
        # Spread chart
        fig.add_trace(go.Scatter(x=spread.index, y=spread, name='Spread (VIX-VIX3M)', fill='tozeroy', line=dict(color='gray')), row=2, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="white", row=2, col=1)
        
        fig.update_layout(
            title=dict(text="VIX Term Structure (1D - 9D - Spot - 3M)", y=0.95),
            height=500, template="plotly_dark", hovermode="x unified",
            margin=dict(t=80),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Alerts
        if spread.iloc[-1] > 0:
            st.error(f"🚨 **Backwardation (High Stress)**: VIX > VIX3M ({spread.iloc[-1]:.2f}). Hedging costs high.")
        
        # Short-term inversion alert
        if vix9d is not None:
            s_spread = vix9d.iloc[-1] - vix.iloc[-1]
            if s_spread > 0:
                st.warning(f"⚠️ **Short-Term Fear**: VIX9D > VIX (+{s_spread:.2f}). 0DTE/Event Risk active.")
        
        st.caption("ℹ️ Normal = Upward Sloping (VIX1D < VIX9D < VIX < VIX3M). **Inversion = Fear/Crash Risk**.")
    
    # ==================== Credit & Liquidity ====================
    
    def render_credit_liquidity_summary(self) -> None:
        """Render credit and liquidity health monitor with 7 indicators."""
        st.markdown("### 🚦 Credit & Liquidity Health")
        cols = st.columns(7)
        
        # 1. Credit Appetite (IEF/HYG)
        if 'Credit_Stress_Ratio' in self.df.columns:
            series = self.df['Credit_Stress_Ratio'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                z = self.tech_analyzer.calculate_z_score(series)
                with cols[0]:
                    status = "Panic" if z > 2 else ("Caution" if z > 0 else "Risk On")
                    color = "red" if z > 2 else ("orange" if z > 0 else "green")
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>Credit Appetite</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{val:.2f}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>Z: {z:.1f} ({status})</div>", unsafe_allow_html=True)
        
        # 2. HY OAS
        if 'HY_OAS' in self.df.columns:
            series = self.df['HY_OAS'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                with cols[1]:
                    thresholds = [(6, 'Stress', 'red'), (4, 'Warning', 'orange')]
                    KPIComponents.render_status_indicator("HY OAS", val, thresholds, "{:.2f}%")
        
        # 3. Liquidity Spread (CP - TBill)
        if 'Liquidity_Spread' in self.df.columns:
            series = self.df['Liquidity_Spread'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                pct = self.tech_analyzer.calculate_pr(series)
                with cols[2]:
                    color = "red" if val > 0.50 else ("orange" if val > 0.20 else "green")
                    status = "Stress" if val > 0.50 else ("Elevated" if val > 0.20 else "Normal")
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>Liq. Spread</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{val:.2f}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>PR: {pct:.0f}%</div>", unsafe_allow_html=True)
        
        # 4. Funding Stress (SOFR - FedFunds)
        if 'SOFR' in self.df.columns and 'FEDFUNDS' in self.df.columns:
            s = self.df['SOFR'].dropna()
            f = self.df['FEDFUNDS'].dropna()
            idx = s.index.intersection(f.index)
            if not idx.empty:
                val = (s.loc[idx] - f.loc[idx]).iloc[-1]
                with cols[3]:
                    color = "red" if val > 0.10 else ("orange" if val > 0.05 else "green")
                    status = "Scarcity" if val > 0.10 else ("Tight" if val > 0.05 else "Stable")
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>Funding Stress</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{val:.2f}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>{status}</div>", unsafe_allow_html=True)
        
        # 5. NFCI
        if 'NFCI' in self.df.columns:
            series = self.df['NFCI'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                with cols[4]:
                    thresholds = [(0.5, 'Systemic', 'red'), (0, 'Tightening', 'orange')]
                    KPIComponents.render_status_indicator("NFCI", val, thresholds)
        
        # 6. STLFSI
        if 'STLFSI' in self.df.columns:
            series = self.df['STLFSI'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                with cols[5]:
                    color = "red" if val > 1.0 else ("orange" if val > 0 else "green")
                    status = "Crisis" if val > 1.0 else ("Stress" if val > 0 else "Normal")
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>STL FSI</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{val:.2f}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>{status}</div>", unsafe_allow_html=True)
        
        # 7. Reserve Scarcity (IORB - EFFR)
        if 'IORB_EFFR_Spread' in self.df.columns:
            series = self.df['IORB_EFFR_Spread'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                with cols[6]:
                    color = "red" if val < 0 else ("orange" if val < 0.05 else "green")
                    status = "Scarce" if val < 0 else ("Draining" if val < 0.05 else "Abundant")
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>Rsrv. Scarcity</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{val:.2f}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>{status}</div>", unsafe_allow_html=True)
        
        st.divider()
    
    def render_smart_money_chart(self) -> None:
        """Render credit risk appetite chart."""
        st.subheader("🧠 Credit Risk Appetite")
        
        start_date = self._render_time_control("smart_money")
        
        if 'Credit_Stress_Ratio' not in self.df.columns or 'SPY' not in self.df.columns:
            st.warning("Missing data for Credit Risk chart.")
            return
        
        df_plot = self._filter_by_date(start_date)
        if df_plot.empty:
            return
        
        ratio = df_plot['Credit_Stress_Ratio']
        spy = df_plot['SPY']
        
        # Z-score on full history
        ratio_full = self.df['Credit_Stress_Ratio']
        z_full = (ratio_full - ratio_full.rolling(252).mean()) / ratio_full.rolling(252).std()
        z_score = z_full[z_full.index >= start_date]
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=spy.index, y=spy, name='SPY', line=dict(color='gray', width=1)), secondary_y=True)
        fig.add_trace(go.Scatter(x=z_score.index, y=z_score, name='Credit Z-Score', line=dict(color='orange', width=2)), secondary_y=False)
        fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="Risk Aversion")
        fig.add_hline(y=-2, line_dash="dash", line_color="green", annotation_text="Risk On")
        
        fig.update_layout(title="Credit Risk Appetite (IEF/HYG vs SPY)", height=500, template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("ℹ️ Rising = Quality Flight. Falling = Credit Seeking.")
    
    # ==================== Safe Havens ====================
    
    def render_safe_havens(self) -> None:
        """Render safe haven indicators."""
        st.subheader("🛡️ Safe Haven Indicators")
        
        # 1. Gold/Silver & USD/JPY & USD/CHF
        self.render_synced_subplots([
            {'col': 'Gold_Silver_Ratio', 'name': 'Gold/Silver Ratio', 'color': 'gold'},
            {'col': 'USDJPY', 'name': 'USD/JPY', 'color': 'green'},
            {'col': 'USDCHF', 'name': 'USD/CHF (Inv. Safe Haven)', 'color': 'red'}
        ], "Safe Haven Currencies", "safe_havens_1")
        st.caption("ℹ️ **Gold/Silver Ratio**: High = Deflation/Risk Off. | **USD/JPY**: High = Risk On. | **USD/CHF**: High = Weak Franc (Risk On). Low = Strong Franc (Risk Off).")
        
        st.divider()
        
        # 2. Utilities vs Market (XLU/SPY) & Bonds vs Stocks (TLT/SPY)
        col1, col2 = st.columns(2)
        
        with col1:
            if 'XLU' in self.df.columns and 'SPY' in self.df.columns:
                xlu_spy = self.df['XLU'] / self.df['SPY']
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=xlu_spy.index, y=xlu_spy, name='XLU/SPY', line=dict(color='#00CC96')))
                fig.update_layout(
                    title="Utilities vs Market (Defensive/Cyclical)",
                    height=350, template="plotly_dark", hovermode="x unified",
                    xaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("ℹ️ **XLU/SPY**: Rising = Defensive Outperformance (**Risk Off**). Falling = Cyclical (**Risk On**).")
        
        with col2:
            if 'TLT' in self.df.columns and 'SPY' in self.df.columns:
                tlt_spy = self.df['TLT'] / self.df['SPY']
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=tlt_spy.index, y=tlt_spy, name='TLT/SPY', line=dict(color='#AB63FA')))
                fig.update_layout(
                    title="Bonds vs Stocks (TLT/SPY)",
                    height=350, template="plotly_dark", hovermode="x unified",
                    xaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("ℹ️ **TLT/SPY**: Rising = Flight to Safety (**Risk Off**). Falling = Risk Appetite (**Risk On**).")
    
    # ==================== Macro ====================
    
    def render_macro_summary(self) -> None:
        """Render macro health monitor."""
        st.markdown("### 🏦 Macro Health Monitor")
        cols = st.columns(6)
        
        # CPI
        if 'CPI' in self.df.columns:
            series = self.df['CPI'].dropna()
            if not series.empty:
                val = series.pct_change(12).iloc[-1] * 100
                with cols[0]:
                    thresholds = [(4, 'High', 'red'), (2.5, 'Elevated', 'orange')]
                    KPIComponents.render_status_indicator("CPI Inflation", val, thresholds, "{:.1f}%")
        
        # 10Y Yield
        if 'US10Y' in self.df.columns:
            series = self.df['US10Y'].dropna()
            if not series.empty:
                val = series.iloc[-1]
                with cols[1]:
                    st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>10Y Yield</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:1.5em; color:white'><b>{val:.2f}%</b></div>", unsafe_allow_html=True)
        
        # Sahm Rule
        if 'UNRATE' in self.df.columns:
            unrate = self.df['UNRATE'].dropna()
            if len(unrate) > 12:
                unrate_3m = unrate.rolling(3).mean()
                sahm = (unrate_3m - unrate_3m.rolling(12).min()).iloc[-1]
                with cols[3]:
                    thresholds = [(0.5, 'Recession', 'red'), (0.4, 'Warning', 'orange')]
                    KPIComponents.render_status_indicator("Sahm Rule", sahm, thresholds)
        
        # Curve
        if 'US10Y' in self.df.columns and 'US2Y' in self.df.columns:
            s10 = self.df['US10Y'].iloc[-1]
            s2 = self.df['US2Y'].iloc[-1]
            curve = s10 - s2
            with cols[4]:
                color = "red" if curve < 0 else ("orange" if curve < 0.2 else "green")
                status = "Inverted" if curve < 0 else ("Flat" if curve < 0.2 else "Normal")
                st.markdown(f"<div style='text-align:center; font-size:0.8em; color:gray'>Curve (10-2)</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; font-size:1.5em; color:{color}'><b>{curve:.2f}%</b></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; font-size:0.8em; color:{color}'>{status}</div>", unsafe_allow_html=True)
        
        st.divider()
    
    def render_macro_data(self) -> None:
        """Render macro data charts."""
        st.subheader("🏦 Central Bank & Macro Data")
        
        region = st.radio("Select Region", ["🇺🇸 US Fed", "🇯🇵 Japan BOJ"], horizontal=True, label_visibility="collapsed")
        
        start_date = self._render_time_control(f"macro_{region}")
        df_plot = self._filter_by_date(start_date)
        
        if region == "🇺🇸 US Fed":
            self._render_us_macro(df_plot)
        else:
            self._render_japan_macro(df_plot)
    
    def _render_us_macro(self, df: pd.DataFrame) -> None:
        """Render US macro charts."""
        col1, col2 = st.columns(2)
        
        # CPI
        with col1:
            if 'CPI' in df.columns:
                cpi = df['CPI'].dropna()
                inflation = cpi.pct_change(12) * 100
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=inflation.index, y=inflation, name='CPI YoY', line=dict(color='purple')))
                fig.update_layout(title="US Inflation (CPI YoY)", height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        # Unemployment
        with col2:
            if 'UNRATE' in df.columns:
                unrate = df['UNRATE'].dropna()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=unrate.index, y=unrate, name='Unemployment', line=dict(color='teal')))
                fig.update_layout(title="US Unemployment Rate", height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        # US Macro Extensions (Sahm Rule, ERP)
        st.divider()
        self._render_us_macro_extensions(df)
    
    def _render_us_macro_extensions(self, df: pd.DataFrame) -> None:
        """Render advanced macro indicators: Sahm Rule and ERP."""
        st.subheader("🧠 Advanced Macro Indicators")
        
        col1, col2 = st.columns(2)
        
        # 1. Sahm Rule
        with col1:
            if 'UNRATE' in self.df.columns:
                unrate = self.df['UNRATE'].dropna()
                if len(unrate) > 12:
                    unrate_3m = unrate.rolling(3).mean()
                    sahm_full = unrate_3m - unrate_3m.rolling(12).min()
                    
                    # Filter to display window
                    start_date = df.index.min() if not df.empty else self.df.index.min()
                    sahm = sahm_full[sahm_full.index >= start_date]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=sahm.index, y=sahm, name='Sahm Rule', fill='tozeroy', line=dict(color='orange')))
                    fig.add_hline(y=0.50, line_dash="dash", line_color="red", annotation_text="Recession Threshold (0.50)")
                    
                    curr_sahm = sahm.iloc[-1] if not sahm.empty else 0
                    status = "RECESSION" if curr_sahm >= 0.50 else "Expansion"
                    color = "red" if curr_sahm >= 0.50 else "green"
                    
                    fig.update_layout(
                        title=f"Sahm Rule Indicator ({status})",
                        height=350, template="plotly_dark",
                        xaxis=dict(showgrid=False),
                        yaxis=dict(autorange=True, fixedrange=False)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"ℹ️ **Current**: <span style='color:{color}'><b>{curr_sahm:.2f}</b></span>. **> 0.50** signals recession start.", unsafe_allow_html=True)
        
        # 2. Equity Risk Premium (ERP)
        with col2:
            if 'US10Y' in df.columns and 'T10YIE' in df.columns:
                us10y = df['US10Y'].dropna()
                breakeven = df['T10YIE'].dropna()
                idx = us10y.index.intersection(breakeven.index)
                
                if not idx.empty:
                    real_yield = us10y.loc[idx] - breakeven.loc[idx]
                    market_ey = 4.5  # Estimated S&P 500 earnings yield
                    erp = market_ey - real_yield
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=erp.index, y=erp, name='Est. ERP', line=dict(color='cyan')))
                    fig.add_hline(y=3.0, line_dash="dash", line_color="yellow", annotation_text="Expensive (<3%)")
                    
                    fig.update_layout(
                        title="Implied Equity Risk Premium (Est.)",
                        height=350, template="plotly_dark",
                        xaxis=dict(showgrid=False),
                        yaxis=dict(autorange=True, fixedrange=False)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("ℹ️ **ERP**: Earnings Yield (Est 4.5%) - Real Yield. **< 3% = Stocks Expensive**. **> 5% = Stocks Cheap**.")
    
    def _render_japan_macro(self, df: pd.DataFrame) -> None:
        """Render Japan macro charts."""
        col1, col2 = st.columns(2)
        
        with col1:
            if 'JPN_UNRATE' in df.columns:
                unrate = df['JPN_UNRATE'].dropna()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=unrate.index, y=unrate, line=dict(color='teal')))
                fig.update_layout(title="Japan Unemployment", height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'JPN_10Y' in df.columns:
                y10 = df['JPN_10Y'].dropna()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=y10.index, y=y10, line=dict(color='cyan')))
                fig.update_layout(title="Japan 10Y Yield", height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== Global Markets ====================
    
    GLOBAL_MARKETS = {
        'EFA': 'Developed (EFA)', 'VGK': 'Europe (VGK)', 'EWJ': 'Japan (EWJ)',
        'EEM': 'Emerging (EEM)', 'MCHI': 'China (MCHI)', 'INDA': 'India (INDA)',
        'EWY': 'Korea (EWY)', 'EWZ': 'Brazil (EWZ)'
    }
    
    def render_global_markets(self) -> None:
        """Render global markets correlation analysis."""
        self.render_correlation_analysis()
    
    def render_correlation_analysis(self) -> None:
        """Render comprehensive correlation analysis with insights."""
        st.subheader("🔗 Market Correlation Analysis (90D)")
        
        assets = ['SPY', 'QQQ', 'IWM', 'TLT', 'GOLD', 'BTC', 'VIX', 'USDJPY', 'DX-Y']
        valid = [a for a in assets if a in self.df.columns]
        
        if not valid:
            st.warning("Insufficient data for correlation.")
            return
        
        # Build correlation matrix
        adj_cols = []
        for a in valid:
            col = f"{a}_Adj" if f"{a}_Adj" in self.df.columns else a
            adj_cols.append(self.df[col].rename(a))
        
        df_corr = pd.concat(adj_cols, axis=1)
        corr_matrix = df_corr.pct_change().tail(90).corr()
        
        # Generate and display insights
        if 'SPY' in corr_matrix.columns:
            spy_corr = corr_matrix['SPY'].drop('SPY').sort_values(ascending=False)
            insights = self._generate_correlation_insights(spy_corr)
            if insights:
                st.info(" | ".join(insights))
            
            last_date = self.df.index[-1].strftime('%Y-%m-%d')
            st.caption(f"📅 **Data Updated**: {last_date} | Window: 90 Trading Days")
        
        # Three tabs for different views
        tab1, tab2, tab3 = st.tabs(["🇺🇸 Asset Class Correlation", "🌍 Global Relative Strength", "🌐 Global Correlation"])
        
        with tab1:
            self._render_asset_correlation(corr_matrix, valid)
        
        with tab2:
            self._render_global_relative_strength()
        
        with tab3:
            self._render_global_spy_correlation()
        
        # Full correlation matrix in expander
        with st.expander("📚 Methodology & Full Correlation Matrix"):
            st.markdown("""
            ### 📊 Methodology
            * **Correlation**: Pearson Correlation Coefficient (90-Day Rolling Window).
            * **Interpretation**:
                * **+1.0**: Perfect positive correlation (Moves exactly together).
                * **0.0**: Uncorrelated (True diversification).
                * **-1.0**: Perfect inverse correlation (Perfect hedge).
            * **Relative Strength**: 21-Day (1 Month) percentage change.
            """)
            fig = ChartComponents.create_heatmap(corr_matrix, "Full Correlation Matrix")
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Dual-Beta Dashboard
        self.render_dual_beta_dashboard(valid)
    
    def _generate_correlation_insights(self, spy_corr: pd.Series) -> list:
        """Generate analyst-level insights from SPY correlations."""
        insights = []
        
        # SPY vs QQQ (Equity Risk)
        if 'QQQ' in spy_corr.index:
            c = spy_corr['QQQ']
            if c > 0.9:
                insights.append(f"⚠️ **Broad Rally ({c:.2f})**: High SPY-QQQ correlation. Unified Risk-On.")
            elif c < 0.7:
                insights.append(f"🔄 **Sector Rotation ({c:.2f})**: Tech diverging from broad market.")
        
        # SPY vs TLT (Interest Rate Risk)
        if 'TLT' in spy_corr.index:
            c = spy_corr['TLT']
            if c > 0.3:
                insights.append(f"🚨 **Stock/Bond ({c:.2f})**: Positive correlation = Diversification Failure.")
            elif c < -0.3:
                insights.append(f"✅ **Stock/Bond ({c:.2f})**: Healthy hedge working.")
        
        # SPY vs BTC (Risk Appetite)
        if 'BTC' in spy_corr.index:
            c = spy_corr['BTC']
            if c > 0.5:
                insights.append(f"🔥 **Crypto Risk-On ({c:.2f})**: BTC trading with stocks.")
            elif c < 0.2:
                insights.append(f"🛡️ **Crypto Decoupling ({c:.2f})**: BTC moving independently.")
        
        # SPY vs GOLD (Safe Haven)
        if 'GOLD' in spy_corr.index:
            c = spy_corr['GOLD']
            if c < -0.2:
                insights.append(f"✨ **Gold Hedge ({c:.2f})**: Gold as safe haven.")
            elif c > 0.4:
                insights.append(f"💸 **Monetary Debasement ({c:.2f})**: Gold/Stocks rising together.")
        
        # SPY vs VIX
        if 'VIX' in spy_corr.index:
            c = spy_corr['VIX']
            if c > -0.3:
                insights.append(f"💀 **Fragility ({c:.2f})**: VIX correlation broken (should be <-0.6).")
        
        return insights
    
    def _render_asset_correlation(self, corr_matrix: pd.DataFrame, valid_assets: list) -> None:
        """Render asset class correlation bar chart."""
        if 'SPY' not in corr_matrix.columns:
            return
        
        spy_corr = corr_matrix['SPY'].drop('SPY').sort_values(ascending=False)
        colors = ['green' if x > 0 else 'red' for x in spy_corr.values]
        
        fig = go.Figure(go.Bar(
            x=spy_corr.index.tolist(),
            y=spy_corr.values,
            marker_color=colors,
            text=[f"{v:.2f}" for v in spy_corr.values],
            textposition='auto'
        ))
        fig.update_layout(
            title="Correlation with SPY (Risk On vs Hedge)",
            yaxis_title="Correlation Coefficient",
            template="plotly_dark",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info("ℹ️ **VIX** should be deeply negative (-0.7). If above -0.3, signals **Market Fragility**.")
    
    def _render_global_relative_strength(self) -> None:
        """Render global relative strength (1M returns)."""
        rs_data = {}
        for ticker, name in self.GLOBAL_MARKETS.items():
            if ticker in self.df.columns:
                col = f"{ticker}_Adj" if f"{ticker}_Adj" in self.df.columns else ticker
                series = self.df[col].dropna()
                if len(series) > 21:
                    ret = series.pct_change(21).iloc[-1] * 100
                    rs_data[name] = ret
        
        if not rs_data:
            st.warning("No global market data available.")
            return
        
        sorted_rs = dict(sorted(rs_data.items(), key=lambda x: x[1], reverse=True))
        colors = ['green' if v > 0 else 'red' for v in sorted_rs.values()]
        
        fig = go.Figure(go.Bar(
            x=list(sorted_rs.keys()),
            y=list(sorted_rs.values()),
            marker_color=colors,
            text=[f"{v:.1f}%" for v in sorted_rs.values()],
            textposition='auto'
        ))
        fig.update_layout(
            title="Global Relative Strength (1-Month Return)",
            yaxis_title="Return (%)",
            template="plotly_dark",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Insight
        if sorted_rs:
            leader = list(sorted_rs.keys())[0]
            laggard = list(sorted_rs.keys())[-1]
            st.info(f"ℹ️ **Capital rotating into {leader}**. Avoid **{laggard}** until momentum stabilizes.")
    
    def _render_global_spy_correlation(self) -> None:
        """Render global markets correlation with SPY."""
        if 'SPY' not in self.df.columns:
            st.warning("SPY data not available.")
            return
        
        spy_col = "SPY_Adj" if "SPY_Adj" in self.df.columns else "SPY"
        spy_ret = self.df[spy_col].pct_change().tail(90)
        
        g_corr_data = {}
        for ticker, name in self.GLOBAL_MARKETS.items():
            if ticker in self.df.columns:
                col = f"{ticker}_Adj" if f"{ticker}_Adj" in self.df.columns else ticker
                series_ret = self.df[col].pct_change().tail(90)
                if not series_ret.empty:
                    g_corr_data[name] = spy_ret.corr(series_ret)
        
        if not g_corr_data:
            st.warning("No global correlation data available.")
            return
        
        sorted_g_corr = dict(sorted(g_corr_data.items(), key=lambda x: x[1], reverse=True))
        
        fig = go.Figure(go.Bar(
            x=list(sorted_g_corr.keys()),
            y=list(sorted_g_corr.values()),
            marker_color='#1E88E5',
            text=[f"{v:.2f}" for v in sorted_g_corr.values()],
            textposition='auto'
        ))
        fig.update_layout(
            title="Global Correlation with SPY (90-Day)",
            yaxis_title="Correlation",
            template="plotly_dark",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Insight
        low_corr = [k for k, v in sorted_g_corr.items() if v < 0.5]
        high_corr = [k for k, v in sorted_g_corr.items() if v > 0.8]
        
        summary = ""
        if high_corr:
            summary += f"**Global Sync**: {', '.join(high_corr[:3])} moving with US. "
        if low_corr:
            summary += f"**Diversify**: Consider {', '.join(low_corr[:3])} for lower correlation."
        
        if summary:
            st.info(f"💡 {summary}")
    
    def render_dual_beta_dashboard(self, valid_assets: list) -> None:
        """Render Dual-Beta & Asymmetric Risk Dashboard."""
        st.subheader("⚖️ Dual-Beta & Asymmetric Risk Dashboard")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            target_asset = st.selectbox(
                "Target Asset", 
                valid_assets, 
                index=valid_assets.index('BTC') if 'BTC' in valid_assets else 0,
                key="dual_beta_target"
            )
        
        with col2:
            benchmark_asset = st.selectbox(
                "Benchmark", 
                valid_assets, 
                index=valid_assets.index('SPY') if 'SPY' in valid_assets else 0,
                key="dual_beta_bench"
            )
        
        if target_asset == benchmark_asset:
            st.info("Target and Benchmark are the same.")
            return
        
        # Get data
        t_col = f"{target_asset}_Adj" if f"{target_asset}_Adj" in self.df.columns else target_asset
        b_col = f"{benchmark_asset}_Adj" if f"{benchmark_asset}_Adj" in self.df.columns else benchmark_asset
        
        t_data = self.df[t_col]
        b_data = self.df[b_col]
        
        risk_metrics = self.risk_analyzer.calculate_asymmetric_risk(t_data, b_data, window=252)
        
        if risk_metrics and risk_metrics.get('valid'):
            b_plus = risk_metrics['beta_plus']
            b_minus = risk_metrics['beta_minus']
            up_cap = risk_metrics.get('up_capture', 0)
            down_cap = risk_metrics.get('down_capture', 0)
            corr = risk_metrics.get('corr', 0)
            
            # Determine status
            status_label, status_color, summary_text = "NEUTRAL", "gray", "Standard systematic risk."
            
            if b_minus > 1.2:
                status_label, status_color = "⚠️ HIGH RISK", "#FF5252"
                summary_text = f"**Tail Risk**: Falls harder than market during crashes (β- {b_minus:.2f})."
            elif b_plus > b_minus and b_minus < 1.0:
                status_label, status_color = "✅ EFFICIENT", "#00E676"
                summary_text = f"**Alpha Generator**: Captures upside (β+ {b_plus:.2f}), resists downside (β- {b_minus:.2f})."
            
            # Display metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Correlation", f"{corr:.2f}")
            c2.metric("Beta+ (Up)", f"{b_plus:.2f}")
            c3.metric("Beta- (Down)", f"{b_minus:.2f}")
            
            with c4:
                st.markdown(f"""
                <div style="text-align: center; padding: 5px; border: 1px solid {status_color}; border-radius: 5px;">
                    <span style="color: {status_color}; font-weight: bold;">{status_label}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.info(f"📝 **Summary**: {summary_text}")
            
            # Capture ratio chart
            fig_cap = go.Figure()
            fig_cap.add_trace(go.Bar(
                y=['Up Capture', 'Down Capture'],
                x=[up_cap, down_cap],
                orientation='h',
                marker_color=['#00E676', '#FF5252'],
                text=[f"{up_cap:.1f}%", f"{down_cap:.1f}%"],
                textposition='auto'
            ))
            fig_cap.add_vline(x=100, line_dash="dash", line_color="gray")
            fig_cap.update_layout(
                title="Upside vs Downside Capture Ratio",
                height=180,
                template="plotly_dark",
                xaxis_title="Capture % (Benchmark = 100%)",
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_cap, use_container_width=True)
            
            # Methodology expander
            with st.expander("📚 Dual-Beta Methodology"):
                st.markdown("""
                **✅ Efficient (Positive Convexity)**: β+ > β- AND β- < 1.0 → Participates in rallies, resists crashes.
                
                **⚠️ High Risk (Negative Convexity)**: β- > 1.2 → Crashes harder than market.
                
                **Math**: Log returns, 252-day window, regimes split by benchmark sign.
                """)
        elif risk_metrics:
            st.warning(f"⚠️ {risk_metrics.get('msg', 'Insufficient data')}")
        else:
            st.error("Insufficient data for risk analysis.")
    
    # ==================== Deep Dive ====================
    
    def render_deep_dive_chart(self, df_ticker: pd.DataFrame, ticker_name: str, info: Dict = None) -> None:
        """Render deep dive analysis for a single ticker."""
        if df_ticker.empty or 'Close' not in df_ticker.columns:
            st.error("No valid data found.")
            return
        
        series = df_ticker['Close']
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        
        # Fundamental snapshot
        if info:
            self._render_fundamental_snapshot(info, ticker_name)
            st.divider()
        
        # Price chart with indicators
        self._render_price_chart(series, ticker_name)
        
        # Historical Move Significance
        st.divider()
        self._render_historical_significance(series)
        
        # Technical analysis
        st.divider()
        self._render_technical_analysis(series, df_ticker)
        
        # Risk metrics
        st.divider()
        self._render_risk_metrics(series)
    
    def _render_historical_significance(self, series: pd.Series) -> None:
        """Render historical move significance analysis."""
        st.subheader("📉 Historical Move Significance")
        
        ret, rank_signed, rank_abs = self.tech_analyzer.calculate_percentile_rank(series)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"Today's Move: **{ret*100:.2f}%**")
            st.write(f"Larger than **{rank_abs:.1f}%** of all daily moves.")
            if rank_abs > 95:
                st.error("🔥 EXTREME VOLATILITY")
        
        with col2:
            returns = series.pct_change().dropna()
            if not returns.empty:
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(x=returns, nbinsx=100, name='History', marker_color='gray', opacity=0.5))
                fig_hist.add_vline(x=ret, line_width=3, line_dash="dash", line_color="red", annotation_text="Today")
                fig_hist.update_layout(
                    title="Return Distribution",
                    showlegend=False, height=250,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(tickformat='.1%')
                )
                st.plotly_chart(fig_hist, use_container_width=True)
    
    def _render_fundamental_snapshot(self, info: Dict, ticker: str) -> None:
        """Render fundamental data snapshot."""
        st.subheader("📊 Fundamental Snapshot")
        
        cols = st.columns(5)
        
        eps_curr = info.get('epsCurrentYear')
        fwd_eps = info.get('forwardEps')
        fwd_pe = info.get('forwardPE')
        peg = info.get('pegRatio')
        
        with cols[0]:
            st.metric("EPS (Current)", f"${eps_curr:.2f}" if eps_curr else "N/A")
        with cols[1]:
            st.metric("Forward EPS", f"${fwd_eps:.2f}" if fwd_eps else "N/A")
        with cols[2]:
            st.metric("Forward PE", f"{fwd_pe:.2f}" if fwd_pe else "N/A")
        with cols[3]:
            st.metric("PEG Ratio", f"{peg:.2f}" if peg else "N/A")
    
    def _render_price_chart(self, series: pd.Series, ticker: str) -> None:
        """Render price chart with moving averages and Bollinger Bands."""
        sma50 = self.tech_analyzer.calculate_sma(series, 50)
        sma200 = self.tech_analyzer.calculate_sma(series, 200)
        upper, lower = self.tech_analyzer.calculate_bollinger_bands(series)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series.index, y=series, name='Price', line=dict(color='white')))
        fig.add_trace(go.Scatter(x=sma50.index, y=sma50, name='SMA 50', line=dict(color='cyan', width=1)))
        fig.add_trace(go.Scatter(x=sma200.index, y=sma200, name='SMA 200', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=upper.index, y=upper, name='BB Upper', line=dict(color='gray', width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=lower.index, y=lower, name='BB Lower', line=dict(color='gray', width=0), fill='tonexty', fillcolor='rgba(255,255,255,0.05)', showlegend=False))
        
        fig.update_layout(title=f"{ticker} Price Action", height=500, template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_technical_analysis(self, series: pd.Series, df_ticker: pd.DataFrame) -> None:
        """Render technical indicators with MACD histogram."""
        st.subheader("🛠️ Technical Analysis")
        
        rsi = self.tech_analyzer.calculate_rsi(series)
        macd, signal = self.tech_analyzer.calculate_macd(series)
        histogram = macd - signal
        
        cols = st.columns(4)
        cols[0].metric("RSI (14)", f"{rsi.iloc[-1]:.2f}" if not rsi.empty else "N/A")
        cols[1].metric("MACD", f"{macd.iloc[-1]:.2f}" if not macd.empty else "N/A")
        
        # Charts
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.5])
        
        # RSI
        fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name='RSI', line=dict(color='purple')), row=1, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=1, col=1)
        
        # MACD with histogram
        fig.add_trace(go.Scatter(x=macd.index, y=macd, name='MACD', line=dict(color='blue')), row=2, col=1)
        fig.add_trace(go.Scatter(x=signal.index, y=signal, name='Signal', line=dict(color='orange')), row=2, col=1)
        fig.add_trace(go.Bar(x=histogram.index, y=histogram, name='Histogram', marker_color='gray'), row=2, col=1)
        
        fig.update_layout(height=400, template="plotly_dark", title="Momentum Indicators")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("ℹ️ **RSI**: >70 = Overbought, <30 = Oversold. | **MACD**: Crossover = Buy/Sell Signal.")
    
    def _render_risk_metrics(self, series: pd.Series) -> None:
        """Render risk metrics."""
        st.subheader("🛡️ Risk Metrics")
        
        sharpe = self.risk_analyzer.calculate_sharpe_ratio(series)
        sortino = self.risk_analyzer.calculate_sortino_ratio(series)
        mdd = self.risk_analyzer.calculate_max_drawdown(series.tail(252))
        var, skew_val, kurt_val, _ = self.risk_analyzer.calculate_cornish_fisher_var(series)
        
        cols = st.columns(4)
        cols[0].metric("Sharpe (1Y)", f"{sharpe:.2f}")
        cols[1].metric("Sortino (1Y)", f"{sortino:.2f}")
        cols[2].metric("Max Drawdown", f"{mdd*100:.2f}%")
        cols[3].metric("VaR (95%)", f"-{var*100:.2f}%")
        
        st.caption(f"Skewness: {skew_val:.2f} | Kurtosis: {kurt_val:.2f}")
        
        # Seasonality
        st.markdown("**📅 Seasonality (10Y)**")
        SeasonalityHeatmap.render(series)
