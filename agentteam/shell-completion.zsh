#compdef agentteam

# AgentTeam Zsh Completion
# Installation: Add to ~/.zshrc:
#   source /path/to/shell-completion.zsh

_agentteam() {
    local -a commands
    commands=(
        'team:Team management'
        'agents:Agent management'
        'task:Task management'
        'inbox:Inbox/messaging'
        'board:Board/dashboard'
        'config:Configuration'
        'spawn:Spawn a new agent'
        'help:Show help'
        'version:Show version'
    )

    local -a team_cmds
    team_cmds=(
        'spawn-team:Create a new team'
        'list:List all teams'
        'status:Show team status'
        'delete:Delete a team'
    )

    local -a agents_cmds
    agents_cmds=(
        'list:List agents in a team'
        'kill:Kill an agent'
    )

    local -a task_cmds
    task_cmds=(
        'create:Create a new task'
        'list:List tasks'
        'update:Update a task'
        'delete:Delete a task'
    )

    local -a inbox_cmds
    inbox_cmds=(
        'send:Send a message'
        'list:List messages'
        'read:Read a message'
    )

    local -a board_cmds
    board_cmds=(
        'serve:Start web dashboard'
        'attach:Attach to team board'
        'token-stats:Show token statistics'
    )

    local -a templates
    templates=(
        'dev-team'
        'dev-team-max'
        'code-review'
        'dev-team-mix'
        'office-team'
    )

    local -a agent_backends
    agent_backends=(
        'openclaw'
        'claude-code'
        'codex'
        'nanobot'
    )

    local -a priorities
    priorities=(
        'low'
        'medium'
        'high'
    )

    local -a global_opts
    global_opts=(
        '--help'
        '--verbose'
    )

    local context state line
    typeset -A opt_args

    _arguments -C \
        '$global_opts' \
        '1:command:->command' \
        '*::arg:->arg' && return

    case $state in
        command)
            _describe 'command' commands
            ;;
        arg)
            case $words[1] in
                team)
                    _arguments -s \
                        '1:subcommand:->team_cmd' \
                        '*::arg:->team_arg'
                    case $state in
                        team_cmd)
                            _describe 'team subcommand' team_cmds
                            ;;
                        team_arg)
                            case $words[2] in
                                spawn-team)
                                    _arguments \
                                        '-d[description]' \
                                        '--description:' \
                                        '-n[leader]' \
                                        '--leader:' \
                                        '-t[template]' \
                                        '--template:->template'
                                    ;;
                                status|delete)
                                    ;;
                                list)
                                    _arguments \
                                        '--format[format]:(table json yaml)' \
                                        '--active[active only]'
                                    ;;
                            esac
                            ;;
                    esac
                    ;;
                agents)
                    _arguments -s \
                        '1:subcommand:->agents_cmd' \
                        '*::arg:->agents_arg'
                    case $state in
                        agents_cmd)
                            _describe 'agents subcommand' agents_cmds
                            ;;
                    esac
                    ;;
                task)
                    _arguments -s \
                        '1:subcommand:->task_cmd' \
                        '*::arg:->task_arg'
                    case $state in
                        task_cmd)
                            _describe 'task subcommand' task_cmds
                            ;;
                        task_arg)
                            case $words[2] in
                                create)
                                    _arguments \
                                        '-t[title]' \
                                        '--title:' \
                                        '-d[description]' \
                                        '--description:' \
                                        '-p[priority]' \
                                        '--priority:->priority' \
                                        '-o[owner]' \
                                        '--owner:'
                                    ;;
                                list)
                                    _arguments \
                                        '--status:' \
                                        '--owner:' \
                                        '--format:->format'
                                    ;;
                                update)
                                    ;;
                            esac
                            ;;
                    esac
                    ;;
                inbox)
                    _arguments -s \
                        '1:subcommand:->inbox_cmd' \
                        '*::arg:->inbox_arg'
                    case $state in
                        inbox_cmd)
                            _describe 'inbox subcommand' inbox_cmds
                            ;;
                    esac
                    ;;
                board)
                    _arguments -s \
                        '1:subcommand:->board_cmd' \
                        '*::arg:->board_arg'
                    case $state in
                        board_cmd)
                            _describe 'board subcommand' board_cmds
                            ;;
                        board_arg)
                            case $words[2] in
                                serve)
                                    _arguments \
                                        '--port:' \
                                        '--host:' \
                                        '--open'
                                    ;;
                            esac
                            ;;
                    esac
                    ;;
                spawn)
                    _arguments \
                        '--team:' \
                        '--agent-name:' \
                        '--task:' \
                        '--agent:->agent'
                    ;;
                config)
                    _arguments \
                        '1:subcommand:->config_cmd'
                    ;;
            esac
            ;;
    esac

    # Handle specific completions
    case $words[$CURRENT] in
        --template|--template=)
            _describe 'template' templates
            ;;
        --agent|--agent=)
            _describe 'agent backend' agent_backends
            ;;
        --priority|--priority=)
            _describe 'priority' priorities
            ;;
    esac
}

_agentteam "$@"
