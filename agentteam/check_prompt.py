import sys
sys.path.insert(0, r'C:\Users\31683\.openclaw\workspace\AgentTeam-OpenClaw')
from agentteam.spawn.prompt import build_agent_prompt

prompt = build_agent_prompt(
    agent_name='test',
    agent_id='test',
    agent_type='tester',
    team_name='team',
    leader_name='leader',
    task='Say hello',
    user='',
    workspace_dir='',
    workspace_branch='',
)

print(f'Prompt length: {len(prompt)}')
print(f'Has <>: {"<" in prompt}')
print(f'Has >: {">" in prompt}')
print()
print('Lines with angle brackets:')
for i, line in enumerate(prompt.split('\n')):
    if '<' in line or '>' in line:
        print(f'  Line {i}: {repr(line)}')
