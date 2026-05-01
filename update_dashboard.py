"""Update dashboard with performance metrics"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find the dashboard header section and replace
old_header = '''<div class="dashboard-header">
                    <h1>指挥中心</h1>
                    <p>实时会话监控与资源调度</p>
                </div>'''

new_header = '''<div class="dashboard-header">
                    <h1>系统性能</h1>
                    <p>CPU、内存、线程实时状态</p>
                </div>'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("Header replaced")
else:
    print("Header not found - trying alternate")
    # Try without the Chinese chars
    idx = content.find('id="page-dashboard"')
    if idx != -1:
        # Look for the dashboard header pattern
        import re
        pattern = r'<div class="dashboard-header">\s*<h1>[^<]*</h1>\s*<p>[^<]*</p>\s*</div>'
        match = re.search(pattern, content[idx:idx+500])
        if match:
            print(f"Found header at offset {match.start()}")
            old = match.group(0)
            new = '<div class="dashboard-header"><h1>系统性能</h1><p>CPU、内存、线程实时状态</p></div>'
            content = content[:idx + match.start()] + new + content[idx + match.end():]
            print("Header replaced via regex")

# Now replace the stats grid with performance stats
# Find the stats-grid div content
old_stats = '''<div class="stat-card">
                        <div class="stat-label">会话总数 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg></div>
                        <div class="stat-value blue" id="stat-sessions">0</div>
                        <div class="stat-sub" id="stat-active">0 个活跃</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">运行中 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
                        <div class="stat-value green" id="stat-running">0</div>
                        <div class="stat-sub" id="stat-running-sub">当前无运行会话</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">等待输入 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
                        <div class="stat-value yellow" id="stat-waiting">0</div>
                        <div class="stat-sub">需要处理</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">风险会话 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
                        <div class="stat-value red" id="stat-risk">0</div>
                        <div class="stat-sub">无高风险会话</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Token 消耗 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
                        <div class="stat-value" id="stat-tokens">0</div>
                        <div class="stat-sub" id="stat-avg-tokens">均值 0/会话</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">缓存命中率 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 100 20 10 10 0 000-20z"/><path d="M12 6v6l4 2"/></svg></div>
                        <div class="stat-value" id="stat-cache">--</div>
                        <div class="stat-sub">尚无缓存记录</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">工作流执行 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
                        <div class="stat-value" id="stat-workflows">0</div>
                        <div class="stat-sub">已完成</div>
                    </div>'''

new_stats = '''<div class="stat-card">
                        <div class="stat-label">CPU 使用 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/></svg></div>
                        <div class="stat-value blue" id="stat-cpu">0%</div>
                        <div class="stat-sub" id="stat-cpu-sub">当前负载</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">内存占用 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 17a5 5 0 005 5 5 5 0 005-5 5 5 0 005 5 5 5 0 005-5M2 7a5 5 0 015-5 5 5 0 015 5 5 5 0 015-5 5 5 0 015 5M2 12a5 5 0 015-5 5 5 0 015 5 5 5 0 015-5 5 5 0 015 5"/></svg></div>
                        <div class="stat-value green" id="stat-memory">0 MB</div>
                        <div class="stat-sub" id="stat-memory-sub">已用内存</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">活跃线程 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></div>
                        <div class="stat-value yellow" id="stat-threads">0</div>
                        <div class="stat-sub">当前线程数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">打开文件 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
                        <div class="stat-value red" id="stat-files">0</div>
                        <div class="stat-sub">文件句柄</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Token 消耗 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
                        <div class="stat-value" id="stat-tokens">0</div>
                        <div class="stat-sub" id="stat-avg-tokens">均值 0/会话</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">缓存命中率 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 100 20 10 10 0 000-20z"/><path d="M12 6v6l4 2"/></svg></div>
                        <div class="stat-value" id="stat-cache">--</div>
                        <div class="stat-sub">尚无缓存记录</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">工作流执行 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
                        <div class="stat-value" id="stat-workflows">0</div>
                        <div class="stat-sub">已完成</div>
                    </div>'''

if old_stats in content:
    content = content.replace(old_stats, new_stats)
    print("Stats replaced")
else:
    print("Stats pattern not found exactly - trying partial match")
    # Try to find and replace just the stat-cards section
    import re
    # Find the stats-grid div
    pattern = r'<div class="stats-grid">.*?</div>\s*</div>\s*</div>'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"Found stats-grid at {match.start()}-{match.end()}")
        # Show what we found
        found = match.group(0)[:500]
        print(f"Content preview: {found[:200]}...")

# Write back
open('clawteam/board/static/index.html', 'w', encoding='utf-8').write(content)
print("\nDashboard HTML updated")
