"""Find all stat-card labels in dashboard"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find dashboard page
dashboard_id = 'id="page-dashboard"'
idx = content.find(dashboard_id)
if idx == -1:
    print("page-dashboard not found")
    exit()

# Find the next page
next_page = content.find('id="page-', idx + 10)
if next_page == -1:
    next_page = len(content)

dashboard_html = content[idx:next_page]

# Find all stat-card divs
import re
stat_cards = re.findall(r'stat-card.*?</div>\s*</div>', dashboard_html, re.DOTALL)

print(f"Found {len(stat_cards)} stat-cards\n")

for i, card in enumerate(stat_cards):
    # Extract the stat-label
    label_match = re.search(r'class="stat-label"[^>]*>([^<]+)', card)
    value_match = re.search(r'class="stat-value[^"]*"[^>]*id="([^"]+)"', card)
    print(f"Card {i+1}:")
    if label_match:
        print(f"  Label: {label_match.group(1)}")
    if value_match:
        print(f"  Value ID: {value_match.group(1)}")
    print()
