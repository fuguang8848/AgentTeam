"""Find all self.method usages"""
content = open('clawteam/board/server.py', 'r', encoding='utf-8').read()

import re
matches = list(re.finditer(r'self\.method', content))
print(f"Found {len(matches)} uses of self.method")
for m in matches:
    start = max(0, m.start() - 50)
    end = min(len(content), m.end() + 50)
    print(f"\n--- {m.start()} ---")
    print(content[start:end])
