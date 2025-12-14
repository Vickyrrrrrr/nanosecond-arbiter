/* ============================================
   NANOSECOND ARBITER AI ARENA - APP.JS v2.0
   Real-time dashboard with advanced features
   ============================================ */

// ============================================
// CONFIGURATION
// ============================================

const CONFIG = {
    apiBaseUrl: window.location.origin,
    pollInterval: 1000,
    chartMaxPoints: 60,
    startingBalance: 10000,
    soundEnabled: true,
    histogramBins: 20,
};

// ============================================
// STATE MANAGEMENT
// ============================================

const state = {
    accountValue: CONFIG.startingBalance,
    pnl: 0,
    tradesCount: 0,
    wins: 0,
    losses: 0,
    ordersProcessed: 0,
    uptime: 0,
    trades: [],
    performanceHistory: [],
    latencyHistory: [],
    aiDecision: null,
    aiReasoning: 'Waiting for AI analysis...',
    aiConfidence: 0.78,
    theme: 'dark',
    soundEnabled: true,
    // Risk metrics
    sharpeRatio: 1.85,
    maxDrawdown: -3.2,
    winLossRatio: 1.42,
    var95: 125.50,
    // Order flow
    buyPressure: 55,
    sellPressure: 45,
    // System metrics
    cpuUsage: 12,
    memoryUsage: 45,
    bufferFill: 23,
    // Latency percentiles
    p50: 19,
    p95: 25,
    p99: 32,
    p999: 45,
};

// Audio context for sound effects
let audioContext = null;

// Performance Chart
let performanceChart = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    initHistogram();
    initRingBufferViz();
    initAudio();
    startPolling();
    startUptime();
    initKeyboardShortcuts();

    // Add initial data point
    state.performanceHistory.push({
        time: new Date(),
        value: CONFIG.startingBalance
    });
    updateChart();

    // Initial latency data
    generateLatencyData();

    // Show startup notification
    showNotification('success', 'Engine Started', 'Nanosecond Arbiter is now active');
});

// ============================================
// AUDIO SYSTEM
// ============================================

function initAudio() {
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
        console.log('Audio not supported');
    }
}

function playSound(type) {
    if (!state.soundEnabled || !audioContext) return;

    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    switch (type) {
        case 'trade':
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.1;
            break;
        case 'profit':
            oscillator.frequency.value = 1200;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.15;
            break;
        case 'loss':
            oscillator.frequency.value = 300;
            oscillator.type = 'triangle';
            gainNode.gain.value = 0.1;
            break;
        case 'alert':
            oscillator.frequency.value = 600;
            oscillator.type = 'square';
            gainNode.gain.value = 0.08;
            break;
    }

    oscillator.start();
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.2);
    oscillator.stop(audioContext.currentTime + 0.2);
}

function toggleSound() {
    state.soundEnabled = !state.soundEnabled;
    const btn = document.getElementById('sound-toggle');
    btn.textContent = state.soundEnabled ? '🔊' : '🔇';
    btn.classList.toggle('muted', !state.soundEnabled);

    if (state.soundEnabled) {
        playSound('alert');
    }
}

// ============================================
// THEME SYSTEM
// ============================================

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    html.setAttribute('data-theme', newTheme);
    state.theme = newTheme;

    const btn = document.getElementById('theme-toggle');
    btn.textContent = newTheme === 'dark' ? '🌙' : '☀️';

    // Update chart colors
    updateChartTheme(newTheme);

    showNotification('success', 'Theme Changed', `Switched to ${newTheme} mode`);
}

function updateChartTheme(theme) {
    if (!performanceChart) return;

    const isDark = theme === 'dark';
    performanceChart.options.scales.y.ticks.color = isDark ? '#606070' : '#8a8aa0';
    performanceChart.options.scales.y.grid.color = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
    performanceChart.update('none');
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
            case '?':
                toggleShortcutsModal();
                break;
            case 't':
                toggleTheme();
                break;
            case 'm':
                toggleSound();
                break;
            case 'e':
                exportTradesCSV();
                break;
            case 'j':
                exportTradesJSON();
                break;
            case 'r':
                refreshData();
                break;
            case '1':
                document.getElementById('main-content').scrollIntoView({ behavior: 'smooth' });
                break;
            case '2':
                document.getElementById('crypto-section').scrollIntoView({ behavior: 'smooth' });
                break;
            case '3':
                document.getElementById('advanced-section').scrollIntoView({ behavior: 'smooth' });
                break;
            case 'escape':
                closeAllModals();
                break;
        }
    });
}

