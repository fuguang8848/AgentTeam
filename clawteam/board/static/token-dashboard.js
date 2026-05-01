/**
 * Token Dashboard - Enhanced token usage visualization for ClawTeam Web UI
 * 
 * Features:
 * - 30-day trend chart (line chart)
 * - Session distribution pie chart
 * - Provider usage distribution
 * - Real-time token counter
 * - Usage predictions
 * 
 * @author ClawTeam Frontend
 */

class TokenDashboard {
    constructor(options = {}) {
        this.options = {
            updateInterval: 10000,
            trendDays: 30,
            chartColors: {
                primary: '#3b82f6',
                secondary: '#a855f7',
                success: '#10b981',
                warning: '#f59e0b',
                error: '#ef4444',
                providers: {
                    'claude': '#8b5cf6',
                    'codex': '#3b82f6',
                    'gemini': '#10b981',
                    'openai': '#f59e0b',
                    'other': '#6b7280'
                }
            },
            ...options
        };
        
        this.usageData = {
            summary: null,
            trend: [],
            providerStats: [],
            sessionBreakdown: {}
        };
        
        this.charts = {
            trend: null,
            pie: null,
            provider: null
        };
        
        this.panelVisible = false;
        this.updateTimer = null;
        
        this.init();
    }
    
    init() {
        this.createStyles();
        this.createPanel();
        this.createMiniDashboard();
        this.bindEvents();
        this.startUpdates();
    }
    
