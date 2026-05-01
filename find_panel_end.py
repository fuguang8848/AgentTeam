"""Find settings panel structure"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()
print(f'File size: {len(content)} chars')

idx = content.find('id="settings-skills"')
print(f'settings-skills at: {idx}')

# Find closing div
depth = 0
for i in range(idx, len(content)):
    if content[i:i+5] == '<div ':
        depth += 1
    elif content[i:i+6] == '</div>':
        depth -= 1
        if depth == 0:
            end_pos = i + 6
            print(f'Panel ends at: {end_pos}')
            print('After:', repr(content[end_pos:end_pos+150]))
            break
