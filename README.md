# 风电出力准双周振荡识别与分解

## 项目名称

- **中文名称**：风电出力准双周振荡识别与分解  
- **英文名称**：Identification and Decomposition of Quasi‑biweekly Oscillation in Wind Power Generation  
- **Python 工程名**：`wind_qbwo_decomp`

---

## 1. 项目概述

### 1.1 研究目标

对全年风电出力曲线（原始为 96 点/日 或 24 点/日）进行处理，从中识别并提取 **7–15 天** 时间尺度上的强周期成分（气象学中称为“准双周振荡”，Quasi‑biweekly Oscillation, QBWO）。要求分析方法具有统计显著性检验，能够适应周期强度随时间的变化，并最终输出可解释的周期分量。

### 1.2 适用数据

- 时间分辨率：15 分钟（96 点/日）或 1 小时（24 点/日）的风电功率时间序列  
- 时间跨度：至少 1 个完整年份（允许少量缺失，需预处理）  
- 格式：时间戳 + 功率值（如 CSV、Parquet）

### 1.3 技术路线概览

```mermaid
graph TD
    A[原始风电出力曲线] --> B[预处理：小时重采样 + 30天滑动去趋势]
    B --> C[全局频谱分析：Welch功率谱 + AR(1)红噪声检验]
    B --> D[时频分析：连续小波变换 CWT + 显著性检验]
    B --> E[自适应分解：EEMD 提取 7-15 天 IMF]
    C --> F[统计显著性结论]
    D --> G[时变周期特征图谱]
    E --> H[准双周振荡分量重构]
    F & G & H --> I[交叉验证：带通滤波对比]
```

---

## 2. 模块设计与实施步骤

### 2.1 数据预处理模块 preprocessing.py

目标：消除年尺度趋势，聚焦天气尺度波动，统一时间分辨率。

流程：

1. 重采样至 1 小时
      若原始数据为 15 min 分辨率，使用 pandas.resample('1h').mean() 降采样，全年约 8760 个点。
2. 缺失值处理
      线性插值填补少量缺失，若连续缺失超过 24 小时则标记，并在后续分析中考虑 COI 影响。
3. 年趋势估计与去除
      采用 30 天滑动平均（窗口大小 30*24，中心化）作为低频趋势，残差序列即为天气尺度波动（周期 < 30 天）。

```python
trend = df_1h['power'].rolling(window=30*24, center=True).mean()
detrended = df_1h['power'] - trend
```

产出：detrended_series.csv（去趋势后的 1 小时数据）

---

### 2.2 全局周期检验模块 spectral_analysis.py

目标：判断整个年份中 7–15 天频段是否存在 统计显著的平均谱峰。

方法：

· 功率谱估计：scipy.signal.welch，使用 nperseg=30*24*4 保证低频分辨率。
· 红噪声背景：
  1. 对去趋势序列拟合 AR(1) 模型，得到滞后-1 自相关系数 α；
  2. 计算对应红噪声的理论功率谱；
  3. 计算 95% 置信上限。
· 显著性判定：若 7–15 天周期区间的谱值超过红噪声 95% 上界，则认为存在全局强周期。

产出：

· 功率谱对比图（含红噪声背景与 95% 置信线）
· 显著性检查结论（是/否）

---

### 2.3 时频定位模块 wavelet_analysis.py

目标：揭示 7–15 天周期强度的 时间演变特征，定位“何时强、何时弱”。

工具：pycwt（连续小波变换，Morlet 母波）

步骤：

1. 使用 Morlet 小波（ω₀=6）计算小波功率谱。
2. 基于 AR(1) 红噪声进行逐尺度显著性检验（pycwt.significance）。
3. 绘制小波功率谱图，纵轴为周期（小时，对数尺度），横轴为时间，标注影响锥（COI）及 7 天、15 天参考线。
4. 在 7–15 天周期带内，识别 significance > 1 的时频区域，提取其时间区间和主导周期。

关键代码示例：

