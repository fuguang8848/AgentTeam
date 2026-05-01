"""Find providers route location"""
content = open('clawteam/board/server.py', 'r', encoding='utf-8').read()

# Find where to add providers endpoints
import re
matches = list(re.finditer(r'elif path == "/api/', content))
print(f"Found {len(matches)} API routes")
for m in matches[:15]:
    start = max(0, m.start() - 20)
    print(f"  {content[start:m.end()].strip()}")
