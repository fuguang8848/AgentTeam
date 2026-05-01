/**
 * Skills Manager - Skill management interface for ClawTeam Web UI
 * 
 * Features:
 * - Skill list display with categories
 * - Skill variable form (dynamic inputs)
 * - Skill execution history
 * - Skill search and filtering
 * - Execute skills with parameters
 * 
 * @author ClawTeam Frontend
 */

class SkillsManager {
    constructor(options = {}) {
        this.options = {
            apiBase: '/api/skills',
            ...options
        };
        
        this.skills = [];
        this.categories = [];
        this.executionHistory = [];
        this.selectedSkill = null;
        this.panelVisible = false;
        
        this.init();
    }
    
    init() {
        this.createStyles();
        this.createPanel();
        this.createSkillButton();
        this.bindEvents();
        this.fetchSkills();
    }
    
    // ==================== Styles ====================
    createStyles() {
        if (document.getElementById('skills-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'skills-styles';
        styles.textContent = `
            /* Skills Button (Header) */
            .skills-button {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: var(--surface-color);
                border-radius: var(--radius-sm);
                border: 1px solid var(--border-color);
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .skills-button:hover {
                background: var(--surface-hover);
            }
            
            .skills-button-icon {
                font-size: 18px;
            }
            
            .skills-button-text {
                font-size: 14px;
                color: var(--text-primary);
            }
            
            /* Skills Panel */
            .skills-panel {
                position: fixed;
                top: 60px;
                right: 16px;
                width: 500px;
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
            
            .skills-panel.visible {
                display: block;
                animation: panel-fade-in 0.2s ease;
            }
            
            .skills-panel-header {
                padding: 16px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .skills-panel-title {
                font-weight: 600;
                font-size: 16px;
                color: var(--text-primary);
            }
            
            .skills-panel-close {
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
            
            .skills-panel-close:hover {
                background: var(--surface-hover);
                color: var(--text-primary);
            }
            
            .skills-panel-body {
                display: flex;
                height: calc(85vh - 60px);
            }
            
            /* Skills List (Left Side) */
            .skills-list-section {
                width: 200px;
                border-right: 1px solid var(--border-color);
                overflow-y: auto;
                padding: 12px;
            }
            
            .skills-search {
                width: 100%;
                padding: 8px 12px;
                background: var(--surface-hover);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-sm);
                color: var(--text-primary);
                font-size: 13px;
                margin-bottom: 12px;
            }
            
            .skills-search:focus {
                outline: none;
                border-color: var(--color-progress);
            }
            
            .skills-category {
                margin-bottom: 12px;
            }
            
            .skills-category-title {
                font-size: 12px;
                font-weight: 600;
                color: var(--text-tertiary);
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .skills-category-count {
                font-size: 11px;
                color: var(--text-tertiary);
            }
            
            .skill-item {
                padding: 8px 12px;
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                margin-bottom: 4px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .skill-item:hover {
                background: var(--surface-active);
            }
            
            .skill-item.active {
                background: var(--color-progress);
                color: white;
            }
            
            .skill-item-icon {
                font-size: 14px;
            }
            
            .skill-item-name {
                font-size: 13px;
                flex: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            /* Skill Detail (Right Side) */
            .skill-detail-section {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
            }
            
            .skill-detail-empty {
                text-align: center;
                padding: 40px;
                color: var(--text-tertiary);
            }
            
            .skill-detail-empty-icon {
                font-size: 48px;
                margin-bottom: 12px;
                opacity: 0.5;
            }
            
            .skill-detail-header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
            }
            
            .skill-detail-icon {
                width: 48px;
                height: 48px;
                background: var(--surface-hover);
                border-radius: var(--radius-md);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }
            
            .skill-detail-info {
                flex: 1;
            }
            
            .skill-detail-name {
                font-size: 18px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .skill-detail-category {
                font-size: 12px;
                color: var(--text-tertiary);
            }
            
            .skill-detail-command {
                font-size: 13px;
                color: var(--color-progress);
                background: var(--surface-hover);
                padding: 4px 8px;
                border-radius: 4px;
                margin-top: 4px;
            }
            
            .skill-detail-description {
                font-size: 14px;
                color: var(--text-secondary);
                line-height: 1.5;
                margin-bottom: 16px;
            }
            
            /* Skill Variables Form */
            .skill-variables-section {
                margin-bottom: 16px;
            }
            
            .skill-variables-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 12px;
            }
            
            .skill-variable-item {
                margin-bottom: 12px;
            }
            
            .skill-variable-label {
                font-size: 13px;
                color: var(--text-primary);
                margin-bottom: 4px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .skill-variable-required {
                color: var(--color-blocked);
                font-size: 11px;
            }
            
            .skill-variable-input {
                width: 100%;
                padding: 10px 12px;
                background: var(--surface-hover);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-sm);
                color: var(--text-primary);
                font-size: 14px;
            }
            
            .skill-variable-input:focus {
                outline: none;
                border-color: var(--color-progress);
            }
            
            .skill-variable-input.textarea {
                min-height: 80px;
                resize: vertical;
            }
            
            .skill-variable-input.select {
                cursor: pointer;
            }
            
            .skill-variable-hint {
                font-size: 11px;
                color: var(--text-tertiary);
                margin-top: 4px;
            }
            
            /* Execute Button */
            .skill-execute-section {
                margin-top: 20px;
                padding-top: 16px;
                border-top: 1px solid var(--border-color);
            }
            
            .skill-execute-btn {
                width: 100%;
                padding: 12px;
                background: var(--color-progress);
                color: white;
                border-radius: var(--radius-sm);
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }
            
            .skill-execute-btn:hover {
                background: #2563eb;
            }
            
            .skill-execute-btn:disabled {
                background: var(--text-tertiary);
                cursor: not-allowed;
            }
            
            .skill-execute-btn.loading {
                opacity: 0.7;
            }
            
            /* Execution History */
            .skill-history-section {
                margin-top: 20px;
            }
            
            .skill-history-title {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .skill-history-clear {
                font-size: 12px;
                color: var(--text-tertiary);
                cursor: pointer;
            }
            
            .skill-history-list {
                max-height: 200px;
                overflow-y: auto;
            }
            
            .skill-history-item {
                padding: 10px 12px;
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                margin-bottom: 6px;
            }
            
            .skill-history-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 6px;
            }
            
            .skill-history-name {
                font-size: 13px;
                font-weight: 500;
                color: var(--text-primary);
            }
            
            .skill-history-time {
                font-size: 11px;
                color: var(--text-tertiary);
            }
            
            .skill-history-status {
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .skill-history-status.success {
                color: var(--color-completed);
            }
            
            .skill-history-status.error {
                color: var(--color-blocked);
            }
            
            .skill-history-status.running {
                color: var(--color-progress);
            }
            
            /* Execution Result Modal */
            .skill-result-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: var(--modal-overlay);
                z-index: 2000;
                display: none;
                align-items: center;
                justify-content: center;
            }
            
            .skill-result-modal.visible {
                display: flex;
            }
            
            .skill-result-content {
                width: 600px;
                max-height: 80vh;
                background: var(--surface-color);
                border-radius: var(--radius-lg);
                overflow: hidden;
            }
            
            .skill-result-header {
                padding: 16px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .skill-result-title {
                font-size: 16px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .skill-result-body {
                padding: 16px;
                max-height: calc(80vh - 120px);
                overflow-y: auto;
            }
            
            .skill-result-output {
                background: var(--surface-hover);
                border-radius: var(--radius-sm);
                padding: 12px;
                font-size: 13px;
                color: var(--text-secondary);
                white-space: pre-wrap;
                word-break: break-word;
            }
            
            .skill-result-footer {
                padding: 16px;
                border-top: 1px solid var(--border-color);
                display: flex;
                justify-content: flex-end;
            }
            
            .skill-result-close-btn {
                padding: 8px 16px;
                background: var(--surface-hover);
                color: var(--text-primary);
                border-radius: var(--radius-sm);
                cursor: pointer;
                border: none;
            }
            
            /* Mobile Responsive */
            @media (max-width: 540px) {
                .skills-panel {
                    width: calc(100vw - 32px);
                    right: 16px;
                    left: 16px;
                }
                
                .skills-panel-body {
                    flex-direction: column;
                }
                
                .skills-list-section {
                    width: 100%;
                    border-right: none;
                    border-bottom: 1px solid var(--border-color);
                    max-height: 200px;
                }
                
                .skill-detail-section {
                    max-height: calc(85vh - 260px);
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // ==================== Panel ====================
    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'skills-panel';
        panel.id = 'skills-panel';
        panel.innerHTML = `
            <div class="skills-panel-header">
                <div class="skills-panel-title">⚡ Skills Manager</div>
                <div class="skills-panel-close" onclick="skillsManager.hidePanel()">✕</div>
            </div>
            <div class="skills-panel-body">
                <!-- Skills List -->
                <div class="skills-list-section">
                    <input type="text" class="skills-search" id="skills-search" placeholder="Search skills..." oninput="skillsManager.filterSkills(this.value)">
                    <div id="skills-list-container"></div>
                </div>
                
                <!-- Skill Detail -->
                <div class="skill-detail-section" id="skill-detail-section">
                    <div class="skill-detail-empty">
                        <div class="skill-detail-empty-icon">⚡</div>
                        <div>Select a skill to view details</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
        
        // Create result modal
        this.createResultModal();
    }
    
    createResultModal() {
        const modal = document.createElement('div');
        modal.className = 'skill-result-modal';
        modal.id = 'skill-result-modal';
        modal.innerHTML = `
            <div class="skill-result-content">
                <div class="skill-result-header">
                    <div class="skill-result-title" id="skill-result-title">Skill Result</div>
                    <div class="skills-panel-close" onclick="skillsManager.hideResultModal()">✕</div>
                </div>
                <div class="skill-result-body">
                    <div class="skill-result-output" id="skill-result-output"></div>
                </div>
                <div class="skill-result-footer">
                    <button class="skill-result-close-btn" onclick="skillsManager.hideResultModal()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideResultModal();
            }
        });
    }
    
    createSkillButton() {
        const header = document.querySelector('.header') || document.querySelector('.topbar');
        if (!header) return;
        
        const btn = document.createElement('div');
        btn.className = 'skills-button';
        btn.id = 'skills-button';
        btn.onclick = () => this.togglePanel();
        btn.innerHTML = `
            <span class="skills-button-icon">⚡</span>
            <span class="skills-button-text">Skills</span>
        `;
        
        const existingBtn = header.querySelector('.skills-button');
        if (existingBtn) {
            existingBtn.replaceWith(btn);
        } else {
            header.appendChild(btn);
        }
    }
    
    // ==================== Events ====================
    bindEvents() {
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('skills-panel');
            const btn = document.getElementById('skills-button');
            if (this.panelVisible && 
                panel && !panel.contains(e.target) && 
                btn && !btn.contains(e.target)) {
                this.hidePanel();
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (document.getElementById('skill-result-modal')?.classList.contains('visible')) {
                    this.hideResultModal();
                } else if (this.panelVisible) {
                    this.hidePanel();
                }
            }
        });
    }
    
    // ==================== Data ====================
    async fetchSkills() {
        try {
            const resp = await fetch(this.options.apiBase);
            if (resp.ok) {
                const data = await resp.json();
                this.skills = data.skills || data;
                this.categories = this.extractCategories();
                this.updateSkillsList();
            }
        } catch (e) {
            console.error('Failed to fetch skills:', e);
            // Use mock data for demo
            this.useMockSkills();
            this.updateSkillsList();
        }
    }
    
    useMockSkills() {
        this.skills = [
            {
                id: 'code-review',
                name: 'Code Review',
                slashCommand: 'code-review',
                category: 'development',
                description: 'Automated PR code review with multi-expert Agent parallel review, confidence-based scoring to filter low-quality results.',
                icon: '🔍',
                variables: [
                    { name: 'target', type: 'text', required: true, label: 'Target Files/PR', hint: 'Files or PR URL to review' },
                    { name: 'depth', type: 'select', required: false, label: 'Review Depth', options: ['quick', 'standard', 'deep'], default: 'standard' }
                ]
            },
            {
                id: 'debug',
                name: 'Debug Analyzer',
                slashCommand: 'debug',
                category: 'development',
                description: 'Analyze error messages and code to help locate and fix bugs.',
                icon: '🐛',
                variables: [
                    { name: 'error', type: 'textarea', required: true, label: 'Error Message', hint: 'Paste the error message or stack trace' },
                    { name: 'context', type: 'textarea', required: false, label: 'Code Context', hint: 'Optional: paste related code' }
                ]
            },
            {
                id: 'commit-msg',
                name: 'Commit Message Generator',
                slashCommand: 'commit-msg',
                category: 'development',
                description: 'Generate standardized Git commit messages based on code changes.',
                icon: '📝',
                variables: []
            },
            {
                id: 'translate',
                name: 'Translate',
                slashCommand: 'translate',
                category: 'writing',
                description: 'Translate text to different languages with context-aware handling.',
                icon: '🌐',
                variables: [
                    { name: 'text', type: 'textarea', required: true, label: 'Text to Translate' },
                    { name: 'lang', type: 'select', required: true, label: 'Target Language', options: ['English', 'Chinese', 'Japanese', 'Spanish', 'French', 'German'] }
                ]
            },
            {
                id: 'write-doc',
                name: 'Documentation Writer',
                slashCommand: 'write-doc',
                category: 'writing',
                description: 'Generate comprehensive documentation for code modules.',
                icon: '📄',
                variables: [
                    { name: 'target', type: 'text', required: true, label: 'Target Module/File' },
                    { name: 'format', type: 'select', required: false, label: 'Output Format', options: ['markdown', 'rst', 'html'], default: 'markdown' }
                ]
            },
            {
                id: 'write-test',
                name: 'Test Generator',
                slashCommand: 'write-test',
                category: 'development',
                description: 'Generate unit tests for specified code modules.',
                icon: '🧪',
                variables: [
                    { name: 'target', type: 'text', required: true, label: 'Target Module' },
                    { name: 'framework', type: 'select', required: false, label: 'Test Framework', options: ['pytest', 'unittest', 'jest', 'mocha'], default: 'pytest' }
                ]
            },
            {
                id: 'refactor',
                name: 'Refactor Assistant',
                slashCommand: 'refactor',
                category: 'development',
                description: 'Analyze and suggest refactoring improvements for code.',
                icon: '🔧',
                variables: [
                    { name: 'target', type: 'text', required: true, label: 'Target Code' },
                    { name: 'focus', type: 'select', required: false, label: 'Focus Area', options: ['performance', 'readability', 'maintainability', 'all'], default: 'all' }
                ]
            },
            {
                id: 'security-check',
                name: 'Security Check',
                slashCommand: 'security-check',
                category: 'analysis',
                description: 'Security audit hook that automatically alerts for command injection, XSS, unsafe patterns.',
                icon: '🔒',
                variables: [
                    { name: 'target', type: 'text', required: true, label: 'Target Files' }
                ]
            },
            {
                id: 'benchmark',
                name: 'Performance Benchmark',
                slashCommand: 'benchmark',
                category: 'analysis',
                description: 'Collect Web/API/Bundle performance metrics and compare with baseline.',
                icon: '📊',
                variables: [
                    { name: 'url', type: 'text', required: true, label: 'Target URL' },
                    { name: 'iterations', type: 'number', required: false, label: 'Iterations', default: 10 }
                ]
            },
            {
                id: 'create-skill',
                name: 'Create Skill',
                slashCommand: 'create-skill',
                category: 'custom',
                description: 'Create, improve, and evaluate Skills: build skill templates from scratch, benchmark performance.',
                icon: '✨',
                variables: [
                    { name: 'name', type: 'text', required: true, label: 'Skill Name' },
                    { name: 'description', type: 'textarea', required: true, label: 'Description' },
                    { name: 'type', type: 'select', required: true, label: 'Skill Type', options: ['prompt', 'native', 'orchestration'] }
                ]
            }
        ];
        
        this.categories = this.extractCategories();
    }
    
    extractCategories() {
        const cats = {};
        this.skills.forEach(s => {
            const cat = s.category || 'other';
            if (!cats[cat]) {
                cats[cat] = { name: cat, skills: [], icon: this.getCategoryIcon(cat) };
            }
            cats[cat].skills.push(s);
        });
        return Object.values(cats);
    }
    
    getCategoryIcon(category) {
        const icons = {
            'development': '💻',
            'writing': '📝',
            'analysis': '📊',
            'custom': '✨',
            'other': '📁'
        };
        return icons[category] || '📁';
    }
    
    // ==================== UI Updates ====================
    updateSkillsList() {
        const container = document.getElementById('skills-list-container');
        if (!container) return;
        
        container.innerHTML = this.categories.map(cat => `
            <div class="skills-category">
                <div class="skills-category-title">
                    <span>${cat.icon}</span>
                    <span>${cat.name}</span>
                    <span class="skills-category-count">(${cat.skills.length})</span>
                </div>
                ${cat.skills.map(s => `
                    <div class="skill-item ${this.selectedSkill?.id === s.id ? 'active' : ''}" 
                         data-id="${s.id}" 
                         onclick="skillsManager.selectSkill('${s.id}')">
                        <span class="skill-item-icon">${s.icon || '⚡'}</span>
                        <span class="skill-item-name">${this.escapeHtml(s.name)}</span>
                    </div>
                `).join('')}
            </div>
        `).join('');
    }
    
    selectSkill(skillId) {
        this.selectedSkill = this.skills.find(s => s.id === skillId);
        this.updateSkillsList();
        this.updateSkillDetail();
    }
    
    updateSkillDetail() {
        const section = document.getElementById('skill-detail-section');
        if (!section) return;
        
        if (!this.selectedSkill) {
            section.innerHTML = `
                <div class="skill-detail-empty">
                    <div class="skill-detail-empty-icon">⚡</div>
                    <div>Select a skill to view details</div>
                </div>
            `;
            return;
        }
        
        const skill = this.selectedSkill;
        
        section.innerHTML = `
            <div class="skill-detail-header">
                <div class="skill-detail-icon">${skill.icon || '⚡'}</div>
                <div class="skill-detail-info">
                    <div class="skill-detail-name">${this.escapeHtml(skill.name)}</div>
                    <div class="skill-detail-category">${skill.category || 'other'}</div>
                    <div class="skill-detail-command">/${skill.slashCommand}</div>
                </div>
            </div>
            
            <div class="skill-detail-description">${this.escapeHtml(skill.description)}</div>
            
            ${skill.variables && skill.variables.length > 0 ? `
                <div class="skill-variables-section">
                    <div class="skill-variables-title">⚙️ Variables</div>
                    ${skill.variables.map(v => this.renderVariableInput(v)).join('')}
                </div>
            ` : ''}
            
            <div class="skill-execute-section">
                <button class="skill-execute-btn" id="skill-execute-btn" onclick="skillsManager.executeSkill()">
                    <span>▶️</span>
                    <span>Execute Skill</span>
                </button>
            </div>
            
            <div class="skill-history-section">
                <div class="skill-history-title">
                    <span>📜 Recent Executions</span>
                    <span class="skill-history-clear" onclick="skillsManager.clearHistory()">Clear</span>
                </div>
                <div class="skill-history-list" id="skill-history-list">
                    ${this.renderHistory()}
                </div>
            </div>
        `;
    }
    
    renderVariableInput(variable) {
        const requiredMark = variable.required ? '<span class="skill-variable-required">*</span>' : '';
        
        let inputHtml = '';
        
        if (variable.type === 'select') {
            inputHtml = `
                <select class="skill-variable-input select" 
                        id="var-${variable.name}" 
                        data-var="${variable.name}">
                    ${variable.options.map(opt => `
                        <option value="${opt}" ${opt === variable.default ? 'selected' : ''}>${opt}</option>
                    `).join('')}
                </select>
            `;
        } else if (variable.type === 'textarea') {
            inputHtml = `
                <textarea class="skill-variable-input textarea" 
                          id="var-${variable.name}" 
                          data-var="${variable.name}"
                          placeholder="${variable.hint || ''}"></textarea>
            `;
        } else if (variable.type === 'number') {
            inputHtml = `
                <input type="number" class="skill-variable-input" 
                       id="var-${variable.name}" 
                       data-var="${variable.name}"
                       value="${variable.default || ''}"
                       placeholder="${variable.hint || ''}">
            `;
        } else {
            inputHtml = `
                <input type="text" class="skill-variable-input" 
                       id="var-${variable.name}" 
                       data-var="${variable.name}"
                       value="${variable.default || ''}"
                       placeholder="${variable.hint || ''}">
            `;
        }
        
        return `
            <div class="skill-variable-item">
                <div class="skill-variable-label">
                    <span>${this.escapeHtml(variable.label)}</span>
                    ${requiredMark}
                </div>
                ${inputHtml}
                ${variable.hint ? `<div class="skill-variable-hint">${this.escapeHtml(variable.hint)}</div>` : ''}
            </div>
        `;
    }
    
    renderHistory() {
        if (this.executionHistory.length === 0) {
            return '<div style="text-align: center; padding: 20px; color: var(--text-tertiary);">No execution history</div>';
        }
        
        return this.executionHistory.slice(0, 10).map(h => `
            <div class="skill-history-item">
                <div class="skill-history-header">
                    <div class="skill-history-name">${this.escapeHtml(h.skillName)}</div>
                    <div class="skill-history-time">${this.formatTime(h.timestamp)}</div>
                </div>
                <div class="skill-history-status ${h.status}">
                    ${h.status === 'success' ? '✅ Success' : h.status === 'error' ? '❌ Error' : '⏳ Running'}
                </div>
            </div>
        `).join('');
    }
    
    // ==================== Actions ====================
    filterSkills(query) {
        const q = query.toLowerCase();
        
        if (!q) {
            this.categories = this.extractCategories();
        } else {
            const filtered = this.skills.filter(s => 
                s.name.toLowerCase().includes(q) || 
                s.description.toLowerCase().includes(q) ||
                s.slashCommand.toLowerCase().includes(q)
            );
            this.categories = [{ name: 'Results', skills: filtered, icon: '🔍' }];
        }
        
        this.updateSkillsList();
    }
    
    async executeSkill() {
        if (!this.selectedSkill) return;
        
        const btn = document.getElementById('skill-execute-btn');
        if (btn) {
            btn.classList.add('loading');
            btn.disabled = true;
        }
        
        // Collect variables
        const variables = {};
        if (this.selectedSkill.variables) {
            this.selectedSkill.variables.forEach(v => {
                const input = document.getElementById(`var-${v.name}`);
                if (input) {
                    variables[v.name] = input.value;
                }
            });
        }
        
        // Check required variables
        const missing = this.selectedSkill.variables?.filter(v => v.required && !variables[v.name]) || [];
        if (missing.length > 0) {
            alert(`Missing required variables: ${missing.map(v => v.label).join(', ')}`);
            if (btn) {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
            return;
        }
        
        // Add to history
        const historyEntry = {
            skillId: this.selectedSkill.id,
            skillName: this.selectedSkill.name,
            timestamp: new Date().toISOString(),
            status: 'running',
            variables
        };
        this.executionHistory.unshift(historyEntry);
        this.updateSkillDetail();
        
        try {
            const resp = await fetch(`${this.options.apiBase}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    skillId: this.selectedSkill.id,
                    slashCommand: this.selectedSkill.slashCommand,
                    variables
                })
            });
            
            const result = await resp.json();
            
            // Update history
            historyEntry.status = result.success ? 'success' : 'error';
            historyEntry.result = result;
            this.updateSkillDetail();
            
            // Show result modal
            this.showResultModal(result);
            
        } catch (e) {
            console.error('Failed to execute skill:', e);
            historyEntry.status = 'error';
            historyEntry.error = e.message;
            this.updateSkillDetail();
            
            // Show mock result for demo
            this.showResultModal({
                success: true,
                output: `Skill "${this.selectedSkill.name}" executed successfully.\n\nVariables used:\n${JSON.stringify(variables, null, 2)}\n\n(This is a demo result. Connect to a real backend for actual execution.)`
            });
        }
        
        if (btn) {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }
    
    showResultModal(result) {
        const modal = document.getElementById('skill-result-modal');
        const title = document.getElementById('skill-result-title');
        const output = document.getElementById('skill-result-output');
        
        if (modal && title && output) {
            title.textContent = result.success ? '✅ Success' : '❌ Error';
            output.textContent = result.output || result.error || JSON.stringify(result, null, 2);
            modal.classList.add('visible');
        }
    }
    
    hideResultModal() {
        const modal = document.getElementById('skill-result-modal');
        if (modal) {
            modal.classList.remove('visible');
        }
    }
    
    clearHistory() {
        this.executionHistory = [];
        this.updateSkillDetail();
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
        const panel = document.getElementById('skills-panel');
        if (panel) {
            panel.classList.add('visible');
            this.panelVisible = true;
            this.fetchSkills();
        }
    }
    
    hidePanel() {
        const panel = document.getElementById('skills-panel');
        if (panel) {
            panel.classList.remove('visible');
            this.panelVisible = false;
        }
    }
    
    // ==================== Helpers ====================
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Global instance
let skillsManager = null;

function initSkillsManager(options = {}) {
    skillsManager = new SkillsManager(options);
    return skillsManager;
}

// Auto-initialize (reliable for scripts loaded at end of body)
(function() {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        // DOM is already ready, init after current execution
        requestAnimationFrame(() => initSkillsManager());
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            initSkillsManager();
        });
    }
})();