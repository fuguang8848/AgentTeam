#!/bin/bash
# AgentTeam Bash Completion
# Installation: Add to ~/.bashrc:
#   source /path/to/shell-completion.sh

_agentteam_completion() {
    local cur prev words cword
    _init_completion || return

    # Main commands
    local commands="team agents task inbox board config spawn help version"

    # Team subcommands
    local team_cmds="spawn-team list status delete"

    # Agents subcommands
    local agents_cmds="list kill"

    # Task subcommands
    local task_cmds="create list update delete"

    # Inbox subcommands
    local inbox_cmds="send list read"

    # Board subcommands
    local board_cmds="serve attach token-stats"

    # Options
    local options="--help --verbose --format --team --agent-name --task --status --owner --priority"

    # Team templates
    local templates="dev-team dev-team-max code-review dev-team-mix office-team"

    # Agents
    local agents="openclaw claude-code codex nanobot"

    # Handle different contexts
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
    elif [[ $cword -eq 2 ]]; then
        case "${words[1]}" in
            team)
                COMPREPLY=( $(compgen -W "$team_cmds" -- "$cur") )
                ;;
            agents)
                COMPREPLY=( $(compgen -W "$agents_cmds" -- "$cur") )
                ;;
            task)
                COMPREPLY=( $(compgen -W "$task_cmds" -- "$cur") )
                ;;
            inbox)
                COMPREPLY=( $(compgen -W "$inbox_cmds" -- "$cur") )
                ;;
            board)
                COMPREPLY=( $(compgen -W "$board_cmds" -- "$cur") )
                ;;
            spawn)
                COMPREPLY=( $(compgen -W "$options" -- "$cur") )
                ;;
        esac
    elif [[ $cword -eq 3 ]]; then
        case "${words[2]}" in
            spawn-team)
                # Team name - no completion
                ;;
            status|delete)
                # Team name - no completion
                ;;
            list)
                COMPREPLY=( $(compgen -W "--format --active" -- "$cur") )
                ;;
            spawn)
                COMPREPLY=( $(compgen -W "$options" -- "$cur") )
                ;;
            -t|--template)
                COMPREPLY=( $(compgen -W "$templates" -- "$cur") )
                ;;
            --agent)
                COMPREPLY=( $(compgen -W "$agents" -- "$cur") )
                ;;
        esac
    else
        # Additional options based on context
        case "${words[*]}" in
            *"team spawn-team"*)
                COMPREPLY=( $(compgen -W "-d --description -n --leader -t --template" -- "$cur") )
                ;;
            *"task create"*)
                COMPREPLY=( $(compgen -W "-d --description -p --priority -o --owner" -- "$cur") )
                ;;
            *"board serve"*)
                COMPREPLY=( $(compgen -W "--port --host --open" -- "$cur") )
                ;;
        esac
    fi

    # Common options always available
    COMPREPLY+=( $(compgen -W "--help --verbose" -- "$cur") )
}

complete -F _agentteam_completion agentteam
