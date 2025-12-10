/* ============================================
   NANOSECOND ARBITER AI ARENA - APP.JS
   Real-time dashboard updates
   ============================================ */

// Configuration
const CONFIG = {
    apiBaseUrl: window.location.origin,
    pollInterval: 1000,          // Poll every 1 second
    chartMaxPoints: 60,          // 1 minute of data at 1s intervals
    startingBalance: 10000,
};

// State
const state = {
    accountValue: CONFIG.startingBalance,
    pnl: 0,
    tradesCount: 0,
    wins: 0,
    ordersProcessed: 0,
    uptime: 0,
    trades: [],
    performanceHistory: [],
    aiDecision: null,
    aiReasoning: 'Waiting for AI analysis...',
};

// Performance Chart
let performanceChart = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    startPolling();
    startUptime();

    // Add initial data point
    state.performanceHistory.push({
        time: new Date(),
        value: CONFIG.startingBalance
    });
    updateChart();
});

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
                legend: {
                    display: false
                },
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
                x: {
                    display: false,
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#606070',
                        font: {
                            family: "'JetBrains Mono', monospace",
                            size: 10
                        },
                        callback: (value) => '$' + value.toLocaleString()
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 300
            }
        }
    });
}

function updateChart() {
    const labels = state.performanceHistory.map(p =>
        p.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    );
    const data = state.performanceHistory.map(p => p.value);

    // Keep only last N points
    if (labels.length > CONFIG.chartMaxPoints) {
        state.performanceHistory = state.performanceHistory.slice(-CONFIG.chartMaxPoints);
    }

    performanceChart.data.labels = labels;
    performanceChart.data.datasets[0].data = data;
    performanceChart.update('none'); // Update without animation for performance
}

// ============================================
// API POLLING
// ============================================

function startPolling() {
    // Initial fetch
    fetchOrderBook();
    fetchMetrics();
    fetchAIDecision();

    // Poll periodically
    setInterval(fetchOrderBook, CONFIG.pollInterval);
    setInterval(fetchMetrics, CONFIG.pollInterval);
    setInterval(fetchAIDecision, CONFIG.pollInterval * 2);
}

