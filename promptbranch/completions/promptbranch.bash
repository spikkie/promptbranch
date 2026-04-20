_promptbranch_complete() {
    local cur prev cmd global_opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    global_opts="--browser-channel --config --debug --dotenv --email --enable-fedcm --headless --keep-no-sandbox --max-retries --password --password-file --profile-dir --project-url --retry-backoff-seconds --service-base-url --service-timeout-seconds --service-token --use-playwright"

    case "$prev" in
        --file|--password-file|--dotenv|--config)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
        --type)
            COMPREPLY=( $(compgen -W "link text file" -- "$cur") )
            return 0
            ;;
    esac

    for word in "${COMP_WORDS[@]:1}"; do
        case "$word" in
            ask|completion|login-check|project-create|project-ensure|project-remove|project-resolve|project-source-add|project-source-remove|prompt|shell|state|state-clear|use)
                cmd="$word"
                break
                ;;
        esac
    done

    if [[ "$cur" == -* ]]; then
        local opts="$global_opts"
        if [[ -n "$cmd" ]]; then
            case "$cmd" in
        login-check) opts="--keep-open $global_opts" ;;
        project-create) opts="--icon --color --memory-mode --keep-open $global_opts" ;;
        project-resolve) opts="--keep-open $global_opts" ;;
        project-ensure) opts="--icon --color --memory-mode --keep-open $global_opts" ;;
        project-remove) opts="--keep-open $global_opts" ;;
        project-source-add) opts="--type --value --file --name --keep-open $global_opts" ;;
        project-source-remove) opts="--exact --keep-open $global_opts" ;;
        state) opts="--json $global_opts" ;;
        prompt) opts="--json $global_opts" ;;
        state-clear) opts=" $global_opts" ;;
        use) opts="--conversation-url --project-name --json --keep-open $global_opts" ;;
        completion) opts=" $global_opts" ;;
        ask) opts="--file --json --conversation-url --keep-open --retries $global_opts" ;;
        shell) opts="--file --json --keep-open --retries $global_opts" ;;
            esac
        fi
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        return 0
    fi

    if [[ -z "$cmd" ]]; then
        COMPREPLY=( $(compgen -W "ask completion login-check project-create project-ensure project-remove project-resolve project-source-add project-source-remove prompt shell state state-clear use" -- "$cur") )
        return 0
    fi

    return 0
}

complete -F _promptbranch_complete promptbranch