    // ==================== Styles ====================
    createStyles() {
        if (document.getElementById('token-dashboard-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'token-dashboard-styles';
        styles.textContent = `
            /* Mini Dashboard (Header) */
            .token-mini-dashboard {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 8px 16px;
                background: var(--surface-color);
                border-radius: var(--radius-sm);
                border: 1px solid var(--border-color);
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .token-mini-dashboard:hover {
                background: var(--surface-hover);
            }
            
            .token-mini-stat {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px;
            }
            
            .token-mini-value {
                font-size: 18px;
                font-weight: 700;
                color: var(--text-primary);
            }
            
            .token-mini-label {
                font-size: 11px;
                color: var(--text-tertiary);
            }
            
            .token-mini-trend {
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .token-mini-trend.up {
                color: var(--color-completed);
            }
            
            .token-mini-trend.down {
                color: var(--color-blocked);
            }
            
            /* Token Dashboard Panel */
            .token-dashboard-panel {
                position: fixed;
                top: 60px;
                right: 16px;
                width: 600px;
                max-height: 85vh;
                background: var(--surface-color);
                backdrop-filter: var(--blur);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-lg);
                box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
                z-index: 1000;
                display: none;
                overflow: hidden;
            }
            
            .token-dashboard-panel.visible {
                display: block;
                animation: panel-fade-in 0.2s ease;
            }
            
            .token-dashboard-header {
                padding: 16px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .token-dashboard-title {
                font-weight: 600;
                font-size: 16px;
                color: var(--text-primary);
            }
            
            .token-dashboard-close {
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: var(--text-tertiary);
                border-radius: 6px;
                transition: all 0.2s;
            }
            
            .token-dashboard-close:hover {
                background: var(--surface-hover);
                color: var(--text-primary);
            }
            
            .token-dashboard-body {
                padding: 16px;
                max-height: calc(85vh - 60px);
                overflow-y: auto;
            }
            
            /* Summary Cards */
            .token-summary-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 12px;
                margin-bottom: 20px;
            }
            
            .token-summary-card {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 12px;
                text-align: center;
            }
            
            .token-summary-icon {
                font-size: 24px;
                margin-bottom: 8px;
            }
            
            .token-summary-value {
                font-size: 20px;
                font-weight: 700;
                color: var(--text-primary);
            }
            
            .token-summary-label {
                font-size: 12px;
                color: var(--text-tertiary);
            }
            
            /* Chart Containers */
            .token-chart-section {
                margin-bottom: 20px;
            }
            
            .token-chart-title {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .token-chart-container {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 16px;
                min-height: 200px;
            }
            
            /* Canvas Charts */
            .token-trend-chart {
                width: 100%;
                height: 200px;
            }
            
            .token-pie-chart {
                width: 200px;
                height: 200px;
                display: block;
                margin: 0 auto;
            }
            
            /* Pie Chart Legend */
            .token-pie-legend {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 12px;
                justify-content: center;
            }
            
            .token-pie-legend-item {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                color: var(--text-secondary);
            }
            
            .token-pie-legend-color {
                width: 12px;
                height: 12px;
                border-radius: 3px;
            }
            
            /* Provider Distribution */
            .token-provider-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }
            
            .token-provider-card {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 12px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .token-provider-icon {
                width: 40px;
                height: 40px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
            }
            
            .token-provider-info {
                flex: 1;
            }
            
            .token-provider-name {
                font-size: 14px;
                font-weight: 500;
                color: var(--text-primary);
            }
            
            .token-provider-stats {
                font-size: 12px;
                color: var(--text-tertiary);
            }
            
            .token-provider-bar {
                height: 4px;
                background: var(--border-color);
                border-radius: 2px;
                overflow: hidden;
                margin-top: 6px;
            }
            
            .token-provider-bar-fill {
                height: 100%;
                border-radius: 2px;
                transition: width 0.3s ease;
            }
            
            /* Prediction Section */
            .token-prediction {
                background: linear-gradient(135deg, var(--color-progress) 0%, var(--color-broadcast) 100%);
                border-radius: var(--radius-md);
                padding: 16px;
                color: white;
                margin-top: 20px;
            }
            
            .token-prediction-title {
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            
            .token-prediction-value {
                font-size: 28px;
                font-weight: 700;
            }
            
            .token-prediction-label {
                font-size: 12px;
                opacity: 0.8;
            }
            
            .token-prediction-trend {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 8px;
                font-size: 13px;
            }
            
            /* Session Breakdown */
            .token-session-list {
                max-height: 200px;
                overflow-y: auto;
            }
            
            .token-session-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 12px;
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                margin-bottom: 6px;
            }
            
            .token-session-name {
                font-size: 13px;
                color: var(--text-primary);
                flex: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .token-session-tokens {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
            }
            
            .token-session-bar {
                width: 60px;
                height: 4px;
                background: var(--border-color);
                border-radius: 2px;
                overflow: hidden;
                margin-left: 12px;
            }
            
            .token-session-bar-fill {
                height: 100%;
                background: var(--color-progress);
                border-radius: 2px;
            }
            
            /* Mobile Responsive */
            @media (max-width: 640px) {
                .token-dashboard-panel {
                    width: calc(100vw - 32px);
                    right: 16px;
                    left: 16px;
                }
                
                .token-summary-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .token-provider-grid {
                    grid-template-columns: 1fr;
                }
                
                .token-mini-dashboard {
                    flex-wrap: wrap;
                    gap: 8px;
                    padding: 6px 12px;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // ==================== Panel ====================
    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'token-dashboard-panel';
        panel.id = 'token-dashboard-panel';
        panel.innerHTML = `
            <div class="token-dashboard-header">
                <div class="token-dashboard-title">📊 Token Usage Dashboard</div>
                <div class="token-dashboard-close" onclick="tokenDashboard.hidePanel()">✕</div>
            </div>
            <div class="token-dashboard-body">
                <!-- Summary Cards -->
                <div class="token-summary-grid">
                    <div class="token-summary-card">
                        <div class="token-summary-icon">🔤</div>
                        <div class="token-summary-value" id="total-tokens-value">0</div>
                        <div class="token-summary-label">Total Tokens</div>
                    </div>
                    <div class="token-summary-card">
                        <div class="token-summary-icon">📅</div>
                        <div class="token-summary-value" id="today-tokens-value">0</div>
                        <div class="token-summary-label">Today</div>
                    </div>
                    <div class="token-summary-card">
                        <div class="token-summary-icon">👥</div>
                        <div class="token-summary-value" id="active-sessions-value">0</div>
                        <div class="token-summary-label">Active Sessions</div>
                    </div>
                    <div class="token-summary-card">
                        <div class="token-summary-icon">⏱️</div>
                        <div class="token-summary-value" id="total-minutes-value">0</div>
                        <div class="token-summary-label">Total Minutes</div>
                    </div>
                </div>
                
                <!-- 30-Day Trend Chart -->
                <div class="token-chart-section">
                    <div class="token-chart-title">
                        <span>📈</span> 30-Day Token Trend
                    </div>
                    <div class="token-chart-container">
                        <canvas id="token-trend-chart" class="token-trend-chart"></canvas>
                    </div>
                </div>
                
                <!-- Session Distribution Pie Chart -->
                <div class="token-chart-section">
                    <div class="token-chart-title">
                        <span>🥧</span> Session Distribution
                    </div>
                    <div class="token-chart-container" style="display: flex; align-items: center; gap: 20px;">
                        <canvas id="token-pie-chart" class="token-pie-chart"></canvas>
                        <div id="token-pie-legend" class="token-pie-legend"></div>
                    </div>
                </div>
                
                <!-- Provider Distribution -->
                <div class="token-chart-section">
                    <div class="token-chart-title">
                        <span>🤖</span> Provider Usage Distribution
                    </div>
                    <div class="token-provider-grid" id="token-provider-grid"></div>
                </div>
                
                <!-- Prediction -->
                <div class="token-prediction">
                    <div class="token-prediction-title">🔮 Tomorrow's Prediction</div>
                    <div class="token-prediction-value" id="prediction-value">0 tokens</div>
                    <div class="token-prediction-label">Based on recent usage patterns</div>
                    <div class="token-prediction-trend" id="prediction-trend">
                        <span>📊</span>
                        <span>Growth rate: 0%</span>
                    </div>
                </div>
                
                <!-- Session Breakdown -->
                <div class="token-chart-section" style="margin-top: 20px;">
                    <div class="token-chart-title">
                        <span>📋</span> Top Sessions by Token Usage
                    </div>
                    <div class="token-session-list" id="token-session-list"></div>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
    }
    
    createMiniDashboard() {
        const header = document.querySelector('.header') || document.querySelector('.topbar');
        if (!header) return;
        
        const mini = document.createElement('div');
        mini.className = 'token-mini-dashboard';
        mini.id = 'token-mini-dashboard';
        mini.onclick = () => this.togglePanel();
        mini.innerHTML = `
            <div class="token-mini-stat">
                <div class="token-mini-value" id="mini-total-tokens">0K</div>
                <div class="token-mini-label">Total</div>
            </div>
            <div class="token-mini-stat">
                <div class="token-mini-value" id="mini-today-tokens">0</div>
                <div class="token-mini-label">Today</div>
            </div>
            <div class="token-mini-stat">
                <div class="token-mini-trend" id="mini-trend">
                    <span>📈</span>
                    <span>0%</span>
                </div>
                <div class="token-mini-label">Trend</div>
            </div>
        `;
        
        const existingMini = header.querySelector('.token-mini-dashboard');
        if (existingMini) {
            existingMini.replaceWith(mini);
        } else {
            header.appendChild(mini);
        }
    }
    
    // ==================== Events ====================
    bindEvents() {
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('token-dashboard-panel');
            const mini = document.getElementById('token-mini-dashboard');
            if (this.panelVisible && 
                panel && !panel.contains(e.target) && 
                mini && !mini.contains(e.target)) {
                this.hidePanel();
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.panelVisible) {
                this.hidePanel();
            }
        });
    }
    
