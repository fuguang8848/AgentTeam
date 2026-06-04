# AgentTeam Coordination Workflows

## Workflow 1: Create a Team and Assign Tasks

A common workflow for setting up a new project team.

```bash
# 1. Set leader identity
export AGENTTEAM_AGENT_ID="leader-001"
export AGENTTEAM_AGENT_NAME="leader"
export AGENTTEAM_AGENT_TYPE="leader"

# 2. Create team
agentteam team spawn-team my-project -d "Web app development" -n leader

# 3. Create tasks with dependencies
agentteam task create my-project "Design API schema" -o leader
# => Task ID: aaa11111

agentteam task create my-project "Implement backend" -o backend-dev --blocked-by aaa11111
# => Task ID: bbb22222 (auto-set to blocked status)

agentteam task create my-project "Build frontend" -o frontend-dev --blocked-by aaa11111
# => Task ID: ccc33333

agentteam task create my-project "Integration testing" --blocked-by bbb22222,ccc33333
# => Task ID: ddd44444

# 4. Check board
agentteam board show my-project

# 5. As tasks complete, update status (auto-unblocks dependents)
agentteam task update my-project aaa11111 --status completed
# bbb22222 and ccc33333 auto-unblock from blocked -> pending
```

## Workflow 2: Multi-Agent Spawn and Coordination

Full lifecycle of spawning multiple agents and coordinating work.

```bash
# Leader creates team
agentteam team spawn-team dev-team -d "Feature development" -n leader

# Spawn worker agents (each gets identity env vars automatically)
agentteam spawn tmux claude --team dev-team --agent-name researcher --agent-type researcher
agentteam spawn tmux claude --team dev-team --agent-name coder --agent-type general-purpose

# Leader creates tasks
agentteam task create dev-team "Research best practices" -o researcher
agentteam task create dev-team "Implement solution" -o coder

# Leader sends instructions via inbox
agentteam inbox send dev-team researcher "Research authentication patterns for microservices"
agentteam inbox send dev-team coder "Wait for researcher's findings before starting implementation"

# Monitor progress
agentteam board live dev-team --interval 5
```

### Worker Agent Perspective

From inside a spawned worker agent:

```bash
# Identity is pre-set via environment
agentteam identity show
# => agentName: researcher, teamName: dev-team

# Check inbox for instructions
agentteam inbox receive dev-team

# Do work, then update task
agentteam task update dev-team <task-id> --status in_progress
# ... work ...
agentteam task update dev-team <task-id> --status completed

# Notify leader when idle
agentteam lifecycle idle dev-team --last-task <task-id> --task-status completed
```

## Workflow 3: Join Request Protocol

When an agent wants to join an existing team dynamically.

```bash
# Agent side: request to join (blocks until response)
agentteam team request-join dev-team bob --capabilities "frontend specialist" --timeout 120

# Leader side: check inbox for join requests
agentteam inbox peek dev-team --agent leader
# => join_request from bob, requestId: join-abc123

# Leader approves
agentteam team approve-join dev-team join-abc123

# Agent receives approval with assigned name and agent ID
# => Approved! Joined as 'bob' (agentId: xyz789)
```

## Workflow 4: Plan Approval Flow

For teams requiring plan review before execution.

```bash
# Worker submits plan
agentteam plan submit dev-team coder "1. Refactor auth module\n2. Add OAuth2\n3. Update tests" \
  --summary "Auth system modernization"

# Leader reviews (checks inbox)
agentteam inbox receive dev-team --agent leader
# => plan_approval_request with planId

# Leader approves or rejects
agentteam plan approve dev-team <plan-id> coder --feedback "Looks good, proceed"
# or
agentteam plan reject dev-team <plan-id> coder --feedback "Add error handling section"
```

## Workflow 5: Graceful Shutdown

Coordinated shutdown of team agents.

```bash
# Leader requests shutdown of a worker
agentteam lifecycle request-shutdown dev-team leader coder --reason "All tasks complete"

# Worker checks inbox, sees shutdown request
agentteam inbox receive dev-team --agent coder
# => shutdown_request, requestId: shut-xyz

# Worker finishes current work, then approves
agentteam lifecycle approve-shutdown dev-team shut-xyz coder

# Leader cleans up team when all agents are done
agentteam team cleanup dev-team --force
```

## Workflow 6: Monitoring and Debugging

Using board and inbox commands to monitor team health.

```bash
# Quick overview of all teams
agentteam board overview

# Detailed view of one team
agentteam board show dev-team

# JSON output for scripting/parsing
agentteam --json board show dev-team | jq '.taskSummary'
agentteam --json task list dev-team --status blocked | jq '.[].subject'

# Check who has unread messages
agentteam --json board show dev-team | jq '.members[] | select(.inboxCount > 0) | .name'

# Live monitoring
agentteam board live dev-team --interval 3

# Watch a specific agent's inbox
agentteam inbox watch dev-team --agent leader
```

## Common Patterns

### Task with Dependencies

```bash
# Create a chain: A -> B -> C
agentteam task create team "Task A" -o alice
# ID: aaa
agentteam task create team "Task B" -o bob --blocked-by aaa
# ID: bbb (status: blocked)
agentteam task create team "Task C" -o carol --blocked-by bbb
# ID: ccc (status: blocked)

# When A completes, B auto-unblocks
agentteam task update team aaa --status completed
# B moves from blocked -> pending

# When B completes, C auto-unblocks
agentteam task update team bbb --status completed
```

### Broadcasting Updates

```bash
# Leader broadcasts to all team members
agentteam inbox broadcast dev-team "Sprint planning at 2pm. Check your tasks."

# Broadcast with routing key for filtering
agentteam inbox broadcast dev-team "Build passed" --key "ci-notification"
```

### Using JSON Output in Scripts

```bash
# Get all blocked tasks
BLOCKED=$(agentteam --json task list dev-team --status blocked)
echo "$BLOCKED" | jq -r '.[].id'

# Count pending messages per team
agentteam --json board overview | jq '.[] | "\(.name): \(.pendingMessages) pending"'

# Get team member names
agentteam --json team status dev-team | jq -r '.members[].name'
```
