// WindQBWO - 前端交互逻辑

let currentTaskId = null;
let charts = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initUploadArea();
    updatePeriodRange();
});

// 加载测试数据
async function loadDemoData() {
    try {
        showLoading('正在加载测试数据...');
        const response = await fetch('/api/demo');
        const result = await response.json();

        if (result.success) {
            currentTaskId = result.data.task_id;
            showFileInfo(result.data);
            document.getElementById('analyzeBtn').disabled = false;
            hideLoading();
        } else {
            showError(result.error || '加载失败');
        }
    } catch (error) {
        showError('加载出错: ' + error.message);
    }
}

// 上传区域初始化
function initUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // 点击上传
    uploadArea.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // 文件选择
    fileInput.addEventListener('change', handleFileSelect);

    // 拖拽
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
}

// 处理文件选择
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

// 处理文件
async function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'parquet'].includes(ext)) {
        showError('仅支持 CSV 或 Parquet 格式');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showLoading('正在上传文件...');
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            currentTaskId = result.data.task_id;
            showFileInfo(result.data);
            document.getElementById('analyzeBtn').disabled = false;
            hideLoading();
        } else {
            showError(result.error || '上传失败');
        }
    } catch (error) {
        showError('上传出错: ' + error.message);
    }
}

// 显示文件信息
function showFileInfo(data) {
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.style.display = 'block';

    document.getElementById('fileName').textContent = data.filename;
    document.getElementById('rowCount').textContent = data.rows.toLocaleString() + ' 行';
    document.getElementById('dateRange').textContent = `${data.date_range[0]} ~ ${data.date_range[1]}`;
    document.getElementById('samplingRate').textContent = data.sampling_rate;
}

// 重置参数
function resetParams() {
    document.getElementById('periodMin').value = 7;
    document.getElementById('periodMax').value = 15;
    document.getElementById('detrendWindow').value = 30;
    document.getElementById('eemdTrials').value = 50;
    document.getElementById('noiseStd').value = 0.1;
    document.getElementById('significance').value = '0.95';
    updatePeriodRange();
}

// 更新周期范围滑块
function updatePeriodRange() {
    const min = parseInt(document.getElementById('periodMin').value);
    const max = parseInt(document.getElementById('periodMax').value);
    const range = 30;
    const fillPercent = ((min + max) / 2 / range) * 100;

    document.getElementById('rangeFill').style.width = `${fillPercent}%`;
}

// 开始分析
async function startAnalysis() {
    if (!currentTaskId) {
        showError('请先上传数据');
        return;
    }

    const params = {
        period_min: parseInt(document.getElementById('periodMin').value),
        period_max: parseInt(document.getElementById('periodMax').value),
        detrend_window: parseInt(document.getElementById('detrendWindow').value),
        eemd_trials: parseInt(document.getElementById('eemdTrials').value),
        noise_std: parseFloat(document.getElementById('noiseStd').value),
        significance: parseFloat(document.getElementById('significance').value)
    };

    const btn = document.getElementById('analyzeBtn');
    btn.disabled = true;

    const progressSection = document.getElementById('progressSection');
    progressSection.style.display = 'block';

    try {
        // 模拟进度更新
        let progress = 0;
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const steps = document.querySelectorAll('.step');

        const updateProgress = (step, text) => {
            progress = step * 20;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = text;

            steps.forEach((s, i) => {
                s.classList.remove('active', 'completed');
                if (i < step) s.classList.add('completed');
                if (i === step) s.classList.add('active');
            });
        };

        updateProgress(0, '正在提交分析任务...');

        // 发送分析请求
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, params })
        });

        updateProgress(1, '正在预处理数据...');

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error);
        }

        updateProgress(2, '正在执行频谱分析...');
        await sleep(300);

        updateProgress(3, '正在执行时频分析...');
        await sleep(300);

        updateProgress(4, '正在进行EEMD分解...');
        await sleep(300);

        updateProgress(5, '正在进行交叉验证...');
        await sleep(500);

        // 显示结果
        progressFill.style.width = '100%';
        progressText.textContent = '分析完成！';

        setTimeout(() => {
            progressSection.style.display = 'none';
            showResults(result);
        }, 500);

    } catch (error) {
        showError('分析失败: ' + error.message);
        progressSection.style.display = 'none';
    }

    btn.disabled = false;
}

// 显示结果
function showResults(result) {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'block';

    // 统计摘要
    const stats = result.stats;
    const statsSummary = document.getElementById('statsSummary');
    statsSummary.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">显著性</span>
            <span class="stat-value ${stats.significance ? 'significant' : 'not-significant'}">
                ${stats.significance ? '✓ 是' : '✗ 否'}
            </span>
        </div>
        <div class="stat-item">
            <span class="stat-label">主导周期</span>
            <span class="stat-value">${stats.dominant_period ? stats.dominant_period.toFixed(1) + ' 天' : 'N/A'}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">方差贡献</span>
            <span class="stat-value">${stats.variance_contribution.toFixed(1)}%</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">相关系数</span>
            <span class="stat-value">${stats.correlation.toFixed(3)}</span>
        </div>
    `;

    // 渲染图表
    renderChart('chartOriginal', result.charts.original_data);
    renderChart('chartDetrended', result.charts.detrended);
    renderChart('chartSpectrum', result.charts.spectrum);
    renderChart('chartWavelet', result.charts.wavelet);
    renderChart('chartIMF', result.charts.imf_decomp);
    renderChart('chartQBWO', result.charts.qbwo_component);
    renderChart('chartValidation', result.charts.validation);

    // 滚动到结果
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// 渲染图表
function renderChart(elementId, chartData) {
    const container = document.getElementById(elementId);
    if (!container) return;

    if (chartData) {
        try {
            const parsed = typeof chartData === 'string' ? JSON.parse(chartData) : chartData;
            Plotly.newPlot(container, parsed.data, parsed.layout || {}, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            });
        } catch (e) {
            container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">图表加载失败</p>';
        }
    }
}

// 工具函数
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showError(message) {
    hideLoading();
    alert(message);
}

function showLoading(text) {
    // 简单实现，可添加loading动画
    console.log(text);
}

function hideLoading() {
    // 简单实现
}
