"""
Trader Dashboard V5 - Reusable UI Components
=============================================
Common chart and display components used across pages.
"""

import calendar
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..config import config, user_settings
from ..analytics.technical import TechnicalAnalyzer

logger = logging.getLogger(__name__)


class ChartComponents:
    """
    Reusable chart components for the dashboard.
    
    Provides consistent styling and behavior across all charts.
    """
    
    # Default chart configuration
    DEFAULT_TEMPLATE = "plotly_dark"
    DEFAULT_HEIGHT = 400
    DEFAULT_HEIGHT_LARGE = 600
    DEFAULT_MARGIN = dict(l=20, r=20, t=50, b=40)
    
    @classmethod
    def create_time_series_chart(
        cls,
        series_list: List[Tuple[pd.Series, str, str]],
        title: str,
        height: int = None,
        y_title: str = None,
        hlines: List[Dict] = None,
        fill_area: bool = False
    ) -> go.Figure:
        """
        Create a time series chart with multiple series.
        
        Args:
            series_list: List of (series, name, color) tuples
            title: Chart title
            height: Chart height
            y_title: Y-axis title
            hlines: List of horizontal line configs
            fill_area: Whether to fill area under first series
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        for i, (series, name, color) in enumerate(series_list):
            if series.empty:
                continue
            
            trace_kwargs = dict(
                x=series.index,
                y=series,
                name=name,
                line=dict(color=color, width=1.5)
            )
            
            if fill_area and i == 0:
                trace_kwargs['fill'] = 'tozeroy'
            
            fig.add_trace(go.Scatter(**trace_kwargs))
        
        # Add horizontal lines
        if hlines:
            for hline in hlines:
                fig.add_hline(
                    y=hline['y'],
                    line_dash=hline.get('dash', 'dash'),
                    line_color=hline.get('color', 'gray'),
                    annotation_text=hline.get('text', '')
                )
        
        fig.update_layout(
            title=dict(text=title, y=0.95),
            height=height or cls.DEFAULT_HEIGHT,
            template=cls.DEFAULT_TEMPLATE,
            hovermode="x unified",
            margin=cls.DEFAULT_MARGIN,
            xaxis=dict(showgrid=False),
            yaxis=dict(
                title=y_title,
                autorange=True,
                fixedrange=False
            )
        )
        
        return fig
    
    @classmethod
    def create_subplot_chart(
        cls,
        chart_configs: List[Dict],
        df: pd.DataFrame,
        title: str,
        height: int = None
    ) -> go.Figure:
        """
        Create synchronized subplots.
        
        Args:
            chart_configs: List of {'col': column, 'name': display_name, 'color': color}
            df: DataFrame with data
            title: Chart title
            height: Total height
            
        Returns:
            Plotly Figure
        """
        valid_configs = [c for c in chart_configs if c['col'] in df.columns]
        
        if not valid_configs:
            return cls._create_empty_chart("No data available")
        
        fig = make_subplots(
            rows=len(valid_configs),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[c['name'] for c in valid_configs]
        )
        
        for i, cfg in enumerate(valid_configs):
            series = df[cfg['col']].dropna()
            if series.empty:
                continue
            
            fig.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series,
                    name=cfg['name'],
                    line=dict(color=cfg['color'], width=1.5)
                ),
                row=i + 1,
                col=1
            )
            
            # Add horizontal lines if specified
            if 'hlines' in cfg:
                for hline in cfg['hlines']:
                    fig.add_hline(
                        y=hline['val'],
                        line_dash="dash",
                        line_color=hline['color'],
                        annotation_text=hline.get('text', ''),
                        row=i + 1,
                        col=1
                    )
        
        fig.update_layout(
            title=dict(text=title, y=0.98),
            height=height or cls.DEFAULT_HEIGHT_LARGE,
            template=cls.DEFAULT_TEMPLATE,
            margin=cls.DEFAULT_MARGIN,
            hovermode="x unified",
            xaxis=dict(showgrid=False),
            yaxis=dict(autorange=True, fixedrange=False)
        )
        
        return fig
    
    @classmethod
    def create_bar_chart(
        cls,
        data: Dict[str, float],
        title: str,
        color_positive: str = 'green',
        color_negative: str = 'red',
        height: int = None,
        orientation: str = 'v'
    ) -> go.Figure:
        """
        Create a bar chart with automatic positive/negative coloring.
        
        Args:
            data: Dictionary of {label: value}
            title: Chart title
            color_positive: Color for positive values
            color_negative: Color for negative values
            height: Chart height
            orientation: 'v' for vertical, 'h' for horizontal
            
        Returns:
            Plotly Figure
        """
        sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
        colors = [color_positive if v > 0 else color_negative for v in sorted_data.values()]
        
        if orientation == 'h':
            fig = go.Figure(go.Bar(
                y=list(sorted_data.keys()),
                x=list(sorted_data.values()),
                orientation='h',
                marker_color=colors,
                text=[f"{v:.1f}%" if isinstance(v, float) else str(v) for v in sorted_data.values()],
                textposition='auto'
            ))
        else:
            fig = go.Figure(go.Bar(
                x=list(sorted_data.keys()),
                y=list(sorted_data.values()),
                marker_color=colors,
                text=[f"{v:.1f}%" if isinstance(v, float) else str(v) for v in sorted_data.values()],
                textposition='auto'
            ))
        
        fig.update_layout(
            title=title,
            height=height or 350,
            template=cls.DEFAULT_TEMPLATE
        )
        
        return fig
    
    @classmethod
    def create_gauge_chart(
        cls,
        value: float,
        title: str,
        min_val: float = 0,
        max_val: float = 100,
        thresholds: List[Dict] = None
    ) -> go.Figure:
        """
        Create a gauge (speedometer) chart.
        
        Args:
            value: Current value
            title: Display title
            min_val: Minimum value
            max_val: Maximum value
            thresholds: List of {'range': [low, high], 'color': color}
            
        Returns:
            Plotly Figure
        """
        default_thresholds = [
            {'range': [0, 25], 'color': "darkred"},
            {'range': [25, 50], 'color': "orangered"},
            {'range': [50, 75], 'color': "green"},
            {'range': [75, 100], 'color': "darkgreen"}
        ]
        
        steps = thresholds or default_thresholds
        
        # Determine bar color based on value
        bar_color = "gray"
        for step in steps:
            if step['range'][0] <= value <= step['range'][1]:
                bar_color = step['color']
                break
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            title={'text': title},
            gauge={
                'axis': {'range': [min_val, max_val]},
                'bar': {'color': bar_color},
                'steps': steps
            }
        ))
        
        fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        
        return fig
    
    @classmethod
    def create_heatmap(
        cls,
        data: pd.DataFrame,
        title: str,
        colorscale: str = 'RdBu',
        height: int = None
    ) -> go.Figure:
        """
        Create a heatmap chart.
        
        Args:
            data: DataFrame with values
            title: Chart title
            colorscale: Plotly colorscale name
            height: Chart height
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure(data=go.Heatmap(
            z=data.values,
            x=data.columns.tolist(),
            y=data.index.tolist(),
            colorscale=colorscale,
            zmin=-1 if colorscale == 'RdBu' else None,
            zmax=1 if colorscale == 'RdBu' else None
        ))
        
        fig.update_layout(
            title=title,
            height=height or cls.DEFAULT_HEIGHT_LARGE,
            template=cls.DEFAULT_TEMPLATE
        )
        
        return fig
    
    @classmethod
    def _create_empty_chart(cls, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            height=200,
            template=cls.DEFAULT_TEMPLATE
        )
        return fig


