import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 创建一年的模拟风电功率数据
start_date = datetime(2023, 1, 1)
n_days = 365
n_hours = n_days * 24

# 时间序列
timestamps = [start_date + timedelta(hours=i) for i in range(n_hours)]

# 模拟风电功率（包含多个周期成分）
np.random.seed(42)

# 基础功率（随机波动）
base_power = np.random.normal(50, 15, n_hours)

# 年度趋势（季节性变化）
annual_trend = 20 * np.sin(2 * np.pi * np.arange(n_hours) / (365 * 24))

# 10天准双周振荡（我们要识别的目标周期）
qbwo_component = 15 * np.sin(2 * np.pi * np.arange(n_hours) / (10 * 24))

# 3天短周期
short_period = 8 * np.sin(2 * np.pi * np.arange(n_hours) / (3 * 24))

# 日周期（昼夜变化）
daily_cycle = 5 * np.sin(2 * np.pi * np.arange(n_hours) / 24)

# 合成总功率
total_power = base_power + annual_trend + qbwo_component + short_period + daily_cycle

# 确保功率为正数
total_power = np.maximum(total_power, 0)

# 创建DataFrame
df = pd.DataFrame({
    'timestamp': timestamps,
    'power_kw': total_power
})

# 保存为CSV
df.to_csv('/workspace/data/raw/test_wind_power.csv', index=False)
print(f"测试数据已生成: {len(df)} 行")
print(f"时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
print(f"功率范围: {df['power_kw'].min():.1f} ~ {df['power_kw'].max():.1f} kW")