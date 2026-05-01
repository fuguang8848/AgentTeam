"""Find dashboard page HTML"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find the page-dashboard div
dashboard_id = 'id="page-dashboard"'
idx = content.find(dashboard_id)
if idx == -1:
    print("page-dashboard not found")
    exit()

print(f"page-dashboard at char {idx}")

# Find the next page div or end of dashboard
next_page = content.find('id="page-', idx + 10)
if next_page == -1:
    next_page = len(content)

# Find the closing div for page-dashboard (go backwards from next_page to find it)
# Actually, each page has class="page"
page_start = content.rfind('<div', 0, idx)
print(f"page div starts at char {page_start}")

# The dashboard content is between page-dashboard and the next page
dashboard_content_start = idx
dashboard_content_end = next_page

dashboard_html = content[dashboard_content_start:dashboard_content_end]
print(f"Dashboard content length: {len(dashboard_html)} chars")

# Find stats-grid in dashboard content
stats_idx = dashboard_html.find('stats-grid')
print(f"stats-grid found at offset {stats_idx} within dashboard")

# Show first 3000 chars of dashboard
print("\n--- Dashboard HTML (first 3000 chars) ---")
# Replace Chinese with placeholders for display
display = dashboard_html[:3000]
print(display)
