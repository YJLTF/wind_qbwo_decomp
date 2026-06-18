# WindQBWO - 风电准双周振荡识别与分解系统

[English](#english) | [中文](#中文)

---

## 中文部分

### 项目简介

**WindQBWO** 是一款专业的风电出力准双周振荡识别与分解系统，提供现代化的 Web 界面，用于分析全年风电功率时间序列，识别并提取 **7-15 天** 时间尺度上的强周期成分（气象学中称为"准双周振荡"，Quasi-Biweekly Oscillation, QBWO）。

### 核心功能

- **数据上传**：支持 CSV/Parquet 格式，自动识别时间列和功率列
- **智能预处理**：自动重采样（15min→1h）、缺失值处理、趋势消除
- **频谱分析**：Welch 功率谱 + AR(1) 红噪声显著性检验
- **时频分析**：连续小波变换(CWT)，定位周期强度的时间演变
- **自适应分解**：EEMD 提取准双周振荡分量
- **交叉验证**：带通滤波对比，确保结果可靠性

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI Layer                          │
│           (HTML5 + CSS3 + JavaScript + Plotly.js)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask API Server                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Engine                             │
│   preprocessing.py │ spectral_analysis.py │ wavelet_analysis │
│          eemd_decomp.py │ validation.py                      │
└─────────────────────────────────────────────────────────────┘
```

### 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 启动服务

```bash
python app.py
```

服务启动后，访问 `http://localhost:5000`

#### 3. 使用系统

1. 上传包含时间列和功率列的 CSV 或 Parquet 文件
2. 设置分析参数（周期范围、去趋势窗口等）
3. 点击"开始分析"
4. 查看可视化结果

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 周期范围 | 7-15 天 | 目标周期分析区间 |
| 去趋势窗口 | 30 天 | 滑动平均窗口大小 |
| EEMD 试验次数 | 50 | 集合经验模态分解试验数 |
| 噪声标准差 | 0.1 | EEMD 噪声比例 |
| 显著性水平 | 95% | 统计检验置信度 |

### 项目结构

```
wind_qbwo_decomp/
├── app.py                      # Flask 主应用
├── requirements.txt            # Python 依赖
├── README.md                    # 本文档
├── templates/
│   └── index.html              # 前端页面
├── static/
│   ├── css/
│   │   └── style.css           # 样式
│   └── js/
│       └── app.js              # 前端逻辑
├── src/
│   ├── preprocessing.py        # 数据预处理
│   ├── spectral_analysis.py    # 频谱分析
│   ├── wavelet_analysis.py      # 小波分析
│   ├── eemd_decomp.py          # EEMD 分解
│   └── validation.py           # 结果验证
└── data/
    ├── raw/                    # 原始数据
    └── processed/              # 处理后数据
```

### 分析流程

1. **预处理**：重采样至 1 小时，线性插值填补缺失，30 天滑动去趋势
2. **频谱分析**：Welch 功率谱估计 + AR(1) 红噪声 95% 置信检验
3. **时频分析**：连续小波变换（Morlet 母波），绘制时变周期图谱
4. **EEMD 分解**：提取周期在 7-15 天内的 IMF，重构 QBWO 分量
5. **交叉验证**：Butterworth 带通滤波与 EEMD 结果对比

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML5, CSS3, JavaScript, Plotly.js |
| 后端 | Python 3, Flask |
| 分析 | NumPy, Pandas, SciPy, PyEMD |

### 输出结果

- **功率谱图**：含红噪声背景与 95% 置信线
- **小波功率谱图**：时频热力图，标注 7 天/15 天参考线
- **IMF 分解图**：各分量周期与方差贡献
- **QBWO 分量图**：提取的准双周振荡时间序列
- **验证对比图**：带通滤波与 EEMD 结果对比

---

## English

### WindQBWO - Identification and Decomposition of Quasi-Biweekly Oscillation in Wind Power Generation

A professional web-based system for identifying and extracting quasi-biweekly oscillation (QBWO) components from annual wind power time series data.

### Features

- **Data Upload**: CSV/Parquet support with auto column detection
- **Smart Preprocessing**: Auto resampling, missing value interpolation, detrending
- **Spectral Analysis**: Welch PSD with AR(1) red noise significance test
- **Time-Frequency Analysis**: Continuous Wavelet Transform (CWT)
- **Adaptive Decomposition**: EEMD for QBWO extraction
- **Cross-Validation**: Bandpass filter comparison

### Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

### Requirements

```
Flask>=3.0.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.11.0
PyEMD>=0.5.1
plotly>=5.18.0
kaleido>=0.2.1
```

---

## 附录：算法详解

### A. 红噪声检验

风电序列具有强自相关性，必须使用 AR(1) 红噪声背景进行检验：

```
P(f) = (2·Δt·σ²·(1-α²)) / (1 - 2·α·cos(2πf·Δt) + α²)
```

其中 α 为滞后-1 自相关系数。

### B. EEMD 分解

集合经验模态分解通过多次添加白噪声进行分解，有效抑制模式混叠：

1. 添加白噪声（标准差为原数据的 0.1 倍）
2. 进行经验模态分解(EMD)
3. 重复 50 次，取集平均
4. 筛选周期在 7-15 天内的 IMF

### C. 去趋势窗口选择

30 天窗口可有效保留 7-15 天波动；如需分析更短周期，可调整至 15 天。