    // ==================== Updates ====================
    startUpdates() {
        this.updateTimer = setInterval(() => {
            this.fetchData();
        }, this.options.updateInterval);
        
        this.fetchData();
    }
    
    stopUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    async fetchData() {
        try {
            // Fetch summary
            const summaryResp = await fetch('/api/usage/summary');
            if (summaryResp.ok) {
                const data = await summaryResp.json();
                if (data && typeof data === 'object' && !data.error) {
                    this.usageData.summary = data;
                }
            }
            
            // Fetch trend
            const trendResp = await fetch(`/api/usage/trend?days=${this.options.trendDays}`);
            if (trendResp.ok) {
                const trendData = await trendResp.json();
                // Validate trendData is an array before using
                if (Array.isArray(trendData)) {
                    this.usageData.trend = trendData;
                } else if (trendData && trendData.dailyData && Array.isArray(trendData.dailyData)) {
                    this.usageData.trend = trendData.dailyData;
                }
            }
            
            // Fetch provider stats
            const providerResp = await fetch('/api/usage/providers');
            if (providerResp.ok) {
                const providerData = await providerResp.json();
                if (Array.isArray(providerData)) {
                    this.usageData.providerStats = providerData;
                }
            }
            
            // Only use real data if we have valid data, otherwise use mock
            if (!this.usageData.trend || this.usageData.trend.length === 0) {
                this.useMockData();
            }
            
            this.updateUI();
            this.renderCharts();
        } catch (e) {
            console.error('Failed to fetch token data:', e);
            // Use mock data for demo
            this.useMockData();
            this.updateUI();
            this.renderCharts();
        }
    }
    
