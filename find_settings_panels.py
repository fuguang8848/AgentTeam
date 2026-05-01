"""Find settings page end"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find the settings page
idx = content.find('id="page-settings"')
if idx == -1:
    print("page-settings not found")
    exit()

# Find the closing div for the settings page
# Look for the pattern where settings page ends
# It's usually after all the settings panels
search = 'id="page-settings"'
idx = content.find(search)
if idx != -1:
    # Find the end of the page-settings div
    depth = 0
    start = idx
    for i, c in enumerate(content[idx:]):
        if c == '<':
            if content[idx+i:idx+i+5] == '<div ':
                depth += 1
            elif content[idx+i:idx+i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end = idx + i + 6
                    print(f"page-settings ends at position {end}")
                    # Show last 200 chars before end
                    print(content[end-200:end])
                    break

# Also find where settings-skills panel ends
idx2 = content.find('id="settings-skills"')
if idx2 != -1:
    print(f"\nsettings-skills at {idx2}")
    # Find its end
    depth = 0
    for i, c in enumerate(content[idx2:]):
        if c == '<':
            if content[idx2+i:idx2+i+5] == '<div ':
                depth += 1
            elif content[idx2+i:idx2+i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end = idx2 + i + 6
                    print(f"settings-skills ends at position {end}")
                    break
