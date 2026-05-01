"""Find provider-related code"""
import os
import re

provider_files = []
pattern = re.compile(r'provider|api_key|openai|anthropic', re.IGNORECASE)

for root, dirs, files in os.walk('clawteam'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                content = open(path, 'r', encoding='utf-8').read()
                if pattern.search(content):
                    matches = pattern.findall(content)
                    provider_files.append((path, len(matches)))
            except:
                pass

print(f"Found {len(provider_files)} files with provider-related code:")
for path, count in sorted(provider_files, key=lambda x: -x[1])[:10]:
    print(f"  {path}: {count} matches")