    useMockData() {
        // Generate mock data for demonstration
        const now = new Date();
        const trend = [];
        for (let i = 29; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            trend.push({
                date: date.toISOString().split('T')[0],
                tokens: Math.floor(Math.random() * 50000 + 10000),
                sessions: Math.floor(Math.random() * 10 + 2),
                providers: {
                    'claude': Math.floor(Math.random() * 20000),
                    'codex': Math.floor(Math.random() * 15000),
                    'gemini': Math.floor(Math.random() * 10000)
                }
            });
        }
        
        this.usageData.summary = {
            totalTokens: trend.reduce((sum, d) => sum + d.tokens, 0),
            todayTokens: trend[trend.length - 1].tokens,
            activeSessions: 5,
            totalMinutes: 120,
            sessionBreakdown: {
                'session-1': 45000,
                'session-2': 32000,
                'session-3': 28000,
                'session-4': 15000,
                'session-5': 8000
            },
            providerBreakdown: {
                'claude': 45000,
                'codex': 32000,
                'gemini': 28000,
                'openai': 15000
            }
        };
        
        this.usageData.trend = trend;
        
        this.usageData.providerStats = [
            { provider: 'claude', totalTokens: 45000, totalSessions: 12, percentage: 35 },
            { provider: 'codex', totalTokens: 32000, totalSessions: 8, percentage: 25 },
            { provider: 'gemini', totalTokens: 28000, totalSessions: 6, percentage: 22 },
            { provider: 'openai', totalTokens: 15000, totalSessions: 4, percentage: 12 },
            { provider: 'other', totalTokens: 8000, totalSessions: 2, percentage: 6 }
        ];
    }
    
    // ==================== UI Updates ====================
    updateUI() {
        const summary = this.usageData.summary;
        if (!summary) return;
        
        // Summary cards
        const totalTokensEl = document.getElementById('total-tokens-value');
        if (totalTokensEl) totalTokensEl.textContent = this.formatNumber(summary.totalTokens);
        const todayTokensEl = document.getElementById('today-tokens-value');
        if (todayTokensEl) todayTokensEl.textContent = this.formatNumber(summary.todayTokens);
        const activeSessionsEl = document.getElementById('active-sessions-value');
        if (activeSessionsEl) activeSessionsEl.textContent = summary.activeSessions;
        const totalMinutesEl = document.getElementById('total-minutes-value');
        if (totalMinutesEl) totalMinutesEl.textContent = summary.totalMinutes;
        
        // Mini dashboard
        const miniTotalEl = document.getElementById('mini-total-tokens');
        if (miniTotalEl) miniTotalEl.textContent = this.formatNumber(summary.totalTokens);
        const miniTodayEl = document.getElementById('mini-today-tokens');
        if (miniTodayEl) miniTodayEl.textContent = this.formatNumber(summary.todayTokens);
        
        // Trend indicator
        const trend = this.calculateTrend();
        const trendEl = document.getElementById('mini-trend');
        if (trendEl) {
            const icon = trend >= 0 ? '📈' : '📉';
            const cls = trend >= 0 ? 'up' : 'down';
            trendEl.className = `token-mini-trend ${cls}`;
            trendEl.innerHTML = `<span>${icon}</span><span>${Math.abs(trend).toFixed(1)}%</span>`;
        }
        
        // Prediction
        const prediction = this.predictNextDay();
        const predictionEl = document.getElementById('prediction-value');
        if (predictionEl) predictionEl.textContent = this.formatNumber(prediction) + ' tokens';
        
        const growthRate = this.calculateGrowthRate();
        const predictionTrend = document.getElementById('prediction-trend');
        if (predictionTrend) {
            const icon = growthRate >= 0 ? '📈' : '📉';
            predictionTrend.innerHTML = `<span>${icon}</span><span>Growth rate: ${growthRate.toFixed(1)}%</span>`;
        }
        
        // Provider grid
        this.updateProviderGrid();
        
        // Session list
        this.updateSessionList();
    }
    
