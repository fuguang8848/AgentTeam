# AgentTeam

Production-ready multi-agent swarm coordination framework. Built for OpenClaw, powered by AI agents themselves.

## Features

- **Multi-Agent Orchestration**: Coordinate multiple AI agents to work together on complex tasks
- **Team Management**: Create, manage, and monitor agent teams with role-based assignments
- **Message Passing**: Inter-agent communication with mailbox and inbox system
- **Session Awareness**: Track and maintain context across agent sessions
- **Real-time Dashboard**: Visual monitoring of agent activities and collaborations
- **Plugin System**: Extensible architecture with custom skills and integrations

## Quick Start

```bash
# Install
pip install agentteam

# Initialize a new team
agentteam init my-team

# Start the team
agentteam start my-team

# Spawn agents
agentteam spawn --name worker-1 --role researcher
agentteam spawn --name worker-2 --role coder
```

## Documentation

For full documentation, visit [OpenClaw Docs](https://docs.openclaw.ai).

## License

MIT
