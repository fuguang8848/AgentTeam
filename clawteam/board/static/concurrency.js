/**
 * Concurrency Control Panel - Session monitoring and resource management for ClawTeam Web UI
 * 
 * Features:
 * - Active sessions count monitoring
 * - Resource usage display (CPU, memory, tokens)
 * - Concurrency limits configuration
 * - Session list with status indicators
 * - Real-time updates via WebSocket
 * 
 * @author ClawTeam Frontend
 */

class ConcurrencyControl {
    constructor(options = {}) {
        this.options = {
            updateInterval: 5000,
            maxSessions: 10,
            warningThreshold: 0.8,
            criticalThreshold: 0.95,
            ...options
        };
        
        this.sessions = [];
        this.stats = {
            activeSessions: 0,
            maxSessions: this.options.maxSessions,
            cpuUsage: 0,
            memoryUsage: 0,
            tokenUsage: 0,
            tokenLimit: 100000,
            queueLength: 0
        };
        
        this.limits = {
            maxConcurrentSessions: 10,
            maxTokensPerSession: 50000,
            maxQueueLength: 100,
            timeoutMinutes: 30
        };
        
        this.panelVisible = false;
        this.updateTimer = null;
        this.ws = null;
        
        this.init();
    }
    
    init() {
        this.createStyles();
        this.createPanel();
        this.createIndicator();
        this.bindEvents();
        this.startUpdates();
    }
    