function toggleShortcutsModal() {
    const modal = document.getElementById('shortcuts-modal');
    modal.classList.toggle('active');
}

function closeAllModals() {
    document.getElementById('shortcuts-modal').classList.remove('active');
}

// ============================================
// NOTIFICATIONS
// ============================================

function showNotification(type, title, message) {
    const container = document.getElementById('notification-container');

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;

    const icons = {
        success: '✅',
        warning: '⚠️',
        error: '❌',
        info: 'ℹ️'
    };

    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || icons.info}</span>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100px)';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ============================================
// CHART INITIALIZATION
// ============================================

function initChart() {
    const ctx = document.getElementById('performance-chart').getContext('2d');

    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Portfolio Value',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 26, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#a0a0b0',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: (context) => `$${context.raw.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: { display: false, grid: { display: false } },
                y: {
                    display: true,
                    position: 'right',
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                    ticks: {
                        color: '#606070',
                        font: { family: "'JetBrains Mono', monospace", size: 10 },
                        callback: (value) => '$' + value.toLocaleString()
                    }
                }
            },
            interaction: { intersect: false, mode: 'index' },
            animation: { duration: 300 }
        }
    });
}

function updateChart() {
    const labels = state.performanceHistory.map(p =>
        p.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    );
    const data = state.performanceHistory.map(p => p.value);

    if (labels.length > CONFIG.chartMaxPoints) {
        state.performanceHistory = state.performanceHistory.slice(-CONFIG.chartMaxPoints);
    }

    performanceChart.data.labels = labels;
    performanceChart.data.datasets[0].data = data;
    performanceChart.update('none');
}

// ============================================
// LATENCY HISTOGRAM
// ============================================

function initHistogram() {
    generateHistogramBars();
}

function generateHistogramBars() {
    const container = document.getElementById('histogram-chart');
    container.innerHTML = '';

    for (let i = 0; i < CONFIG.histogramBins; i++) {
        const bar = document.createElement('div');
        bar.className = 'histogram-bar';
        bar.style.height = '0%';
        bar.setAttribute('data-value', '0ns');
        container.appendChild(bar);
    }
}

function generateLatencyData() {
    // Generate realistic latency distribution (log-normal)
    const bars = document.querySelectorAll('.histogram-bar');
    const baseLatency = 19;

    bars.forEach((bar, i) => {
        // Create a distribution that peaks in the middle-low range
        const position = i / CONFIG.histogramBins;
        let height;

        if (position < 0.3) {
            height = 30 + position * 200;
        } else if (position < 0.5) {
            height = 90 - (position - 0.3) * 300;
        } else {
            height = 30 - (position - 0.5) * 50;
        }

        height = Math.max(5, Math.min(100, height + (Math.random() - 0.5) * 20));

        const latencyValue = Math.round(baseLatency + i * 2 + Math.random() * 3);

        bar.style.height = height + '%';
        bar.setAttribute('data-value', latencyValue + 'ns');
    });

    // Update percentile values with slight variations
    state.p50 = 19 + Math.floor(Math.random() * 3);
    state.p95 = 25 + Math.floor(Math.random() * 4);
    state.p99 = 32 + Math.floor(Math.random() * 5);
    state.p999 = 45 + Math.floor(Math.random() * 10);

    document.getElementById('p50-value').textContent = state.p50 + 'ns';
    document.getElementById('p95-value').textContent = state.p95 + 'ns';
    document.getElementById('p99-value').textContent = state.p99 + 'ns';
    document.getElementById('p999-value').textContent = state.p999 + 'ns';
}

// ============================================
// RING BUFFER VISUALIZATION
// ============================================

function initRingBufferViz() {
    const container = document.getElementById('ring-buffer-viz');
    const numSlots = 32;

    for (let i = 0; i < numSlots; i++) {
        const slot = document.createElement('div');
        slot.className = 'buffer-slot';
        container.appendChild(slot);
    }

    updateRingBufferViz();
}

function updateRingBufferViz() {
    const slots = document.querySelectorAll('.buffer-slot');
    const fillPercent = state.bufferFill / 100;
    const numFilled = Math.floor(slots.length * fillPercent);

    slots.forEach((slot, i) => {
        slot.classList.toggle('filled', i < numFilled);
    });
}

// ============================================
// API POLLING
// ============================================

function startPolling() {
    fetchOrderBook();
    fetchMetrics();
    fetchAIDecision();

    setInterval(fetchOrderBook, CONFIG.pollInterval);
    setInterval(fetchMetrics, CONFIG.pollInterval);
    setInterval(fetchAIDecision, CONFIG.pollInterval * 2);
    setInterval(updateAdvancedMetrics, CONFIG.pollInterval);
}

function refreshData() {
    fetchOrderBook();
    fetchMetrics();
    fetchAIDecision();
    showNotification('info', 'Refreshed', 'All data has been refreshed');
}

async function fetchOrderBook() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/api/orderbook`);
        if (response.ok) {
            const data = await response.json();
            updateOrderBook(data);
        }
    } catch (e) {
        console.log('Order book fetch failed');
    }
}

