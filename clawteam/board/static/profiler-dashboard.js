/**
 * Performance Profiler Dashboard - Shows performance metrics for ClawTeam
 * 
 * Features:
 * - System metrics (CPU, memory, threads)
 * - Recent operation profiles
 * - Latency statistics
 * 
 * @author ClawTeam
 */

class ProfilerDashboard {
    constructor(options = {}) {
        this.options = {
            updateInterval: 5000,
            maxProfiles: 10,
            maxLatencyOps: 5,
            ...options
        };

        this.data = {
            profiles: [],
            latencyStats: [],
            systemMetrics: {}
        };

        this.panelVisible = false;
        this.updateTimer = null;

        this.init();
    }

    init() {
        this.createStyles();
        this.createPanel();
        this.bindEvents();
        this.startUpdates();
    }

    createStyles() {
        if (document.getElementById('profiler-dashboard-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'profiler-dashboard-styles';
        styles.textContent = `
            .profiler-panel {
                position: fixed;
                bottom: 80px;
                right: 20px;
                width: 380px;
                max-height: 500px;
                background: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                z-index: 1000;
                display: none;
                flex-direction: column;
                overflow: hidden;
            }
            
            .profiler-panel.visible {
                display: flex;
            }
            
            .profiler-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: var(--bg-secondary);
                border-bottom: 1px solid var(--border-color);
            }
            
            .profiler-header h3 {
                margin: 0;
                font-size: 14px;
                color: var(--text-primary);
            }
            
            .profiler-close {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                font-size: 18px;
                padding: 4px;
            }
            
            .profiler-content {
                flex: 1;
                overflow-y: auto;
                padding: 12px;
            }
            
            .profiler-section {
                margin-bottom: 16px;
            }
            
            .profiler-section h4 {
                font-size: 11px;
                text-transform: uppercase;
                color: var(--text-secondary);
                margin: 0 0 8px 0;
            }
            
            .profiler-metrics {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }
            
            .profiler-metric {
                background: var(--bg-tertiary);
                padding: 8px 10px;
                border-radius: 6px;
            }
            
            .profiler-metric-label {
                font-size: 10px;
                color: var(--text-secondary);
            }
            
            .profiler-metric-value {
                font-size: 16px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .profiler-table {
                width: 100%;
                font-size: 11px;
                border-collapse: collapse;
            }
            
            .profiler-table th {
                text-align: left;
                padding: 4px 8px;
                color: var(--text-secondary);
                border-bottom: 1px solid var(--border-color);
            }
            
            .profiler-table td {
                padding: 4px 8px;
                color: var(--text-primary);
            }
            
            .profiler-table tr:hover {
                background: var(--bg-tertiary);
            }
            
            .profiler-latency {
                background: var(--bg-tertiary);
                padding: 8px;
                border-radius: 6px;
                margin-bottom: 6px;
            }
            
            .profiler-latency-name {
                font-weight: 600;
                font-size: 12px;
                color: var(--text-primary);
            }
            
            .profiler-latency-stats {
                display: flex;
                gap: 12px;
                font-size: 10px;
                color: var(--text-secondary);
                margin-top: 4px;
            }
            
            .profiler-mini-btn {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-primary);
                font-size: 12px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .profiler-mini-btn:hover {
                background: var(--bg-secondary);
                border-color: var(--primary);
            }
            
            .profiler-empty {
                text-align: center;
                padding: 20px;
                color: var(--text-secondary);
                font-size: 12px;
            }
        `;
        document.head.appendChild(styles);
    }

    createPanel() {
        if (document.getElementById('profiler-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'profiler-panel';
        panel.className = 'profiler-panel';
        panel.innerHTML = `
            <div class="profiler-header">
                <h3>⚡ Performance</h3>
                <button class="profiler-close" onclick="toggleProfilerPanel()">&times;</button>
            </div>
            <div class="profiler-content" id="profiler-content">
                <div class="profiler-empty">Loading profiler data...</div>
            </div>
        `;
        document.body.appendChild(panel);
    }

    createMiniButton() {
        if (document.getElementById('profiler-mini-btn')) return;

        const btn = document.createElement('button');
        btn.id = 'profiler-mini-btn';
        btn.className = 'profiler-mini-btn';
        btn.onclick = () => toggleProfilerPanel();
        btn.innerHTML = '⚡';
        btn.title = 'Performance Profiler';

        // Add to topbar-right if it exists
        const topbarRight = document.querySelector('.topbar-right');
        if (topbarRight) {
            topbarRight.appendChild(btn);
        } else {
            // Fallback: add to body
            document.body.appendChild(btn);
        }
    }

    bindEvents() {
        // ESC to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const panel = document.getElementById('profiler-panel');
                if (panel) panel.classList.remove('visible');
            }
        });
    }

    startUpdates() {
        this.fetchData();
        this.updateTimer = setInterval(() => this.fetchData(), this.options.updateInterval);
    }

    stopUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    async fetchData() {
        try {
            const resp = await fetch('/api/profiler/stats');
            if (!resp.ok) throw new Error('Failed to fetch profiler stats');
            this.data = await resp.json();
            this.render();
        } catch (e) {
            console.error('Profiler fetch error:', e);
        }
    }

    render() {
        const content = document.getElementById('profiler-content');
        if (!content) return;

        const { profiles, latency_stats, system_metrics, total_profiles, total_operations } = this.data;

        let html = '';

        // System Metrics
        if (system_metrics && Object.keys(system_metrics).length > 0) {
            html += `
                <div class="profiler-section">
                    <h4>System</h4>
                    <div class="profiler-metrics">
                        <div class="profiler-metric">
                            <div class="profiler-metric-label">CPU</div>
                            <div class="profiler-metric-value">${system_metrics.cpu_percent || 0}%</div>
                        </div>
                        <div class="profiler-metric">
                            <div class="profiler-metric-label">Memory</div>
                            <div class="profiler-metric-value">${system_metrics.memory_mb || 0} MB</div>
                        </div>
                        <div class="profiler-metric">
                            <div class="profiler-metric-label">Threads</div>
                            <div class="profiler-metric-value">${system_metrics.threads || 0}</div>
                        </div>
                        <div class="profiler-metric">
                            <div class="profiler-metric-label">Files</div>
                            <div class="profiler-metric-value">${system_metrics.open_files || 0}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Summary
        html += `
            <div class="profiler-section">
                <h4>Summary</h4>
                <div class="profiler-metrics">
                    <div class="profiler-metric">
                        <div class="profiler-metric-label">Profiles</div>
                        <div class="profiler-metric-value">${total_profiles || 0}</div>
                    </div>
                    <div class="profiler-metric">
                        <div class="profiler-metric-label">Operations</div>
                        <div class="profiler-metric-value">${total_operations || 0}</div>
                    </div>
                </div>
            </div>
        `;

        // Latency Stats
        if (latency_stats && latency_stats.length > 0) {
            html += `<div class="profiler-section"><h4>Latency</h4>`;
            latency_stats.slice(0, this.options.maxLatencyOps).forEach(ls => {
                html += `
                    <div class="profiler-latency">
                        <div class="profiler-latency-name">${ls.operation}</div>
                        <div class="profiler-latency-stats">
                            <span>avg: ${ls.avg_ms}ms</span>
                            <span>p95: ${ls.p95_ms}ms</span>
                            <span>count: ${ls.count}</span>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        // Recent Profiles
        if (profiles && profiles.length > 0) {
            html += `
                <div class="profiler-section">
                    <h4>Recent Profiles</h4>
                    <table class="profiler-table">
                        <thead>
                            <tr>
                                <th>Operation</th>
                                <th>Time</th>
                                <th>Memory</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${profiles.slice(0, this.options.maxProfiles).map(p => `
                                <tr>
                                    <td>${p.name}</td>
                                    <td>${p.duration_ms}ms</td>
                                    <td>${p.memory_mb} MB</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        if (!html) {
            html = '<div class="profiler-empty">No profiler data yet.<br><small>Profiles will appear as operations run.</small></div>';
        }

        content.innerHTML = html;
    }
}

// Global instance
let profilerDashboard = null;

// Toggle panel visibility
function toggleProfilerPanel() {
    const panel = document.getElementById('profiler-panel');
    if (!panel) return;

    if (panel.classList.contains('visible')) {
        panel.classList.remove('visible');
    } else {
        panel.classList.add('visible');
        if (!profilerDashboard) {
            profilerDashboard = new ProfilerDashboard();
        }
    }
}

// Auto-init when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Create the mini button
    setTimeout(() => {
        if (!profilerDashboard) {
            profilerDashboard = new ProfilerDashboard();
        }
        profilerDashboard.createMiniButton();
    }, 1000);
});

// Export for manual init
window.ProfilerDashboard = ProfilerDashboard;
window.toggleProfilerPanel = toggleProfilerPanel;
