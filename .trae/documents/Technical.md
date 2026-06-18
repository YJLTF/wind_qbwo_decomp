# 风电准双周振荡分析工具 - 技术架构文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      Web UI Layer                        │
│  (HTML5 + CSS3 + JavaScript + Plotly.js)                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     Flask API Server                     │
│  (Python Flask REST API)                                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Analysis Engine                        │
│  preprocessing.py / spectral_analysis.py                │
│  wavelet_analysis.py / eemd_decomp.py / validation.py   │
└─────────────────────────────────────────────────────────┘
```

## 2. 技术栈

### 前端技术
| 技术 | 用途 |
|------|------|
| HTML5 | 页面结构 |
| CSS3 | 样式与动画 |
| Vanilla JavaScript | 交互逻辑 |
| Plotly.js | 交互式图表 |

### 后端技术
| 技术 | 用途 |
|------|------|
| Python 3.9+ | 运行时 |
| Flask | Web框架 |
| NumPy | 数值计算 |
| Pandas | 数据处理 |
| SciPy | 信号处理 |
| PyEMD | EEMD分解 |
| PyCWT | 小波分析 |
| APScheduler | 任务调度(可选) |

## 3. API 接口设计

### 3.1 文件上传
```
POST /api/upload
Request: multipart/form-data
Response: {
  "success": true,
  "data": {
    "filename": "wind_power_2023.csv",
    "rows": 8760,
    "date_range": ["2023-01-01", "2023-12-31"],
    "sampling_rate": "1H"
  }
}
```

### 3.2 执行分析
```
POST /api/analyze
Request: {
  "params": {
    "period_min": 7,
    "period_max": 15,
    "detrend_window": 30,
    "eemd_trials": 50,
    "noise_std": 0.1,
    "significance": 0.95
  }
}
Response: {
  "success": true,
  "job_id": "uuid"
}
```

### 3.3 获取结果
```
GET /api/results/{job_id}
Response: {
  "status": "completed",
  "charts": {
    "original_data": "base64...",
    "detrended": "base64...",
    "spectrum": "base64...",
    "wavelet": "base64...",
    "imf_decomp": "base64...",
    "qbwo_component": "base64...",
    "validation": "base64..."
  },
  "stats": {
    "significance": true,
    "dominant_period": "10.5天",
    "variance_contribution": "23.5%"
  }
}
```

## 4. 目录结构

```
wind_qbwo_decomp/
├── README.md
├── app.py                      # Flask主应用
├── requirements.txt            # Python依赖
├── static/
│   ├── css/
│   │   └── style.css          # 自定义样式
│   └── js/
│       └── app.js             # 前端逻辑
├── templates/
│   └── index.html             # 主页面
├── src/
│   ├── preprocessing.py
│   ├── spectral_analysis.py
│   ├── wavelet_analysis.py
│   ├── eemd_decomp.py
│   └── validation.py
└── output/
    ├── figures/
    └── results/
```

## 5. 核心算法流程

### 5.1 预处理流程
```
原始数据 (15min/24点)
    ↓
重采样至1小时
    ↓
缺失值插值
    ↓
30天滑动去趋势
    ↓
去趋势序列
```

### 5.2 分析主流程
```
去趋势序列
    ├→ Welch功率谱 + AR(1)红噪声检验 → 显著性结论
    ├→ CWT小波变换 → 时频图谱
    └→ EEMD分解 → 筛选7-15天IMF → QBWO分量
                                    ↓
                          带通滤波交叉验证
```

## 6. 数据流

```
用户上传CSV
    ↓
Flask保存到临时目录
    ↓
Python读取并预处理
    ↓
各分析模块处理
    ↓
生成Base64编码图表
    ↓
前端渲染展示
```

## 7. 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 文件格式错误 | 返回具体错误信息 |
| 数据缺失过多 | 警告但继续分析 |
| 分析超时 | 60秒超时返回 |
| 内存不足 | 限制数据点数 |

## 8. 安全性

- 文件上传大小限制：100MB
- 仅允许CSV/Parquet格式
- 临时文件自动清理
- 无持久化存储
