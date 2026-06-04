# AgentTeam Fish Shell Completion
# Installation: Copy to ~/.config/fish/completions/agentteam.fish

complete -c agentteam -n '__fish_use_subcommand' -a 'team' -d 'Team management'
complete -c agentteam -n '__fish_use_subcommand' -a 'agents' -d 'Agent management'
complete -c agentteam -n '__fish_use_subcommand' -a 'task' -d 'Task management'
complete -c agentteam -n '__fish_use_subcommand' -a 'inbox' -d 'Inbox/messaging'
complete -c agentteam -n '__fish_use_subcommand' -a 'board' -d 'Board/dashboard'
complete -c agentteam -n '__fish_use_subcommand' -a 'config' -d 'Configuration'
complete -c agentteam -n '__fish_use_subcommand' -a 'spawn' -d 'Spawn a new agent'
complete -c agentteam -n '__fish_use_subcommand' -a 'help' -d 'Show help'
complete -c agentteam -n '__fish_use_subcommand' -a 'version' -d 'Show version'

# Team subcommands
complete -c agentteam -n '__fish_seen_subcommand_from team' -a 'spawn-team' -d 'Create a new team'
complete -c agentteam -n '__fish_seen_subcommand_from team' -a 'list' -d 'List all teams'
complete -c agentteam -n '__fish_seen_subcommand_from team' -a 'status' -d 'Show team status'
complete -c agentteam -n '__fish_seen_subcommand_from team' -a 'delete' -d 'Delete a team'

# Team spawn-team options
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team' -l description -s d -d 'Team description'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team' -l leader -s n -d 'Leader agent name'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team' -l template -s t -d 'Team template'

# Agents subcommands
complete -c agentteam -n '__fish_seen_subcommand_from agents' -a 'list' -d 'List agents in a team'
complete -c agentteam -n '__fish_seen_subcommand_from agents' -a 'kill' -d 'Kill an agent'

# Task subcommands
complete -c agentteam -n '__fish_seen_subcommand_from task' -a 'create' -d 'Create a new task'
complete -c agentteam -n '__fish_seen_subcommand_from task' -a 'list' -d 'List tasks'
complete -c agentteam -n '__fish_seen_subcommand_from task' -a 'update' -d 'Update a task'
complete -c agentteam -n '__fish_seen_subcommand_from task' -a 'delete' -d 'Delete a task'

# Task create options
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create' -l title -s t -d 'Task title'
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create' -l description -s d -d 'Task description'
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create' -l priority -s p -d 'Task priority'
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create' -l owner -s o -d 'Task owner'

# Inbox subcommands
complete -c agentteam -n '__fish_seen_subcommand_from inbox' -a 'send' -d 'Send a message'
complete -c agentteam -n '__fish_seen_subcommand_from inbox' -a 'list' -d 'List messages'
complete -c agentteam -n '__fish_seen_subcommand_from inbox' -a 'read' -d 'Read a message'

# Board subcommands
complete -c agentteam -n '__fish_seen_subcommand_from board' -a 'serve' -d 'Start web dashboard'
complete -c agentteam -n '__fish_seen_subcommand_from board' -a 'attach' -d 'Attach to team board'
complete -c agentteam -n '__fish_seen_subcommand_from board' -a 'token-stats' -d 'Show token statistics'

# Board serve options
complete -c agentteam -n '__fish_seen_subcommand_from board; and __fish_seen_subcommand_from serve' -l port -d 'Port number'
complete -c agentteam -n '__fish_seen_subcommand_from board; and __fish_seen_subcommand_from serve' -l host -d 'Host to bind to'
complete -c agentteam -n '__fish_seen_subcommand_from board; and __fish_seen_subcommand_from serve' -l open -d 'Open browser automatically'

# Spawn options
complete -c agentteam -n '__fish_seen_subcommand_from spawn' -l team -d 'Team name'
complete -c agentteam -n '__fish_seen_subcommand_from spawn' -l agent-name -d 'Agent name'
complete -c agentteam -n '__fish_seen_subcommand_from spawn' -l task -d 'Task description'
complete -c agentteam -n '__fish_seen_subcommand_from spawn' -l agent -d 'Agent backend'

# Templates
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team; and __fish_contains_opt template' -a 'dev-team' -d 'Development team'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team; and __fish_contains_opt template' -a 'dev-team-max' -d 'Full development team'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team; and __fish_contains_opt template' -a 'code-review' -d 'Code review team'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team; and __fish_contains_opt template' -a 'dev-team-mix' -d 'Mixed fullstack team'
complete -c agentteam -n '__fish_seen_subcommand_from team; and __fish_seen_subcommand_from spawn-team; and __fish_contains_opt template' -a 'office-team' -d 'Office team'

# Agent backends
complete -c agentteam -n '__fish_seen_subcommand_from spawn; and __fish_contains_opt agent' -a 'openclaw' -d 'OpenClaw agent'
complete -c agentteam -n '__fish_seen_subcommand_from spawn; and __fish_contains_opt agent' -a 'claude-code' -d 'Claude Code agent'
complete -c agentteam -n '__fish_seen_subcommand_from spawn; and __fish_contains_opt agent' -a 'codex' -d 'Codex agent'
complete -c agentteam -n '__fish_seen_subcommand_from spawn; and __fish_contains_opt agent' -a 'nanobot' -d 'Nanobot agent'

# Priority values
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create; and __fish_contains_opt priority' -a 'low' -d 'Low priority'
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create; and __fish_contains_opt priority' -a 'medium' -d 'Medium priority'
complete -c agentteam -n '__fish_seen_subcommand_from task; and __fish_seen_subcommand_from create; and __fish_contains_opt priority' -a 'high' -d 'High priority'

# Global options
complete -c agentteam -l help -s h -d 'Show help'
complete -c agentteam -l verbose -s v -d 'Verbose output'
