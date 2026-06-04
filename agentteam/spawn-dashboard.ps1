cd C:\Users\31683\.openclaw\workspace\AgentTeam-OpenClaw
$task = @"
Implement AgentTeam Command Center Web Dashboard (SpectrAI-inspired):

## 任务
1. Create agentteam/board/dashboard.py with CommandCenterDashboard class
2. Create agentteam/api/monitor.py with REST API endpoints
3. Create agentteam/board/templates/dashboard.html with dark theme UI
4. Integrate into agentteam/board/server.py

## Dashboard UI Requirements
- Global KPI cards: Sessions count, Token consumption, Risk sessions
- Active sessions list with duration and event count
- Event distribution bar chart (Startup, Activity, Input, Round Complete)
- Lifecycle stats (Running, Waiting, Completed, Abnormal)
- Auto-refresh every 10 seconds
- Team selector dropdown

## API Endpoints
- GET /api/monitor/stats - global statistics
- GET /api/monitor/sessions - active sessions list
- GET /api/monitor/sessions/{id} - session detail
- GET /api/monitor/sessions/{id}/events - session events
- GET /api/monitor/teams/{team}/lifecycle - lifecycle stats

Report to leader when done.
"@

$encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($task))
agentteam spawn openclaw_sdk --team monitor-squad --agent-name arch-dashboard --agent-type developer --task "$($encoded)" 2>&1
