import agentteam

print("agentteam file:", agentteam.__file__)
print("agentteam version:", agentteam.__version__)

# Check if the backend has escaping
from agentteam.spawn.openclaw_sdk_backend import OpenClawSDKBackend
import inspect

source = inspect.getsource(OpenClawSDKBackend._gateway_call)
if "replace" in source and "^<" in source:
    print("Backend HAS escaping")
else:
    print("Backend MISSING escaping")
    # Show the relevant lines
    for i, line in enumerate(source.split("\n")):
        if "replace" in line or "--params" in line:
            print(f"  {i}: {line}")