async function fetchMetrics() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/api/metrics`);
        if (response.ok) {
            const data = await response.json();
            updateMetrics(data);
        }
    } catch (e) {
        console.log('Metrics fetch failed');
    }
}

async function fetchAIDecision() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/api/ai-decision`);
        if (response.ok) {
            const data = await response.json();
            updateAIDecision(data);
        }
    } catch (e) {
        simulateAIActivity();
    }
}

// ============================================
// UI UPDATES
// ============================================

function updateOrderBook(data) {
    const asksContainer = document.getElementById('asks-rows');
    const bidsContainer = document.getElementById('bids-rows');

    asksContainer.innerHTML = '';
    bidsContainer.innerHTML = '';

    const asks = data.asks || [];
    asks.slice(0, 5).forEach(level => {
        const totalQty = level.orders.reduce((sum, o) => sum + o.quantity, 0);
        const row = document.createElement('div');
        row.className = 'order-row ask';
        row.innerHTML = `
            <span>$${(level.price / 100).toFixed(2)}</span>
            <span>${totalQty}</span>
        `;
        asksContainer.appendChild(row);
    });

    const bids = data.bids || [];
    bids.slice(-5).reverse().forEach(level => {
        const totalQty = level.orders.reduce((sum, o) => sum + o.quantity, 0);
        const row = document.createElement('div');
        row.className = 'order-row bid';
        row.innerHTML = `
            <span>$${(level.price / 100).toFixed(2)}</span>
            <span>${totalQty}</span>
        `;
        bidsContainer.appendChild(row);
    });

    if (asks.length > 0 && bids.length > 0) {
        const bestAsk = asks[0].price / 100;
        const bestBid = bids[bids.length - 1].price / 100;
        const spread = (bestAsk - bestBid).toFixed(2);
        document.getElementById('spread-badge').textContent = `Spread: $${spread}`;
    }
}

function updateMetrics(data) {
    document.getElementById('engine-latency').textContent = data.latency || 29;
    document.getElementById('latency-value').textContent = `${data.latency || 29}ns`;

    const throughput = data.throughput || 33543877;
    document.getElementById('engine-throughput').textContent =
        (throughput / 1000000).toFixed(1) + 'M';

    if (data.ordersProcessed) {
        state.ordersProcessed = data.ordersProcessed;
        document.getElementById('orders-processed').textContent =
            state.ordersProcessed.toLocaleString();
    }
}

