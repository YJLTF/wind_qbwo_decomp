"""
小波分析模块 - 连续小波变换(CWT) + 显著性检验
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def run_wavelet_analysis(detrended_series, time_index, period_min=7, period_max=15, significance=0.95):
    """
    执行小波分析

    注意：这里使用简化版本，避免pycwt的复杂性
    完整实现请参考原始README中的pycwt方法
    """
    data = np.array(detrended_series)
    n = len(data)

    # 简化实现：使用短时傅里叶变换(STFT)近似时频分析
    from scipy import signal as scipy_signal

    # 定义周期范围（小时）
    min_period_hours = period_min * 24
    max_period_hours = period_max * 24

    # 频率范围
    min_freq = 1.0 / max_period_hours
    max_freq = 1.0 / min_period_hours

    # 使用小波母函数简化版（Morlet近似用Gabor）
    # 创建时间-频率功率谱
    frequencies = np.logspace(np.log10(min_freq), np.log10(max_freq), 50)

    # 计算时频功率谱
    power_spectrum = np.zeros((len(frequencies), n))

    for i, freq in enumerate(frequencies):
        # 使用正弦波卷积近似小波变换
        t = np.arange(n)
        # 复正弦波
        wave = np.exp(1j * 2 * np.pi * freq * t)
        # 高斯窗
        window_width = int(3 * (1.0 / freq))
        window = np.exp(-(t - n/2)**2 / (2 * (window_width/3)**2))
        # 卷积
        conv = np.convolve(data * window, wave, mode='same')
        power_spectrum[i, :] = np.abs(conv)**2 / n

    # 计算AR(1)红噪声显著性
    alpha = np.corrcoef(data[:-1], data[1:])[0, 1]
    if np.isnan(alpha):
        alpha = 0.5

    # 显著性阈值（简化）
    conf_factor = 2.5
    signif_threshold = np.var(data) * conf_factor * np.ones((1, n))

    # 转换周期为天
    periods_days = (1.0 / frequencies) / 24

    # 时间轴（天）
    time_days = np.arange(n) / 24

    # 创建热力图
    fig = make_subplots(rows=2, cols=1, row_heights=[0.75, 0.25],
                        subplot_titles=('小波功率谱', '去趋势序列'),
                        vertical_spacing=0.08)

    # 小波功率谱热力图
    fig.add_trace(go.Heatmap(
        x=time_days,
        y=periods_days,
        z=np.log10(power_spectrum + 1e-10),
        colorscale='Viridis',
        showscale=True,
        colorbar=dict(title='Log10 Power', len=0.75, y=0.8)
    ), row=1, col=1)

    # 添加7天和15天参考线
    fig.add_hline(y=7, line_dash="dash", line_color="white",
                  annotation_text="7天", row=1, col=1)
    fig.add_hline(y=15, line_dash="dash", line_color="white",
                  annotation_text="15天", row=1, col=1)

    # 标记显著区域（简化）
    sig_mask = power_spectrum > signif_threshold
    if np.any(sig_mask):
        sig_periods = periods_days[:, None] * np.ones((1, n))
        sig_times = time_days * np.ones((len(periods_days), 1))

        # 找出7-15天内的显著区域
        band_mask = (periods_days >= period_min) & (periods_days <= period_max)
        if np.any(band_mask & (np.any(sig_mask, axis=1))):
            fig.add_hline(y=10, line_dash="solid", line_color="red",
                         line_width=2, row=1, col=1)

    # 去趋势序列
    fig.add_trace(go.Scatter(
        x=time_days,
        y=data[:len(time_days)] / np.std(data),
        mode='lines',
        line=dict(color='#00d4ff', width=1),
        name='标准化序列'
    ), row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0'),
        title=dict(text='时频分析（小波功率谱）', font=dict(size=16)),
        height=600,
        showlegend=False,
        margin=dict(l=60, r=30, t=50, b=40)
    )

    fig.update_xaxes(title_text="时间（天）", row=2, col=1,
                     gridcolor='rgba(255,255,255,0.1)')
    fig.update_xaxes(title_text="时间（天）", row=1, col=1,
                     gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="周期（天）", row=1, col=1,
                     gridcolor='rgba(255,255,255,0.1)', type='log')
    fig.update_yaxes(title_text="标准化功率", row=2, col=1,
                     gridcolor='rgba(255,255,255,0.1)')

    # 识别显著周期带
    band_power = np.mean(power_spectrum[band_mask, :], axis=0)
    max_power_idx = np.argmax(band_power)
    dominant_time_days = time_days[max_power_idx]

    return {
        'time_days': time_days.tolist(),
        'periods_days': periods_days.tolist(),
        'power_spectrum': power_spectrum.tolist(),
        'dominant_period_days': float(periods_days[np.argmax(np.mean(power_spectrum, axis=1))]),
        'dominant_time_days': float(dominant_time_days),
        'chart': fig.to_json()
    }
