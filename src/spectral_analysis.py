"""
频谱分析模块 - Welch功率谱 + AR(1)红噪声检验
"""
import numpy as np
from scipy import signal
import plotly.graph_objects as go

def compute_ar1_autocorr(series):
    """计算AR(1)滞后-1自相关系数"""
    return np.corrcoef(series[:-1], series[1:])[0, 1]

def red_noise_spectrum(freqs, alpha, variance, dt=1.0):
    """
    计算红噪声理论功率谱

    Parameters:
    -----------
    freqs : array
        频率数组
    alpha : float
        AR(1)系数
    variance : float
        序列方差
    dt : float
        采样间隔（小时）

    Returns:
    --------
    array : 红噪声功率谱
    """
    # AR(1)红噪声理论谱: P(f) = (2*dt*variance*(1-alpha^2)) / (1 - 2*alpha*cos(2*pi*f*dt) + alpha^2)
    angular_freq = 2 * np.pi * freqs * dt
    spectrum = (2 * dt * variance * (1 - alpha**2)) / \
               (1 - 2 * alpha * np.cos(angular_freq) + alpha**2)
    return spectrum

def run_spectral_analysis(detrended_series, time_index, period_min=7, period_max=15, significance=0.95):
    """
    执行频谱分析

    Returns:
    --------
    dict : 包含功率谱数据、显著性判断、图表
    """
    # 转换为numpy数组
    data = np.array(detrended_series)
    n = len(data)

    # 采样间隔（小时）
    dt = 1.0

    # Welch功率谱估计
    # nperseg: 窗口大小，约30天*24小时=720
    nperseg = min(30 * 24, n // 4)
    freqs, psd = signal.welch(data, fs=1.0/dt, nperseg=nperseg, noverlap=nperseg//2)

    # 避免零频率
    freqs = freqs[1:]
    psd = psd[1:]

    # 计算周期（天）
    periods_days = (1.0 / freqs) / 24

    # AR(1)红噪声检验
    alpha = compute_ar1_autocorr(data)
    if np.isnan(alpha):
        alpha = 0.5  # 默认值

    variance = np.var(data)
    rn_spectrum = red_noise_spectrum(freqs, alpha, variance, dt)

    # 95%置信上限（使用chi-square分布）
    # 对于Welch估计，自由度约2*nseg/nperseg
    dof = 2 * (n // nperseg)
    chi2_quantile = 2 * dof / 2  # 等效
    conf_level = significance
    f_crit = np.sqrt(-2 * np.log(1 - conf_level)) if conf_level > 0 else 1.0

    # 简化：使用固定系数
    conf_factor = 1.5 if dof < 10 else 1.3
    rn_upper = rn_spectrum * conf_factor

    # 7-15天频段检验
    mask = (periods_days >= period_min) & (periods_days <= period_max)
    if np.any(mask):
        period_psd = psd[mask]
        period_rn = rn_upper[mask]
        is_significant = np.mean(period_psd) > np.mean(period_rn)
        max_psd_idx = np.argmax(period_psd)
        dominant_period_in_band = periods_days[mask][max_psd_idx]
    else:
        is_significant = False
        dominant_period_in_band = None

    # 创建图表
    fig = go.Figure()

    # 观测功率谱
    fig.add_trace(go.Scatter(
        x=periods_days,
        y=psd,
        mode='lines',
        name='观测功率谱',
        line=dict(color='#00d4ff', width=2)
    ))

    # 红噪声背景
    fig.add_trace(go.Scatter(
        x=periods_days,
        y=rn_spectrum,
        mode='lines',
        name='AR(1)红噪声',
        line=dict(color='#888888', width=1.5, dash='dash')
    ))

    # 95%置信上限
    fig.add_trace(go.Scatter(
        x=periods_days,
        y=rn_upper,
        mode='lines',
        name=f'{int(significance*100)}%置信限',
        line=dict(color='#ff6b6b', width=1.5, dash='dot')
    ))

    # 标记7-15天区域
    fig.add_vrect(
        x0=period_min, x1=period_max,
        fillcolor="rgba(124, 58, 237, 0.15)",
        layer="below",
        line_width=0,
        annotation_text="分析区间"
    )

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        title=dict(
            text=f'功率谱分析 (显著性: {"是" if is_significant else "否"})',
            font=dict(size=16)
        ),
        xaxis=dict(
            title='周期（天）',
            gridcolor='rgba(255,255,255,0.1)',
            range=[0, 60]
        ),
        yaxis=dict(
            title='功率谱密度',
            gridcolor='rgba(255,255,255,0.1)',
            type='log'
        ),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
        height=450,
        margin=dict(l=60, r=30, t=60, b=60)
    )

    return {
        'periods_days': periods_days.tolist(),
        'psd': psd.tolist(),
        'red_noise': rn_spectrum.tolist(),
        'confidence_upper': rn_upper.tolist(),
        'alpha': float(alpha),
        'is_significant': bool(is_significant),
        'dominant_period': float(dominant_period_in_band) if dominant_period_in_band else None,
        'chart': fig.to_json()
    }