    updateProviderGrid() {
        const grid = document.getElementById('token-provider-grid');
        if (!grid || !this.usageData.providerStats) return;
        
        const providerIcons = {
            'claude': '🟣',
            'codex': '🔵',
            'gemini': '🟢',
            'openai': '🟡',
            'other': '⚪'
        };
        
        const colors = this.options.chartColors.providers;
        
        grid.innerHTML = this.usageData.providerStats.map(p => `
            <div class="token-provider-card">
                <div class="token-provider-icon" style="background: ${colors[p.provider] || colors.other}20;">
                    ${providerIcons[p.provider] || '⚪'}
                </div>
                <div class="token-provider-info">
                    <div class="token-provider-name">${p.provider}</div>
                    <div class="token-provider-stats">
                        ${this.formatNumber(p.totalTokens)} tokens • ${p.totalSessions} sessions
                    </div>
                    <div class="token-provider-bar">
                        <div class="token-provider-bar-fill" style="width: ${p.percentage}%; background: ${colors[p.provider] || colors.other};"></div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    updateSessionList() {
        const list = document.getElementById('token-session-list');
        if (!list || !this.usageData.summary?.sessionBreakdown) return;
        
        const sessions = Object.entries(this.usageData.summary.sessionBreakdown)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        const maxTokens = Math.max(...sessions.map(s => s[1]));
        
        list.innerHTML = sessions.map(([name, tokens]) => `
            <div class="token-session-item">
                <div class="token-session-name">${this.escapeHtml(name)}</div>
                <div class="token-session-tokens">${this.formatNumber(tokens)}</div>
                <div class="token-session-bar">
                    <div class="token-session-bar-fill" style="width: ${(tokens / maxTokens) * 100}%"></div>
                </div>
            </div>
        `).join('');
    }
    
    // ==================== Charts ====================
    renderCharts() {
        this.renderTrendChart();
        this.renderPieChart();
    }
    
    renderTrendChart() {
        const canvas = document.getElementById('token-trend-chart');
        if (!canvas || !this.usageData.trend) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.offsetWidth;
        const height = canvas.height = canvas.offsetHeight;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        const data = this.usageData.trend;
        const padding = 40;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;
        
        // Find max value
        const maxTokens = Math.max(...data.map(d => d.tokens));
        
        // Draw grid lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
            
            // Y-axis labels
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'right';
            const value = Math.round(maxTokens - (maxTokens / 4) * i);
            ctx.fillText(this.formatNumber(value), padding - 8, y + 4);
        }
        
        // Draw line chart
        ctx.beginPath();
        ctx.strokeStyle = this.options.chartColors.primary;
        ctx.lineWidth = 2;
        
        data.forEach((d, i) => {
            const x = padding + (chartWidth / (data.length - 1)) * i;
            const y = padding + chartHeight - (d.tokens / maxTokens) * chartHeight;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw gradient fill
        const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
        gradient.addColorStop(0, this.options.chartColors.primary + '40');
        gradient.addColorStop(1, this.options.chartColors.primary + '00');
        
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = padding + (chartWidth / (data.length - 1)) * i;
            const y = padding + chartHeight - (d.tokens / maxTokens) * chartHeight;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.lineTo(width - padding, height - padding);
        ctx.lineTo(padding, height - padding);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // Draw dots
        data.forEach((d, i) => {
            const x = padding + (chartWidth / (data.length - 1)) * i;
            const y = padding + chartHeight - (d.tokens / maxTokens) * chartHeight;
            
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fillStyle = this.options.chartColors.primary;
            ctx.fill();
        });
        
        // X-axis labels (show every 5 days)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        
        data.forEach((d, i) => {
            if (i % 5 === 0 || i === data.length - 1) {
                const x = padding + (chartWidth / (data.length - 1)) * i;
                ctx.fillText(d.date.slice(5), x, height - 10);
            }
        });
    }
    
    renderPieChart() {
        const canvas = document.getElementById('token-pie-chart');
        if (!canvas || !this.usageData.summary?.sessionBreakdown) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.offsetWidth;
        const height = canvas.height = canvas.offsetHeight;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.max(10, Math.min(width, height) / 2 - 20);
        
        ctx.clearRect(0, 0, width, height);
        
        const sessions = Object.entries(this.usageData.summary.sessionBreakdown);
        const total = sessions.reduce((sum, [, tokens]) => sum + tokens, 0);
        
        const colors = [
            '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
            '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#ec4899'
        ];
        
        let startAngle = -Math.PI / 2;
        
        sessions.forEach(([name, tokens], i) => {
            const sliceAngle = (tokens / total) * Math.PI * 2;
            
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();
            
            // Add slight border
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            startAngle += sliceAngle;
        });
        
        // Draw center circle (donut effect)
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = 'var(--surface-hover)';
        ctx.fill();
        
        // Center text
        ctx.fillStyle = 'var(--text-primary)';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.formatNumber(total), centerX, centerY - 8);
        ctx.font = '12px sans-serif';
        ctx.fillStyle = 'var(--text-tertiary)';
        ctx.fillText('tokens', centerX, centerY + 10);
        
        // Update legend
        const legend = document.getElementById('token-pie-legend');
        if (legend) {
            legend.innerHTML = sessions.slice(0, 6).map(([name, tokens], i) => `
                <div class="token-pie-legend-item">
                    <div class="token-pie-legend-color" style="background: ${colors[i % colors.length]};"></div>
                    <span>${this.escapeHtml(name.slice(0, 12))}</span>
                    <span>${((tokens / total) * 100).toFixed(1)}%</span>
                </div>
            `).join('');
        }
    }
    
    // ==================== Panel Control ====================
    togglePanel() {
        if (this.panelVisible) {
            this.hidePanel();
        } else {
            this.showPanel();
        }
    }
    
    showPanel() {
        const panel = document.getElementById('token-dashboard-panel');
        if (panel) {
            panel.classList.add('visible');
            this.panelVisible = true;
            this.fetchData();
        }
    }
    
    hidePanel() {
        const panel = document.getElementById('token-dashboard-panel');
        if (panel) {
            panel.classList.remove('visible');
            this.panelVisible = false;
        }
    }
    
    // ==================== Helpers ====================
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
    
    calculateTrend() {
        const trend = this.usageData.trend;
        if (!trend || trend.length < 2) return 0;
        
        const today = trend[trend.length - 1].tokens;
        const yesterday = trend[trend.length - 2].tokens;
        
        if (yesterday === 0) return 0;
        return ((today - yesterday) / yesterday) * 100;
    }
    
    calculateGrowthRate() {
        const trend = this.usageData.trend;
        if (!trend || trend.length < 7) return 0;
        
        const last7 = trend.slice(-7).reduce((sum, d) => sum + d.tokens, 0);
        const prev7 = trend.slice(-14, -7).reduce((sum, d) => sum + d.tokens, 0);
        
        if (prev7 === 0) return 0;
        return ((last7 - prev7) / prev7) * 100;
    }
    
    predictNextDay() {
        const trend = this.usageData.trend;
        if (!trend || trend.length < 7) return 0;
        
        // Simple linear regression
        const last7 = trend.slice(-7);
        const avg = last7.reduce((sum, d) => sum + d.tokens, 0) / 7;
        const growthRate = this.calculateGrowthRate();
        
        return Math.round(avg * (1 + growthRate / 100));
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Global instance
let tokenDashboard = null;

function initTokenDashboard(options = {}) {
    tokenDashboard = new TokenDashboard(options);
    return tokenDashboard;
}

// No auto-init — initialized by index.html nav button click.
// Call initTokenDashboard() manually to start.