class KPIComponents:
    """
    KPI card and indicator display components.
    """
    
    @staticmethod
    def render_metric_card(
        label: str,
        value: Any,
        delta: Optional[str] = None,
        z_score: Optional[float] = None,
        percentile: Optional[float] = None,
        status: Optional[Tuple[str, str]] = None
    ) -> None:
        """
        Render a metric card with optional z-score and percentile.
        
        Args:
            label: Metric label
            value: Display value
            delta: Delta value (e.g., "+2.5%")
            z_score: Z-score value
            percentile: Percentile rank
            status: Tuple of (status_text, color)
        """
        st.metric(label=label, value=value, delta=delta)
        
        extra_html = ""
        
        if z_score is not None:
            z_color = "orange" if abs(z_score) > 2 else "gray"
            extra_html += f"Z-Score: <span style='color:{z_color}'><b>{z_score:.2f}</b></span><br>"
        
        if percentile is not None:
            extra_html += f"PR (1Y): <b>{percentile:.0f}%</b><br>"
        
        if status is not None:
            status_text, status_color = status
            extra_html += f"<span style='color:{status_color}'><b>{status_text}</b></span>"
        
        if extra_html:
            st.markdown(
                f"<div style='font-size: 0.8em; color: gray;'>{extra_html}</div>",
                unsafe_allow_html=True
            )
    
    @staticmethod
    def render_status_indicator(
        label: str,
        value: float,
        thresholds: List[Tuple[float, str, str]],
        format_str: str = "{:.2f}",
        sub_text: Optional[str] = None
    ) -> None:
        """
        Render a status indicator with color-coded value.
        
        Args:
            label: Indicator label
            value: Current value
            thresholds: List of (threshold, status_text, color) in descending order
            format_str: Format string for value display
            sub_text: Additional text below value
        """
        # Determine status based on thresholds
        status = "Normal"
        color = "green"
        
        for threshold, status_text, threshold_color in thresholds:
            if value >= threshold:
                status = status_text
                color = threshold_color
                break
        
        st.markdown(
            f"""
            <div style='text-align:center; font-size:0.8em; color:gray'>{label}</div>
            <div style='text-align:center; font-size:1.5em; color:{color}'><b>{format_str.format(value)}</b></div>
            <div style='text-align:center; font-size:0.8em; color:{color}'>{sub_text or status}</div>
            """,
            unsafe_allow_html=True
        )


