/**
 * Notifications Manager - Real-time notification system for ClawTeam Web UI
 * 
 * Features:
 * - Real-time push via WebSocket
 * - Notification panel UI
 * - Do-not-disturb mode
 * - Notification history
 * - Sound alerts (optional)
 * 
 * @author ClawTeam Frontend
 */

class NotificationsManager {
    constructor(options = {}) {
        this.options = {
            maxNotifications: 100,
            soundEnabled: true,
            autoHideDelay: 5000,
            position: 'top-right', // top-right, top-left, bottom-right, bottom-left
            ...options
        };
        
        this.notifications = [];
        this.unreadCount = 0;
        this.dndMode = false;
        this.panelVisible = false;
        this.ws = null;
        
        this.init();
    }
    
    init() {
        this.createStyles();
        this.createPanel();
        this.createToastContainer();
        this.bindEvents();
    }
    
    // ==================== Styles ====================
    createStyles() {
        if (document.getElementById('notifications-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'notifications-styles';
        styles.textContent = `
            /* Notification Toast Container */
            .notification-toast-container {
                position: fixed;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 8px;
                padding: 16px;
                max-width: 400px;
                pointer-events: none;
            }
            
            .notification-toast-container.top-right {
                top: 0;
                right: 0;
            }
            .notification-toast-container.top-left {
                top: 0;
                left: 0;
            }
            .notification-toast-container.bottom-right {
                bottom: 0;
                right: 0;
            }
            .notification-toast-container.bottom-left {
                bottom: 0;
                left: 0;
            }
            
            /* Notification Toast */
            .notification-toast {
                background: var(--surface-color);
                backdrop-filter: var(--blur);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-md);
                padding: 12px 16px;
                display: flex;
                align-items: flex-start;
                gap: 12px;
                pointer-events: auto;
                animation: notification-slide-in 0.3s ease;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                max-width: 380px;
            }
            
            .notification-toast.hiding {
                animation: notification-slide-out 0.3s ease forwards;
            }
            
            .notification-toast-icon {
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }
            
            .notification-toast-icon.info { color: var(--color-progress); }
            .notification-toast-icon.success { color: var(--color-completed); }
            .notification-toast-icon.warning { color: var(--color-pending); }
            .notification-toast-icon.error { color: var(--color-blocked); }
            .notification-toast-icon.alert { color: var(--color-broadcast); }
            
            .notification-toast-content {
                flex: 1;
                min-width: 0;
            }
            
            .notification-toast-title {
                font-weight: 600;
                font-size: 14px;
                color: var(--text-primary);
                margin-bottom: 4px;
            }
            
            .notification-toast-message {
                font-size: 13px;
                color: var(--text-secondary);
                line-height: 1.4;
            }
            
            .notification-toast-time {
                font-size: 11px;
                color: var(--text-tertiary);
                margin-top: 4px;
            }
            
            .notification-toast-close {
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: var(--text-tertiary);
                border-radius: 4px;
                transition: all 0.2s;
            }
            
            .notification-toast-close:hover {
                background: var(--surface-hover);
                color: var(--text-primary);
            }
            
            @keyframes notification-slide-in {
                from {
                    opacity: 0;
                    transform: translateX(100%);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes notification-slide-out {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100%);
                }
            }
            
            /* Notification Panel */
            .notification-panel {
                position: fixed;
                top: 60px;
                right: 16px;
                width: 380px;
                max-height: 70vh;
                background: var(--surface-color);
                backdrop-filter: var(--blur);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-lg);
                box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
                z-index: 1000;
                display: none;
                overflow: hidden;
            }
            
            .notification-panel.visible {
                display: block;
                animation: panel-fade-in 0.2s ease;
            }
            
            @keyframes panel-fade-in {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .notification-panel-header {
                padding: 16px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .notification-panel-title {
                font-weight: 600;
                font-size: 16px;
                color: var(--text-primary);
            }
            
            .notification-panel-actions {
                display: flex;
                gap: 8px;
            }
            
            .notification-panel-btn {
                padding: 6px 12px;
                font-size: 12px;
                border-radius: var(--radius-sm);
                background: var(--surface-hover);
                color: var(--text-secondary);
                cursor: pointer;
                transition: all 0.2s;
                border: none;
            }
            
            .notification-panel-btn:hover {
                background: var(--surface-active);
                color: var(--text-primary);
            }
            
            .notification-panel-btn.dnd-active {
                background: var(--color-broadcast);
                color: white;
            }
            
            .notification-panel-body {
                max-height: calc(70vh - 120px);
                overflow-y: auto;
            }
            
            .notification-list {
                padding: 8px;
            }
            
            .notification-item {
                padding: 12px;
                border-radius: var(--radius-sm);
                background: var(--surface-hover);
                margin-bottom: 8px;
                cursor: pointer;
                transition: all 0.2s;
                border-left: 3px solid transparent;
            }
            
            .notification-item:hover {
                background: var(--surface-active);
            }
            
            .notification-item.unread {
                border-left-color: var(--color-progress);
            }
            
            .notification-item-header {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 6px;
            }
            
            .notification-item-icon {
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }
            
            .notification-item-icon.info { color: var(--color-progress); }
            .notification-item-icon.success { color: var(--color-completed); }
            .notification-item-icon.warning { color: var(--color-pending); }
            .notification-item-icon.error { color: var(--color-blocked); }
            .notification-item-icon.alert { color: var(--color-broadcast); }
            
            .notification-item-title {
                font-weight: 500;
                font-size: 14px;
                color: var(--text-primary);
                flex: 1;
            }
            
            .notification-item-time {
                font-size: 11px;
                color: var(--text-tertiary);
            }
            
            .notification-item-message {
                font-size: 13px;
                color: var(--text-secondary);
                line-height: 1.4;
            }
            
            .notification-item-source {
                font-size: 11px;
                color: var(--text-tertiary);
                margin-top: 4px;
            }
            
            .notification-empty {
                padding: 40px;
                text-align: center;
                color: var(--text-tertiary);
            }
            
            .notification-empty-icon {
                font-size: 48px;
                margin-bottom: 12px;
                opacity: 0.5;
            }
            
            /* Notification Badge */
            .notification-badge {
                position: absolute;
                top: -4px;
                right: -4px;
                min-width: 18px;
                height: 18px;
                background: var(--color-blocked);
                color: white;
                font-size: 11px;
                font-weight: 600;
                border-radius: 9px;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0 4px;
            }
            
            .notification-badge.hidden {
                display: none;
            }
            
            /* Mobile Responsive */
            @media (max-width: 480px) {
                .notification-panel {
                    width: calc(100vw - 32px);
                    right: 16px;
                    left: 16px;
                }
                
                .notification-toast-container {
                    max-width: calc(100vw - 32px);
                }
                
                .notification-toast {
                    max-width: 100%;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // ==================== Panel ====================
    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'notification-panel';
        panel.id = 'notification-panel';
        panel.innerHTML = `
            <div class="notification-panel-header">
                <div class="notification-panel-title">
                    <span>🔔</span> Notifications
                    <span class="notification-badge" id="notification-unread-badge">0</span>
                </div>
                <div class="notification-panel-actions">
                    <button class="notification-panel-btn" id="notification-dnd-btn" title="Do Not Disturb">
                        🌙 DND
                    </button>
                    <button class="notification-panel-btn" id="notification-clear-btn" title="Clear All">
                        🗑️ Clear
                    </button>
                    <button class="notification-panel-btn" id="notification-close-btn" title="Close">
                        ✕
                    </button>
                </div>
            </div>
            <div class="notification-panel-body">
                <div class="notification-list" id="notification-list"></div>
            </div>
        `;
        document.body.appendChild(panel);
        
        // Create notification bell button in header
        this.createNotificationBell();
    }
    
    createNotificationBell() {
        // Find existing header or create one
        const header = document.querySelector('.header') || document.querySelector('.topbar');
        if (!header) return;
        
        const bellContainer = document.createElement('div');
        bellContainer.className = 'notification-bell-container';
        bellContainer.style.cssText = `
            position: relative;
            cursor: pointer;
            padding: 8px;
            border-radius: var(--radius-sm);
            transition: all 0.2s;
        `;
        bellContainer.innerHTML = `
            <span style="font-size: 20px;">🔔</span>
            <span class="notification-badge" id="header-notification-badge">0</span>
        `;
        bellContainer.onclick = () => this.togglePanel();
        
        // Insert into header
        const existingBell = header.querySelector('.notification-bell-container');
        if (existingBell) {
            existingBell.replaceWith(bellContainer);
        } else {
            header.appendChild(bellContainer);
        }
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.className = `notification-toast-container ${this.options.position}`;
        container.id = 'notification-toast-container';
        document.body.appendChild(container);
    }
    
    // ==================== Events ====================
    bindEvents() {
        // DND button
        document.getElementById('notification-dnd-btn')?.addEventListener('click', () => {
            this.toggleDND();
        });
        
        // Clear button
        document.getElementById('notification-clear-btn')?.addEventListener('click', () => {
            this.clearAll();
        });
        
        // Close button
        document.getElementById('notification-close-btn')?.addEventListener('click', () => {
            this.hidePanel();
        });
        
        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notification-panel');
            const bell = document.querySelector('.notification-bell-container');
            if (this.panelVisible && 
                panel && !panel.contains(e.target) && 
                bell && !bell.contains(e.target)) {
                this.hidePanel();
            }
        });
        
        // Keyboard shortcut: Escape to close panel
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.panelVisible) {
                this.hidePanel();
            }
        });
    }
    
    // ==================== WebSocket Integration ====================
    connectWebSocket(ws) {
        this.ws = ws;
        
        // Listen for notification messages
        if (ws) {
            ws.addEventListener('message', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'notification') {
                        this.handleNotification(data.data);
                    }
                } catch (e) {
                    // Ignore parse errors
                }
            });
        }
    }
    
    handleNotification(data) {
        const notification = {
            id: data.id || Date.now().toString(),
            type: data.type || 'info',
            title: data.title || 'Notification',
            message: data.message || '',
            source: data.source || 'system',
            timestamp: data.timestamp || new Date().toISOString(),
            severity: data.severity || 'medium',
            details: data.details || null,
            read: false
        };
        
        this.addNotification(notification);
    }
    
    // ==================== Public API ====================
    addNotification(notification) {
        // Add to list
        this.notifications.unshift(notification);
        
        // Limit max notifications
        if (this.notifications.length > this.options.maxNotifications) {
            this.notifications = this.notifications.slice(0, this.options.maxNotifications);
        }
        
        // Update unread count
        if (!notification.read) {
            this.unreadCount++;
            this.updateBadge();
        }
        
        // Show toast (unless DND mode)
        if (!this.dndMode) {
            this.showToast(notification);
            
            // Play sound (if enabled)
            if (this.options.soundEnabled && notification.severity !== 'low') {
                this.playSound(notification.type);
            }
        }
        
        // Update panel list
        this.updatePanelList();
        
        // Dispatch event
        this.dispatchEvent('notification-added', notification);
    }
    
    showToast(notification) {
        const container = document.getElementById('notification-toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.dataset.id = notification.id;
        
        const iconMap = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            alert: '🚨'
        };
        
        toast.innerHTML = `
            <div class="notification-toast-icon ${notification.type}">${iconMap[notification.type] || 'ℹ️'}</div>
            <div class="notification-toast-content">
                <div class="notification-toast-title">${this.escapeHtml(notification.title)}</div>
                <div class="notification-toast-message">${this.escapeHtml(notification.message)}</div>
                <div class="notification-toast-time">${this.formatTime(notification.timestamp)}</div>
            </div>
            <div class="notification-toast-close" onclick="notificationsManager.closeToast('${notification.id}')">✕</div>
        `;
        
        container.appendChild(toast);
        
        // Auto hide
        if (this.options.autoHideDelay > 0) {
            setTimeout(() => {
                this.hideToast(notification.id);
            }, this.options.autoHideDelay);
        }
        
        // Click to dismiss
        toast.addEventListener('click', (e) => {
            if (!e.target.classList.contains('notification-toast-close')) {
                this.hideToast(notification.id);
                this.markAsRead(notification.id);
            }
        });
    }
    
    hideToast(id) {
        const toast = document.querySelector(`.notification-toast[data-id="${id}"]`);
        if (toast) {
            toast.classList.add('hiding');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
    }
    
    closeToast(id) {
        this.hideToast(id);
        this.markAsRead(id);
    }
    
    markAsRead(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification && !notification.read) {
            notification.read = true;
            this.unreadCount--;
            this.updateBadge();
            this.updatePanelList();
            this.dispatchEvent('notification-read', notification);
        }
    }
    
    markAllAsRead() {
        this.notifications.forEach(n => {
            if (!n.read) {
                n.read = true;
            }
        });
        this.unreadCount = 0;
        this.updateBadge();
        this.updatePanelList();
        this.dispatchEvent('notifications-all-read');
    }
    
    clearAll() {
        this.notifications = [];
        this.unreadCount = 0;
        this.updateBadge();
        this.updatePanelList();
        
        // Clear all toasts
        const container = document.getElementById('notification-toast-container');
        if (container) {
            container.innerHTML = '';
        }
        
        this.dispatchEvent('notifications-clear');
    }
    
    togglePanel() {
        if (this.panelVisible) {
            this.hidePanel();
        } else {
            this.showPanel();
        }
    }
    
    showPanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.add('visible');
            this.panelVisible = true;
            this.updatePanelList();
        }
    }
    
    hidePanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.remove('visible');
            this.panelVisible = false;
        }
    }
    
    toggleDND() {
        this.dndMode = !this.dndMode;
        
        const btn = document.getElementById('notification-dnd-btn');
        if (btn) {
            btn.classList.toggle('dnd-active', this.dndMode);
            btn.textContent = this.dndMode ? '🌙 DND ON' : '🌙 DND';
        }
        
        this.dispatchEvent('dnd-toggle', { enabled: this.dndMode });
    }
    
    setDND(enabled) {
        this.dndMode = enabled;
        
        const btn = document.getElementById('notification-dnd-btn');
        if (btn) {
            btn.classList.toggle('dnd-active', this.dndMode);
            btn.textContent = this.dndMode ? '🌙 DND ON' : '🌙 DND';
        }
    }
    
    // ==================== Updates ====================
    updateBadge() {
        const badges = [
            document.getElementById('header-notification-badge'),
            document.getElementById('notification-unread-badge')
        ];
        
        badges.forEach(badge => {
            if (badge) {
                if (this.unreadCount > 0) {
                    badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            }
        });
    }
    
    updatePanelList() {
        const list = document.getElementById('notification-list');
        if (!list) return;
        
        if (this.notifications.length === 0) {
            list.innerHTML = `
                <div class="notification-empty">
                    <div class="notification-empty-icon">📭</div>
                    <div>No notifications</div>
                </div>
            `;
            return;
        }
        
        const iconMap = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            alert: '🚨'
        };
        
        list.innerHTML = this.notifications.map(n => `
            <div class="notification-item ${n.read ? '' : 'unread'}" data-id="${n.id}" onclick="notificationsManager.onItemClick('${n.id}')">
                <div class="notification-item-header">
                    <div class="notification-item-icon ${n.type}">${iconMap[n.type] || 'ℹ️'}</div>
                    <div class="notification-item-title">${this.escapeHtml(n.title)}</div>
                    <div class="notification-item-time">${this.formatTime(n.timestamp)}</div>
                </div>
                <div class="notification-item-message">${this.escapeHtml(n.message)}</div>
                ${n.source ? `<div class="notification-item-source">Source: ${this.escapeHtml(n.source)}</div>` : ''}
            </div>
        `).join('');
    }
    
    onItemClick(id) {
        this.markAsRead(id);
        const notification = this.notifications.find(n => n.id === id);
        if (notification) {
            this.dispatchEvent('notification-click', notification);
        }
    }
    
    // ==================== Helpers ====================
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // < 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // < 1 hour
            return `${Math.floor(diff / 60000)}m ago`;
        } else if (diff < 86400000) { // < 24 hours
            return `${Math.floor(diff / 3600000)}h ago`;
        } else if (diff < 604800000) { // < 7 days
            return `${Math.floor(diff / 86400000)}d ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    playSound(type) {
        // Simple beep using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Different tones for different types
            const frequencies = {
                info: 800,
                success: 600,
                warning: 1000,
                error: 400,
                alert: 1200
            };
            
            oscillator.frequency.value = frequencies[type] || 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (e) {
            // Ignore audio errors
        }
    }
    
    dispatchEvent(name, data = null) {
        const event = new CustomEvent(name, { detail: data });
        document.dispatchEvent(event);
    }
    
    // ==================== API Fetch ====================
    async fetchNotifications(teamName) {
        try {
            const resp = await fetch(`/api/teams/${teamName}/alerts`);
            if (resp.ok) {
                const alerts = await resp.json();
                alerts.forEach(alert => {
                    this.handleNotification({
                        id: alert.alert_id,
                        type: this.mapAlertType(alert.event_type),
                        title: this.formatAlertTitle(alert.event_type),
                        message: alert.message,
                        source: alert.source,
                        timestamp: alert.timestamp,
                        severity: alert.severity,
                        details: alert.details
                    });
                });
            }
        } catch (e) {
            console.error('Failed to fetch notifications:', e);
        }
    }
    
    mapAlertType(eventType) {
        const typeMap = {
            'task_timeout': 'warning',
            'agent_failure_rate_high': 'error',
            'team_inactivity': 'warning',
            'resource_exhaustion': 'error',
            'configuration_error': 'error'
        };
        return typeMap[eventType] || 'info';
    }
    
    formatAlertTitle(eventType) {
        const titleMap = {
            'task_timeout': 'Task Timeout',
            'agent_failure_rate_high': 'High Failure Rate',
            'team_inactivity': 'Team Inactivity',
            'resource_exhaustion': 'Resource Exhaustion',
            'configuration_error': 'Configuration Error'
        };
        return titleMap[eventType] || 'Alert';
    }
    
    // ==================== Manual Notification ====================
    notify(type, title, message, options = {}) {
        this.addNotification({
            id: options.id || Date.now().toString(),
            type: type,
            title: title,
            message: message,
            source: options.source || 'manual',
            timestamp: options.timestamp || new Date().toISOString(),
            severity: options.severity || 'medium',
            details: options.details || null,
            read: false
        });
    }
    
    info(title, message, options = {}) {
        this.notify('info', title, message, options);
    }
    
    success(title, message, options = {}) {
        this.notify('success', title, message, options);
    }
    
    warning(title, message, options = {}) {
        this.notify('warning', title, message, { ...options, severity: 'high' });
    }
    
    error(title, message, options = {}) {
        this.notify('error', title, message, { ...options, severity: 'critical' });
    }
    
    alert(title, message, options = {}) {
        this.notify('alert', title, message, { ...options, severity: 'critical' });
    }
}

// Global instance
let notificationsManager = null;

function initNotificationsManager(options = {}) {
    notificationsManager = new NotificationsManager(options);
    return notificationsManager;
}

// Auto-initialize (reliable for scripts loaded at end of body)
(function() {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        // DOM is already ready, init after current execution
        requestAnimationFrame(() => initNotificationsManager());
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            initNotificationsManager();
        });
    }
})();