async function fetchOrderBook() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/api/orderbook`);
        if (response.ok) {
            const data = await response.json();
            updateOrderBook(data);
        }
    } catch (e) {
        console.log('Order book fetch failed, engine may not be running');
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
        // AI endpoint may not exist yet - use simulation
        simulateAIActivity();
    }
}

// ============================================
// UI UPDATES
// ============================================

function updateOrderBook(data) {
    const asksContainer = document.getElementById('asks-rows');
    const bidsContainer = document.getElementById('bids-rows');

    // Clear existing rows
    asksContainer.innerHTML = '';
    bidsContainer.innerHTML = '';

    // Render asks (reversed for display)
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

    // Render bids (sorted descending)
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

    // Calculate spread
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
        document.querySelector('.reasoning-text').textContent = data.reasoning;
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

    // Sync trading state from Python trader
    if (data.balance !== undefined) {
        console.log("DEBUG: Received Balance:", data.balance);
        state.accountValue = data.balance;
        document.getElementById('account-value').textContent =
            `$${data.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

        // Also update the Crypto Panel balance
        const cryptoBal = document.getElementById('crypto-balance');
        if (cryptoBal) {
            cryptoBal.textContent = `$${data.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    }

    if (data.pnl !== undefined) {
        state.pnl = data.pnl;
        const pnlElement = document.getElementById('pnl-value');
        pnlElement.textContent = data.pnl >= 0 ? `+$${data.pnl.toFixed(2)}` : `-$${Math.abs(data.pnl).toFixed(2)}`;
        pnlElement.className = `pnl-value ${data.pnl >= 0 ? 'positive' : 'negative'}`;

        // Also update Crypto Panel P&L
        if (document.getElementById('crypto-pnl')) {
            document.getElementById('crypto-pnl').textContent =
                data.pnl >= 0 ? `+$${data.pnl.toFixed(2)}` : `-$${Math.abs(data.pnl).toFixed(2)}`;
            document.getElementById('crypto-pnl').className = `crypto-stat-value ${data.pnl >= 0 ? 'positive' : 'negative'}`;
        }

        // Update performance history for chart
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

    // Handle trade data if present
    // Recent trades
    if (data.trade) {
        state.trades.unshift({
            action: data.trade.signal,
            price: data.trade.price,
            quantity: data.trade.quantity,
            latency: data.trade.latency_ns,
            time: new Date()
        });
        if (state.trades.length > 20) state.trades.pop();
        updateTradesUI();
    }

    // NEW: Update positions table
    if (data.positions) {
        renderPositionsTable(data.positions);
    }
}

function renderPositionsTable(positions) {
    const container = document.getElementById('positions-body');
    if (!container) return;

    const symbols = Object.keys(positions);

    if (symbols.length === 0) {
        container.innerHTML = '<div class="empty-state">No open positions</div>';
        return;
    }

    container.innerHTML = symbols.map(sym => {
        const pos = positions[sym];
        const pnl = parseFloat(pos.pnl);
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const pnlSign = pnl >= 0 ? '+' : '';

        let icon = '○';
        if (sym.includes('BTC')) icon = '₿';
        if (sym.includes('ETH')) icon = 'Ξ';
        if (sym.includes('SOL')) icon = '◎';

        return `
            <div class="position-card">
                <div class="position-header">
                    <div class="position-asset">
                        <span class="asset-icon">${icon}</span>
                        ${sym}
                    </div>
                    <div class="position-pnl ${pnlClass}">
                        ${pnlSign}$${Math.abs(pnl).toFixed(2)}
                    </div>
                </div>
                <div class="position-details">
                    <div class="detail-row">
                        <span class="detail-label">Quantity</span>
                        <span class="detail-value text-accent-cyan">${parseFloat(pos.quantity).toFixed(4)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Entry Price</span>
                        <span class="detail-value text-accent-purple">$${parseFloat(pos.entry_price).toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Current Price</span>
                        <span class="detail-value text-gradient-primary">$${parseFloat(pos.current_price).toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capital Used</span>
                        <span class="detail-value">$${parseFloat(pos.capital).toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// SIMULATION (for demo when AI not connected)
// ============================================

function simulateAIActivity() {
    // Simulation disabled to prevent ghost data
    console.log("Waiting for API connection...");
}

function simulateTrade(action) {
    // Simulation disabled
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
    // P&L
    const pnlElement = document.getElementById('pnl-value');
    pnlElement.textContent = state.pnl >= 0 ?
        `+$${state.pnl.toFixed(2)}` :
        `-$${Math.abs(state.pnl).toFixed(2)}`;
    pnlElement.className = `pnl-value ${state.pnl >= 0 ? 'positive' : 'negative'}`;

    // Account value
    document.getElementById('account-value').textContent =
        `$${state.accountValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Trades count
    document.getElementById('trades-count').textContent = state.tradesCount;

    // Win rate
    const winRate = state.tradesCount > 0 ?
        Math.round((state.wins / state.tradesCount) * 100) : 0;
    document.getElementById('win-rate').textContent = `${winRate}%`;

    // Orders processed
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
// UTILITY FUNCTIONS
// ============================================

function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// ============================================
// CRYPTO TRADING SECTION
// ============================================

// Crypto State
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
    signals: {
        btc: 'HOLD',
        eth: 'HOLD',
        sol: 'HOLD'
    }
};

// Start crypto price feeds
function initCrypto() {
    connectBinanceWebSocket();
    startCryptoPolling();
}

// Connect to Binance WebSocket for real-time prices
function connectBinanceWebSocket() {
    const symbols = ['btcusdt', 'ethusdt', 'solusdt'];
    const streams = symbols.map(s => `${s}@ticker`).join('/');
    const wsUrl = `wss://stream.binance.com:9443/stream?streams=${streams}`;

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('Connected to Binance WebSocket');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.data) {
                updateCryptoPrice(data.data);
            }
        };

        ws.onerror = (error) => {
            console.log('Binance WebSocket error, using simulated data');
            simulateCryptoPrices();
        };

        ws.onclose = () => {
            console.log('Binance WebSocket closed, reconnecting in 5s...');
            setTimeout(connectBinanceWebSocket, 5000);
        };
    } catch (e) {
        console.log('WebSocket not available, using simulated data');
        simulateCryptoPrices();
    }
}

// Update crypto price from WebSocket data
function updateCryptoPrice(data) {
    const symbol = data.s.toLowerCase();
    const price = parseFloat(data.c);
    const changePercent = parseFloat(data.P);

    if (symbol.includes('btc')) {
        cryptoState.prices.btc.previous = cryptoState.prices.btc.current;
        cryptoState.prices.btc.current = price;
        cryptoState.prices.btc.change = changePercent;
        updateCryptoPriceUI('btc', price, changePercent);
    } else if (symbol.includes('eth')) {
        cryptoState.prices.eth.previous = cryptoState.prices.eth.current;
        cryptoState.prices.eth.current = price;
        cryptoState.prices.eth.change = changePercent;
        updateCryptoPriceUI('eth', price, changePercent);
    } else if (symbol.includes('sol')) {
        cryptoState.prices.sol.previous = cryptoState.prices.sol.current;
        cryptoState.prices.sol.current = price;
        cryptoState.prices.sol.change = changePercent;
        updateCryptoPriceUI('sol', price, changePercent);
    }
}

// Update crypto price UI
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

// Simulate crypto prices if WebSocket fails
function simulateCryptoPrices() {
    // Start with realistic prices
    cryptoState.prices.btc.current = 97000 + Math.random() * 2000;
    cryptoState.prices.eth.current = 3800 + Math.random() * 200;
    cryptoState.prices.sol.current = 220 + Math.random() * 20;

    setInterval(() => {
        // Small random changes
        ['btc', 'eth', 'sol'].forEach(coin => {
            const prev = cryptoState.prices[coin].current;
            const change = (Math.random() - 0.5) * prev * 0.001;
            cryptoState.prices[coin].previous = prev;
            cryptoState.prices[coin].current = prev + change;
            cryptoState.prices[coin].change = ((cryptoState.prices[coin].current - prev) / prev * 100);

            updateCryptoPriceUI(
                coin,
                cryptoState.prices[coin].current,
                cryptoState.prices[coin].change
            );
        });
    }, 1000);
}

// Poll for crypto trading signals
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
        // Simulation disabled to preventing confusing user with fake data
        // simulateCryptoSignals();
        console.log("Waiting for API...");
    }
}

function updateCryptoDecision(data) {
    // Update reasoning
    if (data.reasoning) {
        const reasoningEl = document.getElementById('crypto-ai-reasoning');
        if (reasoningEl) {
            reasoningEl.innerHTML = `<p>${data.reasoning}</p>`;
        }
    }

    // Update signals
    if (data.signals) {
        ['btc', 'eth', 'sol'].forEach(coin => {
            const signal = data.signals[coin] || 'HOLD';
            cryptoState.signals[coin] = signal;
            updateSignalUI(coin, signal);
        });
    }

    // Update trades
    if (data.trade) {
        addCryptoTrade(data.trade);
    }

    // Update stats
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
}

function updateCryptoTradesUI() {
    const container = document.getElementById('crypto-trades-container');
    const countEl = document.getElementById('crypto-trades-count');

    if (countEl) {
        countEl.textContent = `${cryptoState.trades.length} trades`;
    }

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

    if (positionsEl) {
        positionsEl.textContent = cryptoState.positions;
    }
}

// Simulate crypto signals for demo
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
        if (reasoningEl) {
            reasoningEl.innerHTML = `<p>${reasoning}</p>`;
        }

        // Add simulated trade sometimes
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

            // Update PnL
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
