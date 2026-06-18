"""
风电准双周振荡识别与分解系统 - Flask主应用
"""
import os
import uuid
import base64
import json
import traceback
from io import BytesIO
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import numpy as np

from src.preprocessing import preprocess_data
from src.spectral_analysis import run_spectral_analysis
from src.wavelet_analysis import run_wavelet_analysis
from src.eemd_decomp import run_eemd_analysis
from src.validation import run_validation

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = 'data/raw'
app.config['OUTPUT_FOLDER'] = 'output'

# 存储分析任务状态
tasks = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """文件上传接口"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'})

    # 检查文件格式
    ext = file.filename.lower().split('.')[-1]
    if ext not in ['csv', 'parquet']:
        return jsonify({'success': False, 'error': '仅支持CSV/Parquet格式'})

    # 保存文件
    task_id = str(uuid.uuid4())
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{task_id}.{ext}')
    file.save(filepath)

    try:
        # 读取并解析数据
        if ext == 'csv':
            df = pd.read_csv(filepath)
        else:
            df = pd.read_parquet(filepath)

        # 查找时间列和功率列
        time_col = None
        power_col = None

        for col in df.columns:
            col_lower = str(col).lower()
            if 'time' in col_lower or 'date' in col_lower or 'dt' in col_lower:
                time_col = col
            elif 'power' in col_lower or 'wind' in col_lower or 'kw' in col_lower or 'mw' in col_lower:
                power_col = col

        # 如果没找到，尝试使用第一列和第二列
        if time_col is None:
            time_col = df.columns[0]
        if power_col is None:
            power_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        # 转换时间列
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)

        # 基本统计
        rows = len(df)
        date_range = [str(df[time_col].min()), str(df[time_col].max())]

        # 判断采样率
        if rows > 7000:  # 大约8760(全年小时数据)
            sampling_rate = "15min" if rows > 30000 else "1h"
        else:
            sampling_rate = "1h"

        # 存储数据信息
        tasks[task_id] = {
            'filepath': filepath,
            'time_col': time_col,
            'power_col': power_col,
            'filename': file.filename,
            'rows': rows,
            'date_range': date_range,
            'sampling_rate': sampling_rate,
            'params': None,
            'results': None,
            'status': 'uploaded'
        }

        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'filename': file.filename,
                'rows': rows,
                'date_range': date_range,
                'sampling_rate': sampling_rate,
                'columns': list(df.columns)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/demo', methods=['GET'])
def load_demo():
    """加载测试数据接口"""
    demo_file = 'data/raw/test_wind_power.csv'

    if not os.path.exists(demo_file):
        return jsonify({'success': False, 'error': '测试数据文件不存在'})

    task_id = str(uuid.uuid4())
    filepath = demo_file

    try:
        df = pd.read_csv(filepath)

        # 查找时间列和功率列
        time_col = None
        power_col = None

        for col in df.columns:
            col_lower = str(col).lower()
            if 'time' in col_lower or 'date' in col_lower or 'dt' in col_lower:
                time_col = col
            elif 'power' in col_lower or 'wind' in col_lower or 'kw' in col_lower or 'mw' in col_lower:
                power_col = col

        if time_col is None:
            time_col = df.columns[0]
        if power_col is None:
            power_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)

        rows = len(df)
        date_range = [str(df[time_col].min()), str(df[time_col].max())]
        sampling_rate = "1h"

        tasks[task_id] = {
            'filepath': filepath,
            'time_col': time_col,
            'power_col': power_col,
            'filename': 'test_wind_power.csv',
            'rows': rows,
            'date_range': date_range,
            'sampling_rate': sampling_rate,
            'params': None,
            'results': None,
            'status': 'uploaded'
        }

        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'filename': 'test_wind_power.csv (测试数据)',
                'rows': rows,
                'date_range': date_range,
                'sampling_rate': sampling_rate,
                'columns': list(df.columns)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """执行分析接口"""
    data = request.get_json()
    task_id = data.get('task_id')
    params = data.get('params', {})

    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'})

    task = tasks[task_id]

    # 更新参数
    task['params'] = {
        'period_min': params.get('period_min', 7),
        'period_max': params.get('period_max', 15),
        'detrend_window': params.get('detrend_window', 30),
        'eemd_trials': params.get('eemd_trials', 50),
        'noise_std': params.get('noise_std', 0.1),
        'significance': params.get('significance', 0.95)
    }

    try:
        task['status'] = 'analyzing'

        # 读取数据
        filepath = task['filepath']
        ext = filepath.lower().split('.')[-1]

        if ext == 'csv':
            df = pd.read_csv(filepath)
        else:
            df = pd.read_parquet(filepath)

        time_col = task['time_col']
        power_col = task['power_col']

        # 确保时间排序
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)

        # 执行预处理
        preprocess_result = preprocess_data(
            df, time_col, power_col,
            detrend_window=task['params']['detrend_window']
        )

        # 统一数据引用
        detrended_series = preprocess_result['detrended_series']
        time_index = preprocess_result['time_index']

        # 执行频谱分析
        spectral_result = run_spectral_analysis(
            detrended_series,
            time_index,
            period_min=task['params']['period_min'],
            period_max=task['params']['period_max'],
            significance=task['params']['significance']
        )

        # 执行小波分析
        wavelet_result = run_wavelet_analysis(
            detrended_series,
            time_index,
            period_min=task['params']['period_min'],
            period_max=task['params']['period_max'],
            significance=task['params']['significance']
        )

        # 执行EEMD分解
        eemd_result = run_eemd_analysis(
            detrended_series,
            period_min=task['params']['period_min'],
            period_max=task['params']['period_max'],
            trials=task['params']['eemd_trials'],
            noise_std=task['params']['noise_std']
        )

        # 执行验证
        validation_result = run_validation(
            detrended_series,
            eemd_result['qbwo_component'],
            period_min=task['params']['period_min'],
            period_max=task['params']['period_max']
        )

        # 整理结果
        task['results'] = {
            'preprocessing': preprocess_result,
            'spectral': spectral_result,
            'wavelet': wavelet_result,
            'eemd': eemd_result,
            'validation': validation_result
        }
        task['status'] = 'completed'

        # 生成统计摘要
        dp = eemd_result.get('dominant_period')
        stats = {
            'significance': bool(spectral_result.get('is_significant', False)),
            'dominant_period': round(float(dp), 2) if dp not in (None, 'N/A') else None,
            'variance_contribution': round(float(eemd_result.get('variance_ratio', 0)) * 100, 2),
            'correlation': round(float(validation_result.get('correlation', 0)), 3)
        }

        return jsonify({
            'success': True,
            'stats': stats,
            'charts': {
                'original_data': preprocess_result.get('original_chart', ''),
                'detrended': preprocess_result.get('detrended_chart', ''),
                'spectrum': spectral_result.get('chart', ''),
                'wavelet': wavelet_result.get('chart', ''),
                'imf_decomp': eemd_result.get('imf_chart', ''),
                'qbwo_component': eemd_result.get('qbwo_chart', ''),
                'validation': validation_result.get('chart', '')
            }
        })

    except Exception as e:
        task['status'] = 'error'
        task['error'] = str(e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'})

    task = tasks[task_id]
    return jsonify({
        'success': True,
        'status': task['status'],
        'error': task.get('error', None)
    })

@app.route('/api/params/<task_id>', methods=['GET'])
def get_params(task_id):
    """获取任务参数"""
    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'})

    task = tasks[task_id]
    return jsonify({
        'success': True,
        'params': task['params']
    })

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs('output/figures', exist_ok=True)
    os.makedirs('output/results', exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5000)
