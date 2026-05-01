"""Find dashboard page structure"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find dashboard page section
search = 'id="page-dashboard"'
idx = content.find(search)
if idx == -1:
    print("Dashboard page not found")
    exit()

print(f"Dashboard page at char position {idx}")
print()

# Find the dashboard stats grid
stats_grid = content.find('stats-grid', idx)
print(f"stats-grid found at {stats_grid}")
print()

# Show the dashboard header area
start = idx
end = idx + 1500
dashboard_content = content[start:end]

# Find key elements
import re
session_badge = re.search(r'session-count-badge', dashboard_content)
if session_badge:
    print(f"session-count-badge found at offset {session_badge.start()} in dashboard")

# Find all panels
panels = re.findall(r'class="panel"', dashboard_content)
print(f"Number of panels in dashboard: {len(panels)}")

# Find stats
stats = re.findall(r'id="[^"]*count[^"]*"', dashboard_content)
print(f"Stats found: {stats[:10]}")
