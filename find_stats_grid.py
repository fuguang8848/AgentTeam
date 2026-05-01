"""Find stats grid and dashboard cards"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find stats-grid section
stats_grid = content.find('stats-grid')
if stats_grid == -1:
    print("stats-grid not found")
    exit()

# Find the stats container
stats_start = content.rfind('<div', 0, stats_grid)
stats_end = content.find('</div>', stats_grid) + 6

print(f"Stats section at chars {stats_start} to {stats_end}")
print()

# Extract and show the stats section
stats_html = content[stats_start:stats_end]
print("Stats HTML (first 2000 chars):")
print(stats_html[:2000])
print()
print("Stats HTML (last 1000 chars):")
print(stats_html[-1000:])