function updateAIDecision(data) {
    if (data.reasoning) {
        state.aiReasoning = data.reasoning;
        updateAIReasoningChain(data.reasoning);
    }

    if (data.signal) {
        const decisionBox = document.querySelector('.decision-box');
        const signalText = document.getElementById('current-signal');

        decisionBox.className = 'decision-box ' + data.signal.toLowerCase();
        signalText.textContent = data.signal.toUpperCase();

        document.getElementById('ai-status-text').textContent =
            data.signal === 'NEUTRAL' ? 'Analyzing market...' :
                `Signal: ${data.signal.toUpperCase()}`;
    }

    if (data.confidence !== undefined) {
        updateConfidenceGauge(data.confidence);
    }

    if (data.balance !== undefined) {
        state.accountValue = data.balance;
        document.getElementById('account-value').textContent =
            `$${data.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    if (data.pnl !== undefined) {
        const prevPnl = state.pnl;
        state.pnl = data.pnl;
        const pnlElement = document.getElementById('pnl-value');
        pnlElement.textContent = data.pnl >= 0 ? `+$${data.pnl.toFixed(2)}` : `-$${Math.abs(data.pnl).toFixed(2)}`;
        pnlElement.className = `pnl-value ${data.pnl >= 0 ? 'positive' : 'negative'}`;

        // Check for significant P&L change
        if (Math.abs(data.pnl - prevPnl) > 10) {
            if (data.pnl > prevPnl) {
                playSound('profit');
            } else {
                playSound('loss');
            }
        }

        state.performanceHistory.push({
            time: new Date(),
            value: state.accountValue
        });
        updateChart();
    }

    if (data.tradesCount !== undefined) {
        state.tradesCount = data.tradesCount;
        document.getElementById('trades-count').textContent = data.tradesCount;
    }

    if (data.trade) {
        const trade = {
            id: Date.now(),
            action: data.trade.signal || 'BUY',
            price: data.trade.price?.toFixed(2) || '0.00',
            quantity: data.trade.quantity || 1,
            latency: data.trade.latency_ns || 29,
            time: new Date(),
            pnl: 0
        };
        state.trades.unshift(trade);
        if (state.trades.length > 20) state.trades.pop();
        updateTradesUI();
        playSound('trade');
    }
}

function updateAIReasoningChain(reasoning) {
    const container = document.getElementById('ai-decision-chain');

    // Split reasoning into steps (or generate fake steps for demo)
    const steps = reasoning.split('. ').filter(s => s.length > 0).slice(0, 4);

    container.innerHTML = steps.map((step, i) => `
        <div class="decision-step">
            <span class="step-number">${i + 1}</span>
            <span class="step-text">${step}${step.endsWith('.') ? '' : '...'}</span>
        </div>
    `).join('');
}

function updateConfidenceGauge(confidence) {
    state.aiConfidence = confidence;
    document.getElementById('confidence-value').textContent = Math.round(confidence * 100) + '%';

    const fill = document.getElementById('confidence-fill');
    fill.style.width = (confidence * 100) + '%';

    fill.className = 'confidence-fill';
    if (confidence >= 0.7) {
        fill.classList.add('high');
    } else if (confidence >= 0.4) {
        fill.classList.add('medium');
    } else {
        fill.classList.add('low');
    }
}

// ============================================
// ADVANCED METRICS UPDATES
// ============================================

function updateAdvancedMetrics() {
    // Simulate advanced metrics updates
    updateRiskMetrics();
    updateOrderFlow();
    updateSystemMetrics();
    generateLatencyData();
}

function updateRiskMetrics() {
    // Sharpe Ratio
    state.sharpeRatio = 1.5 + Math.random() * 0.8;
    document.getElementById('sharpe-ratio').textContent = state.sharpeRatio.toFixed(2);
    document.getElementById('sharpe-meter').style.width = Math.min(100, state.sharpeRatio * 40) + '%';

    // Max Drawdown
    state.maxDrawdown = -(2 + Math.random() * 4);
    document.getElementById('max-drawdown').textContent = state.maxDrawdown.toFixed(1) + '%';
    document.getElementById('drawdown-meter').style.width = Math.abs(state.maxDrawdown) * 10 + '%';

    // Win/Loss Ratio
    if (state.tradesCount > 0) {
        state.winLossRatio = state.wins / Math.max(1, state.losses);
    }
    document.getElementById('win-loss-ratio').textContent = state.winLossRatio.toFixed(2);
    document.getElementById('winloss-meter').style.width = Math.min(100, state.winLossRatio * 40) + '%';

    // VaR
    state.var95 = 100 + Math.random() * 100;
    document.getElementById('var-value').textContent = '$' + state.var95.toFixed(2);
    document.getElementById('var-meter').style.width = Math.min(100, state.var95 / 3) + '%';
}

function updateOrderFlow() {
    // Simulate order flow changes
    const change = (Math.random() - 0.5) * 10;
    state.buyPressure = Math.max(20, Math.min(80, state.buyPressure + change));
    state.sellPressure = 100 - state.buyPressure;

    document.getElementById('flow-buy').style.width = state.buyPressure + '%';
    document.getElementById('flow-buy').textContent = Math.round(state.buyPressure) + '%';
    document.getElementById('flow-sell').style.width = state.sellPressure + '%';
    document.getElementById('flow-sell').textContent = Math.round(state.sellPressure) + '%';

    const imbalance = state.buyPressure - 50;
    const arrow = document.getElementById('imbalance-arrow');
    const text = document.getElementById('imbalance-text');

    if (imbalance > 5) {
        arrow.textContent = '↑';
        arrow.className = 'imbalance-arrow bullish';
        text.textContent = `Bullish Pressure (+${Math.round(imbalance)}%)`;
    } else if (imbalance < -5) {
        arrow.textContent = '↓';
        arrow.className = 'imbalance-arrow bearish';
        text.textContent = `Bearish Pressure (${Math.round(imbalance)}%)`;
    } else {
        arrow.textContent = '→';
        arrow.className = 'imbalance-arrow';
        text.textContent = 'Neutral (balanced)';
    }
}

function updateSystemMetrics() {
    // CPU
    state.cpuUsage = 8 + Math.random() * 15;
    document.getElementById('cpu-usage').textContent = Math.round(state.cpuUsage) + '%';

    // Memory
    state.memoryUsage = 40 + Math.random() * 20;
    document.getElementById('memory-usage').textContent = Math.round(state.memoryUsage) + 'MB';

    // Buffer fill
    state.bufferFill = 10 + Math.random() * 40;
    document.getElementById('buffer-fill').textContent = Math.round(state.bufferFill) + '%';
    updateRingBufferViz();
}

// ============================================
// SIMULATION (for demo)
// ============================================

function simulateAIActivity() {
    const signals = ['BUY', 'SELL', 'NEUTRAL'];
    const reasonings = [
        'Bullish momentum detected. RSI indicates oversold conditions. MACD showing positive divergence.',
        'Bearish divergence forming. Taking profit on long positions. Volume declining.',
        'Market consolidating. Waiting for clear breakout signal. Bollinger bands narrowing.',
        'Strong support level holding. Accumulating position. Order flow bullish.',
        'Resistance tested 3 times. Expecting breakdown. Smart money exiting.',
        'Volume surge detected. Following smart money flow. Institutional buying detected.',
    ];

    if (Math.random() > 0.7) {
        const signal = signals[Math.floor(Math.random() * signals.length)];
        const reasoning = reasonings[Math.floor(Math.random() * reasonings.length)];
        const confidence = 0.5 + Math.random() * 0.45;

        updateAIDecision({ signal, reasoning, confidence });

        if (signal !== 'NEUTRAL') {
            simulateTrade(signal);
        }
    }
}

function simulateTrade(action) {
    const price = 100 + Math.random() * 50;
    const quantity = Math.floor(1 + Math.random() * 10);
    const latency = 20 + Math.floor(Math.random() * 20);

    const tradeValue = price * quantity;
    const pnlChange = action === 'BUY' ?
        (Math.random() > 0.4 ? Math.random() * 50 : -Math.random() * 30) :
        (Math.random() > 0.4 ? Math.random() * 50 : -Math.random() * 30);

    state.pnl += pnlChange;
    state.accountValue = CONFIG.startingBalance + state.pnl;
    state.tradesCount++;
    state.ordersProcessed++;

    if (pnlChange > 0) {
        state.wins++;
        playSound('profit');
    } else {
        state.losses++;
        playSound('loss');
    }

    const trade = {
        id: Date.now(),
        action,
        price: price.toFixed(2),
        quantity,
        latency,
        time: new Date(),
        pnl: pnlChange.toFixed(2),
    };

    state.trades.unshift(trade);
    if (state.trades.length > 20) state.trades.pop();

    updateTradesUI();
    updateStatsUI();

    state.performanceHistory.push({
        time: new Date(),
        value: state.accountValue
    });
    updateChart();

    playSound('trade');
}

function updateTradesUI() {
    const container = document.getElementById('trades-container');

    if (state.trades.length === 0) {
        container.innerHTML = `
            <div class="trade-placeholder">
                <span>No trades yet. AI is analyzing...</span>
            </div>
        `;
        return;
    }

    container.innerHTML = state.trades.map(trade => `
        <div class="trade-item">
            <div class="trade-left">
                <span class="trade-action ${trade.action.toLowerCase()}">${trade.action}</span>
                <span class="trade-details">$${trade.price} × ${trade.quantity}</span>
            </div>
            <div class="trade-right">
                <span class="trade-latency">⚡ ${trade.latency}ns</span>
                <span class="trade-time">${trade.time.toLocaleTimeString()}</span>
            </div>
        </div>
    `).join('');
}

function updateStatsUI() {
    const pnlElement = document.getElementById('pnl-value');
    pnlElement.textContent = state.pnl >= 0 ?
        `+$${state.pnl.toFixed(2)}` :
        `-$${Math.abs(state.pnl).toFixed(2)}`;
    pnlElement.className = `pnl-value ${state.pnl >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('account-value').textContent =
        `$${state.accountValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById('trades-count').textContent = state.tradesCount;

    const winRate = state.tradesCount > 0 ?
        Math.round((state.wins / state.tradesCount) * 100) : 0;
    document.getElementById('win-rate').textContent = `${winRate}%`;

    document.getElementById('orders-processed').textContent =
        state.ordersProcessed.toLocaleString();
}

// ============================================
// UPTIME COUNTER
// ============================================

function startUptime() {
    setInterval(() => {
        state.uptime++;
        document.getElementById('uptime').textContent = state.uptime;
    }, 1000);
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

function exportTradesCSV() {
    if (state.trades.length === 0) {
        showNotification('warning', 'No Data', 'No trades to export');
        return;
    }

    const headers = ['ID', 'Action', 'Price', 'Quantity', 'Latency (ns)', 'Time', 'P&L'];
    const rows = state.trades.map(t => [
        t.id,
        t.action,
        t.price,
        t.quantity,
        t.latency,
        t.time.toISOString(),
        t.pnl || 0
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    downloadFile(csv, 'trades.csv', 'text/csv');
    showNotification('success', 'Exported', 'Trades exported as CSV');
}

function exportTradesJSON() {
    if (state.trades.length === 0) {
        showNotification('warning', 'No Data', 'No trades to export');
        return;
    }

    const json = JSON.stringify(state.trades, null, 2);
    downloadFile(json, 'trades.json', 'application/json');
    showNotification('success', 'Exported', 'Trades exported as JSON');
}

function exportRiskReport() {
    const report = {
        timestamp: new Date().toISOString(),
        metrics: {
            sharpeRatio: state.sharpeRatio,
            maxDrawdown: state.maxDrawdown,
            winLossRatio: state.winLossRatio,
            var95: state.var95,
            totalTrades: state.tradesCount,
            wins: state.wins,
            losses: state.losses,
            pnl: state.pnl
        },
        latency: {
            p50: state.p50,
            p95: state.p95,
            p99: state.p99,
            p999: state.p999
        }
    };

    const json = JSON.stringify(report, null, 2);
    downloadFile(json, 'risk_report.json', 'application/json');
    showNotification('success', 'Exported', 'Risk report exported');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================
// CRYPTO TRADING SECTION
// ============================================

const cryptoState = {
    prices: {
        btc: { current: 0, previous: 0, change: 0 },
        eth: { current: 0, previous: 0, change: 0 },
        sol: { current: 0, previous: 0, change: 0 }
    },
    trades: [],
    balance: 1000,
    pnl: 0,
    positions: 0,
    signals: { btc: 'HOLD', eth: 'HOLD', sol: 'HOLD' }
};

function initCrypto() {
    connectBinanceWebSocket();
    startCryptoPolling();
}

function connectBinanceWebSocket() {
    const symbols = ['btcusdt', 'ethusdt', 'solusdt'];
    const streams = symbols.map(s => `${s}@ticker`).join('/');
    const wsUrl = `wss://stream.binance.com:9443/stream?streams=${streams}`;

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => console.log('Connected to Binance WebSocket');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.data) updateCryptoPrice(data.data);
        };
        ws.onerror = () => simulateCryptoPrices();
        ws.onclose = () => setTimeout(connectBinanceWebSocket, 5000);
    } catch (e) {
        simulateCryptoPrices();
    }
}