    // ==================== Styles ====================
    createStyles() {
        if (document.getElementById('concurrency-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'concurrency-styles';
        styles.textContent = `
            /* Concurrency Indicator (Header) */
            .concurrency-indicator {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 16px;
                background: var(--surface-color);
                border-radius: var(--radius-sm);
                border: 1px solid var(--border-color);
            }
            
            .concurrency-stat {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .concurrency-stat-icon {
                font-size: 16px;
            }
            
            .concurrency-stat-value {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .concurrency-stat-label {
                font-size: 11px;
                color: var(--text-tertiary);
            }
            
            .concurrency-stat.warning .concurrency-stat-value {
                color: var(--color-pending);
            }
            
            .concurrency-stat.critical .concurrency-stat-value {
                color: var(--color-blocked);
            }
            
            /* Concurrency Panel */
            .concurrency-panel {
                position: fixed;
                top: 60px;
                right: 400px;
                width: 420px;
                max-height: 80vh;
                background: var(--surface-color);
                backdrop-filter: var(--blur);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-lg);
                box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
                z-index: 1000;
                display: none;
                overflow: hidden;
            }
            
            .concurrency-panel.visible {
                display: block;
                animation: panel-fade-in 0.2s ease;
            }
            
            .concurrency-panel-header {
                padding: 16px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .concurrency-panel-title {
                font-weight: 600;
                font-size: 16px;
                color: var(--text-primary);
            }
            
            .concurrency-panel-close {
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
            
            .concurrency-panel-close:hover {
                background: var(--surface-hover);
                color: var(--text-primary);
            }
            
            .concurrency-panel-body {
                padding: 16px;
                max-height: calc(80vh - 60px);
                overflow-y: auto;
            }
            
            /* Resource Usage Section */
            .resource-section {
                margin-bottom: 20px;
            }
            
            .resource-section-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .resource-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }
            
            .resource-card {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 12px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .resource-card-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .resource-card-icon {
                font-size: 20px;
            }
            
            .resource-card-value {
                font-size: 24px;
                font-weight: 700;
                color: var(--text-primary);
            }
            
            .resource-card-label {
                font-size: 12px;
                color: var(--text-tertiary);
            }
            
            .resource-card-bar {
                height: 6px;
                background: var(--border-color);
                border-radius: 3px;
                overflow: hidden;
            }
            
            .resource-card-bar-fill {
                height: 100%;
                border-radius: 3px;
                transition: width 0.3s ease;
            }
            
            .resource-card-bar-fill.normal {
                background: var(--color-completed);
            }
            
            .resource-card-bar-fill.warning {
                background: var(--color-pending);
            }
            
            .resource-card-bar-fill.critical {
                background: var(--color-blocked);
            }
            
            /* Sessions List */
            .sessions-list {
                margin-top: 16px;
            }
            
            .sessions-list-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            }
            
            .sessions-list-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
            }
            
            .sessions-list-count {
                font-size: 12px;
                color: var(--text-tertiary);
            }
            
            .session-item {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 12px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: all 0.2s;
            }
            
            .session-item:hover {
                background: var(--surface-active);
            }
            
            .session-status-indicator {
                width: 10px;
                height: 10px;
                border-radius: 50%;
            }
            
            .session-status-indicator.active {
                background: var(--color-completed);
                box-shadow: 0 0 8px var(--color-completed);
            }
            
            .session-status-indicator.idle {
                background: var(--color-pending);
            }
            
            .session-status-indicator.error {
                background: var(--color-blocked);
            }
            
            .session-status-indicator.completed {
                background: var(--text-tertiary);
            }
            
            .session-info {
                flex: 1;
                min-width: 0;
            }
            
            .session-name {
                font-size: 14px;
                font-weight: 500;
                color: var(--text-primary);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .session-meta {
                font-size: 12px;
                color: var(--text-tertiary);
                display: flex;
                gap: 8px;
            }
            
            .session-provider {
                padding: 2px 8px;
                background: var(--surface-active);
                border-radius: 4px;
                font-size: 11px;
                color: var(--text-secondary);
            }
            
            .session-actions {
                display: flex;
                gap: 4px;
            }
            
            .session-action-btn {
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: var(--text-tertiary);
                border-radius: 4px;
                transition: all 0.2s;
                border: none;
                background: transparent;
            }
            
            .session-action-btn:hover {
                background: var(--surface-active);
                color: var(--text-primary);
            }
            
            .session-action-btn.kill:hover {
                color: var(--color-blocked);
            }
            
            /* Limits Configuration */
            .limits-section {
                margin-top: 20px;
                padding-top: 16px;
                border-top: 1px solid var(--border-color);
            }
            
            .limits-section-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 12px;
            }
            
            .limit-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 0;
            }
            
            .limit-label {
                font-size: 13px;
                color: var(--text-secondary);
            }
            
            .limit-input {
                width: 100px;
                padding: 6px 12px;
                background: var(--surface-hover);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-sm);
                color: var(--text-primary);
                font-size: 13px;
                text-align: right;
            }
            
            .limit-input:focus {
                outline: none;
                border-color: var(--color-progress);
            }
            
            .limits-save-btn {
                margin-top: 12px;
                padding: 8px 16px;
                background: var(--color-progress);
                color: white;
                border-radius: var(--radius-sm);
                font-size: 13px;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
            }
            
            .limits-save-btn:hover {
                background: #2563eb;
            }
            
            /* Queue Monitor */
            .queue-section {
                margin-top: 16px;
            }
            
            .queue-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            }
            
            .queue-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
            }
            
            .queue-count {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .queue-count.warning {
                color: var(--color-pending);
            }
            
            .queue-count.critical {
                color: var(--color-blocked);
            }
            
            .queue-bar {
                height: 8px;
                background: var(--border-color);
                border-radius: 4px;
                overflow: hidden;
            }
            
            .queue-bar-fill {
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease;
                background: var(--color-progress);
            }
            
            .queue-bar-fill.warning {
                background: var(--color-pending);
            }
            
            .queue-bar-fill.critical {
                background: var(--color-blocked);
            }
            
            /* Mobile Responsive */
            @media (max-width: 480px) {
                .concurrency-panel {
                    width: calc(100vw - 32px);
                    right: 16px;
                    left: 16px;
                }
                
                .resource-grid {
                    grid-template-columns: 1fr;
                }
                
                .concurrency-indicator {
                    flex-wrap: wrap;
                    padding: 6px 12px;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // ==================== Panel ====================
    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'concurrency-panel';
        panel.id = 'concurrency-panel';
        panel.innerHTML = `
            <div class="concurrency-panel-header">
                <div class="concurrency-panel-title">⚡ Concurrency Control</div>
                <div class="concurrency-panel-close" onclick="concurrencyControl.hidePanel()">✕</div>
            </div>
            <div class="concurrency-panel-body">
                <!-- Resource Usage -->
                <div class="resource-section">
                    <div class="resource-section-title">
                        <span>📊</span> Resource Usage
                    </div>
                    <div class="resource-grid">
                        <div class="resource-card" id="sessions-card">
                            <div class="resource-card-header">
                                <span class="resource-card-icon">👥</span>
                                <span class="resource-card-label">Active Sessions</span>
                            </div>
                            <div class="resource-card-value" id="active-sessions-value">0</div>
                            <div class="resource-card-bar">
                                <div class="resource-card-bar-fill normal" id="sessions-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="resource-card" id="tokens-card">
                            <div class="resource-card-header">
                                <span class="resource-card-icon">🔤</span>
                                <span class="resource-card-label">Token Usage</span>
                            </div>
                            <div class="resource-card-value" id="token-usage-value">0</div>
                            <div class="resource-card-bar">
                                <div class="resource-card-bar-fill normal" id="tokens-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="resource-card" id="cpu-card">
                            <div class="resource-card-header">
                                <span class="resource-card-icon">💻</span>
                                <span class="resource-card-label">CPU Usage</span>
                            </div>
                            <div class="resource-card-value" id="cpu-usage-value">0%</div>
                            <div class="resource-card-bar">
                                <div class="resource-card-bar-fill normal" id="cpu-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="resource-card" id="memory-card">
                            <div class="resource-card-header">
                                <span class="resource-card-icon">💾</span>
                                <span class="resource-card-label">Memory Usage</span>
                            </div>
                            <div class="resource-card-value" id="memory-usage-value">0%</div>
                            <div class="resource-card-bar">
                                <div class="resource-card-bar-fill normal" id="memory-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Queue Monitor -->
                <div class="queue-section">
                    <div class="queue-header">
                        <div class="queue-title">📬 Message Queue</div>
                        <div class="queue-count" id="queue-count">0 pending</div>
                    </div>
                    <div class="queue-bar">
                        <div class="queue-bar-fill" id="queue-bar-fill" style="width: 0%"></div>
                    </div>
                </div>
                
                <!-- Sessions List -->
                <div class="sessions-list">
                    <div class="sessions-list-header">
                        <div class="sessions-list-title">Active Sessions</div>
                        <div class="sessions-list-count" id="sessions-list-count">0 sessions</div>
                    </div>
                    <div id="sessions-list-container"></div>
                </div>
                
                <!-- Limits Configuration -->
                <div class="limits-section">
                    <div class="limits-section-title">⚙️ Concurrency Limits</div>
                    <div class="limit-item">
                        <span class="limit-label">Max Concurrent Sessions</span>
                        <input type="number" class="limit-input" id="limit-max-sessions" value="10" min="1" max="50">
                    </div>
                    <div class="limit-item">
                        <span class="limit-label">Max Tokens per Session</span>
                        <input type="number" class="limit-input" id="limit-max-tokens" value="50000" min="1000" max="500000">
                    </div>
                    <div class="limit-item">
                        <span class="limit-label">Max Queue Length</span>
                        <input type="number" class="limit-input" id="limit-max-queue" value="100" min="10" max="1000">
                    </div>
                    <div class="limit-item">
                        <span class="limit-label">Session Timeout (min)</span>
                        <input type="number" class="limit-input" id="limit-timeout" value="30" min="5" max="120">
                    </div>
                    <button class="limits-save-btn" onclick="concurrencyControl.saveLimits()">Save Limits</button>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
    }
    
    createIndicator() {
        // Find header to add indicator
        const header = document.querySelector('.header') || document.querySelector('.topbar');
        if (!header) return;
        
        const indicator = document.createElement('div');
        indicator.className = 'concurrency-indicator';
        indicator.id = 'concurrency-indicator';
        indicator.onclick = () => this.togglePanel();
        indicator.innerHTML = `
            <div class="concurrency-stat" id="indicator-sessions">
                <span class="concurrency-stat-icon">👥</span>
                <span class="concurrency-stat-value" id="indicator-sessions-value">0</span>
                <span class="concurrency-stat-label">sessions</span>
            </div>
            <div class="concurrency-stat" id="indicator-tokens">
                <span class="concurrency-stat-icon">🔤</span>
                <span class="concurrency-stat-value" id="indicator-tokens-value">0K</span>
                <span class="concurrency-stat-label">tokens</span>
            </div>
            <div class="concurrency-stat" id="indicator-queue">
                <span class="concurrency-stat-icon">📬</span>
                <span class="concurrency-stat-value" id="indicator-queue-value">0</span>
                <span class="concurrency-stat-label">queue</span>
            </div>
        `;
        
        const existingIndicator = header.querySelector('.concurrency-indicator');
        if (existingIndicator) {
            existingIndicator.replaceWith(indicator);
        } else {
            header.appendChild(indicator);
        }
    }
    
    // ==================== Events ====================
    bindEvents() {
        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('concurrency-panel');
            const indicator = document.getElementById('concurrency-indicator');
            if (this.panelVisible && 
                panel && !panel.contains(e.target) && 
                indicator && !indicator.contains(e.target)) {
                this.hidePanel();
            }
        });
        
        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.panelVisible) {
                this.hidePanel();
            }
        });
    }
    
    // ==================== Updates ====================
    startUpdates() {
        this.updateTimer = setInterval(() => {
            this.fetchStats();
        }, this.options.updateInterval);
        
        // Initial fetch
        this.fetchStats();
    }
    
    stopUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    async fetchStats() {
        try {
            // Fetch session registry stats
            const sessionsResp = await fetch('/api/sessions');
            if (sessionsResp.ok) {
                const sessionsData = await sessionsResp.json();
                this.sessions = sessionsData.sessions || [];
                this.stats.activeSessions = sessionsData.activeCount || this.sessions.length;
            }
            
            // Fetch token usage
            const usageResp = await fetch('/api/usage/summary');
            if (usageResp.ok) {
                const usageData = await usageResp.json();
                this.stats.tokenUsage = usageData.totalTokens || 0;
                this.stats.tokenLimit = usageData.tokenLimit || 100000;
            }
            
            // Fetch transport stats for queue
            const transportResp = await fetch('/api/transport/stats');
            if (transportResp.ok) {
                const transportData = await transportResp.json();
                this.stats.queueLength = transportData.queueLength || 0;
            }
            
            // Simulate CPU/Memory (would need actual backend implementation)
            this.stats.cpuUsage = Math.random() * 30 + 10; // Placeholder
            this.stats.memoryUsage = Math.random() * 40 + 20; // Placeholder
            
            this.updateUI();
        } catch (e) {
            console.error('Failed to fetch concurrency stats:', e);
        }
    }
    
    // ==================== WebSocket Integration ====================
    connectWebSocket(ws) {
        this.ws = ws;
        
        if (ws) {
            ws.addEventListener('message', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'concurrency-update') {
                        this.handleConcurrencyUpdate(data.data);
                    }
                    if (data.type === 'session-update') {
                        this.handleSessionUpdate(data.data);
                    }
                } catch (e) {
                    // Ignore parse errors
                }
            });
        }
    }
    
    handleConcurrencyUpdate(data) {
        if (data.stats) {
            this.stats = { ...this.stats, ...data.stats };
            this.updateUI();
        }
    }
    
    handleSessionUpdate(data) {
        if (data.action === 'add') {
            this.sessions.push(data.session);
        } else if (data.action === 'remove') {
            this.sessions = this.sessions.filter(s => s.sessionId !== data.sessionId);
        } else if (data.action === 'update') {
            const idx = this.sessions.findIndex(s => s.sessionId === data.session.sessionId);
            if (idx >= 0) {
                this.sessions[idx] = data.session;
            }
        }
        this.stats.activeSessions = this.sessions.filter(s => s.status === 'active').length;
        this.updateUI();
    }
    
    // ==================== UI Updates ====================
    updateUI() {
        this.updateIndicator();
        this.updateResourceCards();
        this.updateSessionsList();
        this.updateQueueMonitor();
    }
    
    updateIndicator() {
        // Sessions
        const sessionsValue = document.getElementById('indicator-sessions-value');
        const sessionsStat = document.getElementById('indicator-sessions');
        if (sessionsValue) {
            sessionsValue.textContent = this.stats.activeSessions;
        }
        if (sessionsStat) {
            const ratio = this.stats.activeSessions / this.limits.maxConcurrentSessions;
            sessionsStat.classList.remove('warning', 'critical');
            if (ratio >= this.options.criticalThreshold) {
                sessionsStat.classList.add('critical');
            } else if (ratio >= this.options.warningThreshold) {
                sessionsStat.classList.add('warning');
            }
        }
        
        // Tokens
        const tokensValue = document.getElementById('indicator-tokens-value');
        const tokensStat = document.getElementById('indicator-tokens');
        if (tokensValue) {
            const tokensK = Math.round(this.stats.tokenUsage / 1000);
            tokensValue.textContent = tokensK + 'K';
        }
        if (tokensStat) {
            const ratio = this.stats.tokenUsage / this.stats.tokenLimit;
            tokensStat.classList.remove('warning', 'critical');
            if (ratio >= this.options.criticalThreshold) {
                tokensStat.classList.add('critical');
            } else if (ratio >= this.options.warningThreshold) {
                tokensStat.classList.add('warning');
            }
        }
        
        // Queue
        const queueValue = document.getElementById('indicator-queue-value');
        const queueStat = document.getElementById('indicator-queue');
        if (queueValue) {
            queueValue.textContent = this.stats.queueLength;
        }
        if (queueStat) {
            const ratio = this.stats.queueLength / this.limits.maxQueueLength;
            queueStat.classList.remove('warning', 'critical');
            if (ratio >= this.options.criticalThreshold) {
                queueStat.classList.add('critical');
            } else if (ratio >= this.options.warningThreshold) {
                queueStat.classList.add('warning');
            }
        }
    }
    
    updateResourceCards() {
        // Sessions card
        const sessionsValue = document.getElementById('active-sessions-value');
        const sessionsBar = document.getElementById('sessions-bar-fill');
        if (sessionsValue) {
            sessionsValue.textContent = this.stats.activeSessions;
        }
        if (sessionsBar) {
            const ratio = this.stats.activeSessions / this.limits.maxConcurrentSessions;
            sessionsBar.style.width = `${Math.min(ratio * 100, 100)}%`;
            sessionsBar.className = 'resource-card-bar-fill ' + this.getStatusClass(ratio);
        }
        
        // Tokens card
        const tokensValue = document.getElementById('token-usage-value');
        const tokensBar = document.getElementById('tokens-bar-fill');
        if (tokensValue) {
            tokensValue.textContent = this.formatNumber(this.stats.tokenUsage);
        }
        if (tokensBar) {
            const ratio = this.stats.tokenUsage / this.stats.tokenLimit;
            tokensBar.style.width = `${Math.min(ratio * 100, 100)}%`;
            tokensBar.className = 'resource-card-bar-fill ' + this.getStatusClass(ratio);
        }
        
        // CPU card
        const cpuValue = document.getElementById('cpu-usage-value');
        const cpuBar = document.getElementById('cpu-bar-fill');
        if (cpuValue) {
            cpuValue.textContent = Math.round(this.stats.cpuUsage) + '%';
        }
        if (cpuBar) {
            cpuBar.style.width = `${this.stats.cpuUsage}%`;
            cpuBar.className = 'resource-card-bar-fill ' + this.getStatusClass(this.stats.cpuUsage / 100);
        }
        
        // Memory card
        const memoryValue = document.getElementById('memory-usage-value');
        const memoryBar = document.getElementById('memory-bar-fill');
        if (memoryValue) {
            memoryValue.textContent = Math.round(this.stats.memoryUsage) + '%';
        }
        if (memoryBar) {
            memoryBar.style.width = `${this.stats.memoryUsage}%`;
            memoryBar.className = 'resource-card-bar-fill ' + this.getStatusClass(this.stats.memoryUsage / 100);
        }
    }
    
    updateSessionsList() {
        const container = document.getElementById('sessions-list-container');
        const countEl = document.getElementById('sessions-list-count');
        
        if (countEl) {
            countEl.textContent = `${this.sessions.length} sessions`;
        }
        
        if (!container) return;
        
        if (this.sessions.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: var(--text-tertiary);">
                    No active sessions
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.sessions.map(s => `
            <div class="session-item" data-id="${s.sessionId}">
                <div class="session-status-indicator ${s.status}"></div>
                <div class="session-info">
                    <div class="session-name">${this.escapeHtml(s.sessionName || s.sessionId)}</div>
                    <div class="session-meta">
                        <span>${s.role || 'worker'}</span>
                        <span>${this.formatDuration(s.startTime)}</span>
                    </div>
                </div>
                <div class="session-provider">${this.escapeHtml(s.provider || 'unknown')}</div>
                <div class="session-actions">
                    <button class="session-action-btn" title="View Details" onclick="concurrencyControl.viewSession('${s.sessionId}')">👁️</button>
                    <button class="session-action-btn kill" title="Kill Session" onclick="concurrencyControl.killSession('${s.sessionId}')">❌</button>
                </div>
            </div>
        `).join('');
    }
    
    updateQueueMonitor() {
        const queueCount = document.getElementById('queue-count');
        const queueBar = document.getElementById('queue-bar-fill');
        
        if (queueCount) {
            queueCount.textContent = `${this.stats.queueLength} pending`;
            const ratio = this.stats.queueLength / this.limits.maxQueueLength;
            queueCount.classList.remove('warning', 'critical');
            if (ratio >= this.options.criticalThreshold) {
                queueCount.classList.add('critical');
            } else if (ratio >= this.options.warningThreshold) {
                queueCount.classList.add('warning');
            }
        }
        
        if (queueBar) {
            const ratio = this.stats.queueLength / this.limits.maxQueueLength;
            queueBar.style.width = `${Math.min(ratio * 100, 100)}%`;
            queueBar.className = 'queue-bar-fill ' + this.getStatusClass(ratio);
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
        const panel = document.getElementById('concurrency-panel');
        if (panel) {
            panel.classList.add('visible');
            this.panelVisible = true;
            this.fetchStats();
        }
    }
    
    hidePanel() {
        const panel = document.getElementById('concurrency-panel');
        if (panel) {
            panel.classList.remove('visible');
            this.panelVisible = false;
        }
    }
    
    // ==================== Actions ====================
    async viewSession(sessionId) {
        try {
            const resp = await fetch(`/api/sessions/${sessionId}`);
            if (resp.ok) {
                const session = await resp.json();
                console.log('Session details:', session);
                // Could show a modal with session details
                this.dispatchEvent('session-view', session);
            }
        } catch (e) {
            console.error('Failed to view session:', e);
        }
    }
    
    async killSession(sessionId) {
        if (!confirm('Are you sure you want to kill this session?')) return;
        
        try {
            const resp = await fetch(`/api/sessions/${sessionId}/kill`, {
                method: 'POST'
            });
            if (resp.ok) {
                this.sessions = this.sessions.filter(s => s.sessionId !== sessionId);
                this.updateUI();
                this.dispatchEvent('session-killed', { sessionId });
            }
        } catch (e) {
            console.error('Failed to kill session:', e);
        }
    }
    
    async saveLimits() {
        const limits = {
            maxConcurrentSessions: parseInt(document.getElementById('limit-max-sessions')?.value || 10),
            maxTokensPerSession: parseInt(document.getElementById('limit-max-tokens')?.value || 50000),
            maxQueueLength: parseInt(document.getElementById('limit-max-queue')?.value || 100),
            timeoutMinutes: parseInt(document.getElementById('limit-timeout')?.value || 30)
        };
        
        this.limits = limits;
        
        try {
            const resp = await fetch('/api/concurrency/limits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(limits)
            });
            if (resp.ok) {
                this.dispatchEvent('limits-saved', limits);
                alert('Limits saved successfully!');
            } else {
                alert('Failed to save limits');
            }
        } catch (e) {
            console.error('Failed to save limits:', e);
            // Still update local limits
            this.dispatchEvent('limits-saved', limits);
        }
    }
    
    // ==================== Helpers ====================
    getStatusClass(ratio) {
        if (ratio >= this.options.criticalThreshold) return 'critical';
        if (ratio >= this.options.warningThreshold) return 'warning';
        return 'normal';
    }
    
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
    
    formatDuration(startTime) {
        if (!startTime) return 'N/A';
        const start = new Date(startTime);
        const now = new Date();
        const diff = now - start;
        
        if (diff < 60000) return 'Just started';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ${Math.floor((diff % 3600000) / 60000)}m`;
        return `${Math.floor(diff / 86400000)}d`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    dispatchEvent(name, data = null) {
        const event = new CustomEvent(name, { detail: data });
        document.dispatchEvent(event);
    }
}

// Global instance
let concurrencyControl = null;

function initConcurrencyControl(options = {}) {
    concurrencyControl = new ConcurrencyControl(options);
    return concurrencyControl;
}

// No auto-init — initialized by index.html nav button click.
// Call initConcurrencyControl() manually to start.