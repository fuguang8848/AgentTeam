"""Test simple command"""
import subprocess
import locale
import json

encoding = locale.getpreferredencoding(False) or "utf-8"

# Test 1: no params at all
print("Test 1: no params")
cmd = ['cmd', '/c', 'openclaw', 'gateway', 'call', 'sessions.create']
result = subprocess.run(cmd, capture_output=True, timeout=30)
print(f"returncode: {result.returncode}")
print(f"stderr: {result.stderr.decode(encoding, errors='replace')[:200]}")

# Test 2: simple params without < or >
print("\nTest 2: simple params (no special chars)")
params = {"key": "test", "message": "hello world"}
params_json = json.dumps(params)
cmd = ['cmd', '/c', 'openclaw', 'gateway', 'call', 'sessions.send', '--params', params_json]
result = subprocess.run(cmd, capture_output=True, timeout=30)
print(f"returncode: {result.returncode}")
print(f"stderr: {result.stderr.decode(encoding, errors='replace')[:200]}")

# Test 3: params with caret-escaped brackets
print("\nTest 3: params with ^< ^> escaping")
params = {"key": "test", "message": "test ^<hello^> world"}
params_json = json.dumps(params).replace('<', '^<').replace('>', '^>')
cmd = ['cmd', '/c', 'openclaw', 'gateway', 'call', 'sessions.send', '--params', params_json]
print(f"cmd: {cmd}")
result = subprocess.run(cmd, capture_output=True, timeout=30)
print(f"returncode: {result.returncode}")
stdout = result.stdout.decode(encoding, errors='replace')
stderr = result.stderr.decode(encoding, errors='replace')
print(f"stdout: {stdout[:200]}")
print(f"stderr: {stderr[:200]}")