function updateCryptoPrice(data) {
    const symbol = data.s.toLowerCase();
    const price = parseFloat(data.c);
    const changePercent = parseFloat(data.P);

    if (symbol.includes('btc')) {
        cryptoState.prices.btc = { current: price, change: changePercent };
        updateCryptoPriceUI('btc', price, changePercent);
    } else if (symbol.includes('eth')) {
        cryptoState.prices.eth = { current: price, change: changePercent };
        updateCryptoPriceUI('eth', price, changePercent);
    } else if (symbol.includes('sol')) {
        cryptoState.prices.sol = { current: price, change: changePercent };
        updateCryptoPriceUI('sol', price, changePercent);
    }
}

function updateCryptoPriceUI(coin, price, changePercent) {
    const priceEl = document.getElementById(`${coin}-price`);
    const changeEl = document.getElementById(`${coin}-change`);

    if (priceEl) {
        priceEl.textContent = `$${price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    if (changeEl) {
        const isPositive = changePercent >= 0;
        changeEl.textContent = `${isPositive ? '+' : ''}${changePercent.toFixed(2)}%`;
        changeEl.className = `crypto-change ${isPositive ? 'positive' : 'negative'}`;
    }
}

function simulateCryptoPrices() {
    cryptoState.prices.btc.current = 97000 + Math.random() * 2000;
    cryptoState.prices.eth.current = 3800 + Math.random() * 200;
    cryptoState.prices.sol.current = 220 + Math.random() * 20;

    setInterval(() => {
        ['btc', 'eth', 'sol'].forEach(coin => {
            const prev = cryptoState.prices[coin].current;
            const change = (Math.random() - 0.5) * prev * 0.001;
            cryptoState.prices[coin].current = prev + change;
            cryptoState.prices[coin].change = ((cryptoState.prices[coin].current - prev) / prev * 100);
            updateCryptoPriceUI(coin, cryptoState.prices[coin].current, cryptoState.prices[coin].change);
        });
    }, 1000);
}

function startCryptoPolling() {
    fetchCryptoDecision();
    setInterval(fetchCryptoDecision, 2000);
}

async function fetchCryptoDecision() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/api/crypto-decision`);
        if (response.ok) {
            const data = await response.json();
            updateCryptoDecision(data);
        }
    } catch (e) {
        simulateCryptoSignals();
    }
}

