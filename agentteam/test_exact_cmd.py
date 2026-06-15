"""Test the exact command from the trace"""

import subprocess
import locale
import json

encoding = locale.getpreferredencoding(False) or "utf-8"

# Build the params directly
key = "agent:main:dashboard:1af1fa5b-0c00-43a8-9b77-d7436b40a4b7"
message = "Test message with <angle> brackets"

params = {"key": key, "message": message}
params_json = json.dumps(params, ensure_ascii=False)
params_json_escaped = params_json.replace("<", "^<").replace(">", "^>")

print(f"Original JSON: {params_json}")
print(f"Escaped JSON: {params_json_escaped}")

cmd = ["cmd", "/c", "openclaw", "gateway", "call", "sessions.send", "--params", params_json_escaped]
print(f"\nCommand: {cmd}")

result = subprocess.run(cmd, capture_output=True, timeout=30)
print(f"returncode: {result.returncode}")
stdout = result.stdout.decode(encoding, errors="replace")
stderr = result.stderr.decode(encoding, errors="replace")
print(f"stdout: {stdout}")
print(f"stderr: {stderr}")