class TimeControl:
    """
    Time range selector component with persistence.
    """
    
    OPTIONS = ["3M", "6M", "1Y", "3Y", "5Y", "Max"]
    
    @classmethod
    def render(cls, key: str, default: str = "5Y") -> datetime:
        """
        Render time range radio buttons and return start date.
        
        Args:
            key: Unique key for persistence
            default: Default selection
            
        Returns:
            Start datetime based on selection
        """
        # Load saved preference
        saved_val = user_settings.get_range_setting(key, default)
        if saved_val not in cls.OPTIONS:
            saved_val = default
        
        # Render radio buttons
        selection = st.radio(
            "Select Time Range",
            cls.OPTIONS,
            index=cls.OPTIONS.index(saved_val),
            horizontal=True,
            key=f"radio_{key}",
            label_visibility="collapsed"
        )
        
        # Save if changed
        if selection != saved_val:
            user_settings.set_range_setting(key, selection)
        
        # Calculate start date
        return cls._selection_to_date(selection)
    
    @staticmethod
    def _selection_to_date(selection: str) -> datetime:
        """Convert selection string to start date."""
        now = datetime.now()
        
        mapping = {
            "3M": timedelta(days=90),
            "6M": timedelta(days=180),
            "1Y": timedelta(days=365),
            "3Y": timedelta(days=365 * 3),
            "5Y": timedelta(days=365 * 5),
            "Max": None
        }
        
        delta = mapping.get(selection)
        if delta is None:
            return datetime(2000, 1, 1)
        
        return now - delta


class SeasonalityHeatmap:
    """
    Seasonality analysis heatmap component.
    """
    
    @staticmethod
    def render(series: pd.Series, container=None) -> None:
        """
        Render a seasonality heatmap showing average monthly returns.
        
        Args:
            series: Price series
            container: Streamlit container (optional)
        """
        target = container or st
        
        if series.empty:
            target.warning("No data for seasonality analysis")
            return
        
        # Prepare data
        df = series.to_frame(name='Close')
        df['Year'] = df.index.year
        df['Month'] = df.index.month
        df['Return'] = df['Close'].pct_change()
        
        # Monthly returns pivot
        monthly_ret = df.groupby(['Year', 'Month'])['Return'].sum().unstack() * 100
        avg_monthly = monthly_ret.mean()
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=[avg_monthly.values],
            x=[calendar.month_abbr[i] for i in avg_monthly.index],
            y=['Avg Return'],
            colorscale='RdBu',
            zmid=0,
            text=[[f"{v:.1f}%" for v in avg_monthly.values]],
            texttemplate="%{text}"
        ))
        
        fig.update_layout(
            height=150,
            margin=dict(l=0, r=0, t=0, b=0),
            template="plotly_dark"
        )
        
        target.plotly_chart(fig, use_container_width=True)
        
        # Best/Worst months
        best_month = calendar.month_name[avg_monthly.idxmax()]
        worst_month = calendar.month_name[avg_monthly.idxmin()]
        target.caption(f"✅ Best: **{best_month}** | ❌ Worst: **{worst_month}**")