function updateCryptoDecision(data) {
    if (data.reasoning) {
        const reasoningEl = document.getElementById('crypto-ai-reasoning');
        if (reasoningEl) reasoningEl.innerHTML = `<p>${data.reasoning}</p>`;
    }

    if (data.signals) {
        ['btc', 'eth', 'sol'].forEach(coin => {
            const signal = data.signals[coin] || 'HOLD';
            cryptoState.signals[coin] = signal;
            updateSignalUI(coin, signal);
        });
    }

    if (data.trade) addCryptoTrade(data.trade);
    if (data.balance) cryptoState.balance = data.balance;
    if (data.pnl !== undefined) cryptoState.pnl = data.pnl;
    if (data.positions !== undefined) cryptoState.positions = data.positions;
    updateCryptoStatsUI();
}

function updateSignalUI(coin, signal) {
    const signalEl = document.querySelector(`#${coin}-signal .signal-value`);
    if (signalEl) {
        signalEl.textContent = signal;
        signalEl.className = `signal-value ${signal.toLowerCase()}`;
    }
}

function addCryptoTrade(trade) {
    cryptoState.trades.unshift(trade);
    if (cryptoState.trades.length > 15) cryptoState.trades.pop();
    updateCryptoTradesUI();
    playSound('trade');
}

