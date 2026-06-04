import sys
sys.path.insert(0, 'C:\\Users\\31683\\.openclaw\\workspace\\AgentTeam-OpenClaw')
from agentteam.spawn.openclaw_sdk_backend import OpenClawSDKBackend

backend = OpenClawSDKBackend()
print('_gateway_cmd:', backend._gateway_cmd)

# Try a simple spawn
result = backend.spawn(
    command=['openclaw'],
    agent_name='cli-test',
    agent_id='test:cli-test',
    agent_type='tester',
    team_name='cli-test-team',
    prompt='Say hello in 1 sentence',
    model=None,
)
print('Spawn result:', result)