```python
import pycwt as wavelet
wave, scales, freqs, coi, fft, fftfreqs = wavelet.cwt(data, dt=1.0)
power = np.abs(wave) ** 2
alpha, _, _ = wavelet.ar1(data)
signif, _ = wavelet.significance(1.0, dt, scales, 0, alpha, significance_level=0.95)
sig95 = np.ones_like(power) * signif[:, None]
sig_mask = power / sig95 > 1   # 显著区域
```

产出：

· 小波功率谱图（PNG/SVG）
· 显著周期带时变记录表（CSV：起止时间、主导周期、最大功率）

---

### 2.4 自适应分解模块 eemd_decomp.py

目标：从序列中 直接提取 7–15 天振荡成分，计算其方差贡献。

工具：PyEMD 的 EEMD（集合经验模态分解）

流程：

1. 对去趋势序列执行 EEMD（试验次数 50，噪声标准差比例 0.1）。
2. 计算每个 IMF 的 平均周期（过零点法）和 方差占比。
3. 筛选平均周期落在 [7*24, 15*24] 小时内的 IMF。
4. 重构所选 IMF，得到准双周振荡分量。

```python
from PyEMD import EEMD
eemd = EEMD(trials=50, noise_width=0.1)
imfs = eemd(data)

for i, imf in enumerate(imfs):
    T = avg_period(imf) * 1   # 小时
    var_ratio = np.var(imf) / np.var(data)
    if 7*24 <= T <= 15*24:
        print(f"IMF {i}: period={T/24:.1f}d, variance={var_ratio:.2%}")
```

产出：

· IMF 分解图（含各分量周期与方差占比）
· 重构的 QBWO 分量时序数据（CSV）
· 方差贡献率统计表

---

### 2.5 结果验证与交叉比对模块 validation.py

目标：确保分解结果的物理一致性。

方法：

· 带通滤波验证：设计 7–15 天 Butterworth 带通滤波器，对去趋势序列滤波，与 EEMD 重构分量比较（相关系数、波形重合度）。
· 分段稳定性：按季节分段重复 EEMD 或 CWT，检查周期是否存在且稳定。

产出：验证对比图及相关系数报告。

---

## 3. 环境依赖

· Python 3.9+
· 核心库：
  · numpy, pandas, matplotlib
  · scipy（信号处理、统计）
  · pycwt（小波分析）
  · PyEMD（EEMD 分解）
  · statsmodels（可选，用于 AR 模型验证）

安装命令：

```bash
pip install numpy pandas matplotlib scipy pycwt EMD-signal statsmodels
```

---

## 4. 项目文件结构

```
wind_qbwo_decomp/
├── README.md                  # 本开发方案
├── data/
│   ├── raw/                   # 原始数据
│   └── processed/             # 预处理后数据
├── src/
│   ├── preprocessing.py       # 模块 2.1
│   ├── spectral_analysis.py   # 模块 2.2
│   ├── wavelet_analysis.py    # 模块 2.3
│   ├── eemd_decomp.py         # 模块 2.4
│   └── validation.py          # 模块 2.5
├── output/
│   ├── figures/               # 谱图、小波图等
│   └── results/               # 重构分量、统计表
└── run_pipeline.py            # 主执行脚本（依次调用各模块）
```

---

## 5. 预期成果

· 全年风电功率在 7–15 天尺度的 平均谱特征 及显著性判断；
· 准双周振荡 强度随时间的动态变化图谱（小波谱）；
· 提取出的 QBWO 时间序列，可用于进一步的相关性分析或预报模型输入；
· 一套可复用的 Python 工具链，适配同类新能源出力周期分析任务。

---

## 6. 注意事项

· 红噪声检验 是可靠性的关键：风电序列通常具有强自相关性，必须使用 AR(1) 背景，否则可能误报周期。
· 去趋势窗口选择：30 天窗口可有效保留 7–15 天波动；若需分析更短周期，可调整窗口至 15 天，但需注意低频泄漏。
· 数据缺失：CWT 和 EEMD 均要求连续无缺失序列，长时间缺口宜分段处理或先插值再标记。
· 模式混叠：EEMD 中噪声设置不宜过大，以 0.1–0.2 倍数据标准差为宜，平衡分解质量与残余噪声。
