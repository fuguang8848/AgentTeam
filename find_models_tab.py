"""Find model settings section"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find the models settings tab
idx = content.find('settings-models')
if idx == -1:
    print("settings-models not found")
    exit()

# Show context around it
start = max(0, idx - 100)
end = min(len(content), idx + 2000)
print(content[start:end])