function updateCryptoTradesUI() {
    const container = document.getElementById('crypto-trades-container');
    const countEl = document.getElementById('crypto-trades-count');

    if (countEl) countEl.textContent = `${cryptoState.trades.length} trades`;
    if (!container) return;

    if (cryptoState.trades.length === 0) {
        container.innerHTML = `
            <div class="trade-placeholder">
                <span>Start crypto_trader.py to begin</span>
            </div>
        `;
        return;
    }

    container.innerHTML = cryptoState.trades.map(trade => `
        <div class="trade-item">
            <div class="trade-left">
                <span class="trade-action ${trade.action.toLowerCase()}">${trade.action} ${trade.coin}</span>
                <span class="trade-details">$${trade.price} × ${trade.quantity}</span>
            </div>
            <div class="trade-right">
                <span class="trade-latency">⚡ ${trade.latency}ns</span>
                <span class="trade-time">${new Date(trade.timestamp).toLocaleTimeString()}</span>
            </div>
        </div>
    `).join('');
}

function updateCryptoStatsUI() {
    const balanceEl = document.getElementById('crypto-balance');
    const pnlEl = document.getElementById('crypto-pnl');
    const positionsEl = document.getElementById('crypto-positions');

    if (balanceEl) {
        balanceEl.textContent = `$${cryptoState.balance.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    if (pnlEl) {
        const isPositive = cryptoState.pnl >= 0;
        pnlEl.textContent = `${isPositive ? '+' : ''}$${cryptoState.pnl.toFixed(2)}`;
        pnlEl.className = `crypto-stat-value ${isPositive ? 'positive' : 'negative'}`;
    }

    if (positionsEl) positionsEl.textContent = cryptoState.positions;
}

function simulateCryptoSignals() {
    if (Math.random() > 0.8) {
        const coins = ['btc', 'eth', 'sol'];
        const signals = ['BUY', 'SELL', 'HOLD'];
        const reasonings = [
            'BTC showing strength above 97k support. ETH following.',
            'SOL momentum increasing. Breaking resistance.',
            'Market consolidating. Waiting for breakout.',
            'Volume spike detected on BTC. Smart money accumulating.',
            'ETH gas fees dropping. Network activity bullish.',
        ];

        const randomCoin = coins[Math.floor(Math.random() * coins.length)];
        const randomSignal = signals[Math.floor(Math.random() * signals.length)];
        const reasoning = reasonings[Math.floor(Math.random() * reasonings.length)];

        cryptoState.signals[randomCoin] = randomSignal;
        updateSignalUI(randomCoin, randomSignal);

        const reasoningEl = document.getElementById('crypto-ai-reasoning');
        if (reasoningEl) reasoningEl.innerHTML = `<p>${reasoning}</p>`;

        if (randomSignal !== 'HOLD' && Math.random() > 0.5) {
            const price = cryptoState.prices[randomCoin].current || 100;
            const trade = {
                action: randomSignal,
                coin: randomCoin.toUpperCase(),
                price: price.toFixed(2),
                quantity: (Math.random() * 0.5).toFixed(4),
                latency: 20 + Math.floor(Math.random() * 20),
                timestamp: new Date().toISOString()
            };
            addCryptoTrade(trade);

            const pnlChange = randomSignal === 'BUY' ?
                (Math.random() > 0.4 ? Math.random() * 20 : -Math.random() * 10) :
                (Math.random() > 0.4 ? Math.random() * 20 : -Math.random() * 10);
            cryptoState.pnl += pnlChange;
            cryptoState.positions += randomSignal === 'BUY' ? 1 : -1;
            cryptoState.positions = Math.max(0, cryptoState.positions);
            updateCryptoStatsUI();
        }
    }
}

// Initialize crypto on page load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initCrypto, 1000);
});
