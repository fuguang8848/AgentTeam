"""Find session monitoring sections"""
content = open('clawteam/board/static/index.html', 'r', encoding='utf-8').read()

# Find dashboard section
import re

# Look for session monitoring related content
patterns = [
    'session-count-badge',
    '实时会话',
    '会话监控',
    '实时监控',
    'session-monitor',
]

for pat in patterns:
    idx = content.find(pat)
    if idx != -1:
        print(f"Found '{pat}' at position {idx}")
        # Show context
        start = max(0, idx - 100)
        end = min(len(content), idx + 200)
        context = content[start:end]
        # Truncate to 80 chars per line
        for line in context.split('\n')[:5]:
            if len(line) > 80:
                line = line[:80] + '...'
            print(f"  {line}")
        print()
