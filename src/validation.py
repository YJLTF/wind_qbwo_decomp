"""
验证模块 - 带通滤波交叉验证
"""
import numpy as np
from scipy import signal
import plotly.graph_objects as go

def butterworth_bandpass(data, period_min, period_max, dt=1.0):
    """
    设计Butterworth带通滤波器

    Parameters:
    -----------
    data : array
        输入数据
    period_min : float
        最小周期（天）
    period_max : float
        最大周期（天）
    dt : float
        采样间隔（小时）

    Returns:
    --------
    array : 滤波后的数据
    """
    # 转换周期为频率
    high_freq = 1.0 / (period_max * 24)  # 最大周期的频率（低频）
    low_freq = 1.0 / (period_min * 24)   # 最小周期的频率（高频）

    # 奈奎斯特频率
    fs = 1.0 / dt
    nyq = fs / 2

    # 归一化频率
    low = high_freq / nyq
    high = min(low_freq / nyq, 0.99)  # 避免超过1

    # 设计滤波器
    order = 4
    b, a = signal.butter(order, [low, high], btype='band')

    # 应用滤波
    filtered = signal.filtfilt(b, a, data)

    return filtered

def run_validation(detrended_series, qbwo_component, period_min=7, period_max=15):
    """
    执行交叉验证：带通滤波与EEMD提取分量对比
    """
    data = np.array(detrended_series)
    qbwo = np.array(qbwo_component)

    # 带通滤波
    bp_filtered = butterworth_bandpass(data, period_min, period_max)

    # 计算相关系数
    if np.std(qbwo) > 0 and np.std(bp_filtered) > 0:
        correlation = np.corrcoef(qbwo, bp_filtered)[0, 1]
    else:
        correlation = 0

    # 计算波形重合度（简化）
    waveform_match = 1 - np.mean(np.abs(qbwo - bp_filtered) / (np.std(data) + 1e-10))

    # 创建对比图
    n = len(data)
    time_days = np.arange(n) / 24

    fig = make_subplots(rows=3, cols=1,
                        vertical_spacing=0.08,
                        subplot_titles=(
                            'EEMD提取的QBWO分量',
                            'Butterworth带通滤波结果',
                            '对比差异'
                        ))

    # EEMD分量
    fig.add_trace(go.Scatter(
        x=time_days,
        y=qbwo,
        mode='lines',
        line=dict(color='#00d4ff', width=1),
        name='EEMD QBWO'
    ), row=1, col=1)

    # 带通滤波
    fig.add_trace(go.Scatter(
        x=time_days,
        y=bp_filtered,
        mode='lines',
        line=dict(color='#f59e0b', width=1),
        name='带通滤波'
    ), row=2, col=1)

    # 差异
    diff = qbwo - bp_filtered
    fig.add_trace(go.Scatter(
        x=time_days,
        y=diff,
        mode='lines',
        line=dict(color='#ef4444', width=1),
        name='差异'
    ), row=3, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        title=dict(
            text=f'交叉验证结果 (相关系数: {correlation:.3f}, 波形重合度: {waveform_match:.1%})',
            font=dict(size=16)
        ),
        height=600,
        showlegend=False,
        margin=dict(l=60, r=30, t=50, b=40)
    )

    fig.update_xaxes(title_text="时间（天）", gridcolor='rgba(255,255,255,0.1)')
    for i in range(1, 4):
        fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)', row=i, col=1)

    return {
        'bandpass_filtered': bp_filtered.tolist(),
        'correlation': float(correlation),
        'waveform_match': float(waveform_match),
        'difference': diff.tolist(),
        'chart': fig.to_json()
    }
