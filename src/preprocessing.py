"""
预处理模块 - 数据重采样、缺失值处理、去趋势
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def preprocess_data(df, time_col, power_col, detrend_window=30):
    """
    数据预处理

    Parameters:
    -----------
    df : DataFrame
        原始数据
    time_col : str
        时间列名
    power_col : str
        功率列名
    detrend_window : int
        去趋势滑动窗口天数

    Returns:
    --------
    dict : 包含去趋势序列、时间索引、图表等
    """
    # 复制数据
    data = df.copy()
    data.set_index(time_col, inplace=True)

    # 重采样至1小时
    if len(data) > 30000:  # 15min数据
        data = data.resample('1H').mean()

    # 线性插值填补少量缺失
    original_missing = data[power_col].isna().sum()
    data[power_col] = data[power_col].interpolate(method='linear')

    # 原始序列
    original_series = data[power_col].values
    time_index = data.index

    # 去趋势：30天滑动平均
    window_hours = detrend_window * 24
    trend = data[power_col].rolling(window=window_hours, center=True, min_periods=1).mean()
    detrended = data[power_col] - trend
    detrended_series = detrended.values

    # 生成原始数据图表
    fig_original = go.Figure()
    fig_original.add_trace(go.Scatter(
        x=time_index,
        y=original_series,
        mode='lines',
        name='原始功率',
        line=dict(color='#00d4ff', width=1)
    ))
    fig_original.add_trace(go.Scatter(
        x=time_index,
        y=trend,
        mode='lines',
        name=f'{detrend_window}天趋势',
        line=dict(color='#ff6b6b', width=2)
    ))
    fig_original.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        title=dict(text='原始风电功率与趋势线', font=dict(size=16)),
        xaxis=dict(title='时间', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='功率', gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
        height=400,
        margin=dict(l=60, r=30, t=50, b=60)
    )
    original_chart = fig_original.to_json()

    # 生成去趋势序列图表
    fig_detrended = go.Figure()
    fig_detrended.add_trace(go.Scatter(
        x=time_index,
        y=detrended_series,
        mode='lines',
        name='去趋势序列',
        line=dict(color='#7c3aed', width=1)
    ))
    fig_detrended.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        title=dict(text='去趋势后序列（天气尺度波动）', font=dict(size=16)),
        xaxis=dict(title='时间', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='功率偏差', gridcolor='rgba(255,255,255,0.1)'),
        height=400,
        margin=dict(l=60, r=30, t=50, b=60)
    )
    detrended_chart = fig_detrended.to_json()

    return {
        'original_series': original_series,
        'detrended_series': detrended_series,
        'time_index': time_index,
        'trend': trend.values,
        'original_missing': original_missing,
        'original_chart': original_chart,
        'detrended_chart': detrended_chart
    }
