"""Find where to insert providers panel"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find settings-skills panel end
search = 'id="settings-skills"'
idx = content.find(search)
if idx == -1:
    print("settings-skills not found")
    exit()

print(f"settings-skills at position {idx}")

# Find the closing div for settings-skills panel
# Look for the pattern: </div></div></div> (panel-body, panel, settings-panel)
depth = 0
panel_start = -1
for i in range(idx, len(content)):
    if content[i:i+5] == '<div ':
        if panel_start == -1:
            panel_start = i
        depth += 1
    elif content[i:i+6] == '</div>':
        depth -= 1
        if depth == 0 and panel_start != -1:
            end = i + 6
            print(f"settings-skills panel ends at {end}")
            # Show what's after
            print(f"Content after (next 100 chars): {repr(content[end:end+100])}")
            break
