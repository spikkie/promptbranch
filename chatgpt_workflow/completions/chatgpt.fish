complete -c chatgpt -f
complete -c chatgpt -l browser-channel -r
complete -c chatgpt -l config -r
complete -c chatgpt -l debug
complete -c chatgpt -l dotenv -r
complete -c chatgpt -l email -r
complete -c chatgpt -l enable-fedcm
complete -c chatgpt -l headless
complete -c chatgpt -l keep-no-sandbox
complete -c chatgpt -l max-retries -r
complete -c chatgpt -l password -r
complete -c chatgpt -l password-file -r
complete -c chatgpt -l profile-dir -r
complete -c chatgpt -l project-url -r
complete -c chatgpt -l retry-backoff-seconds -r
complete -c chatgpt -l service-base-url -r
complete -c chatgpt -l service-timeout-seconds -r
complete -c chatgpt -l service-token -r
complete -c chatgpt -l use-playwright
complete -c chatgpt -n '__fish_use_subcommand' -a 'ask'
complete -c chatgpt -n '__fish_use_subcommand' -a 'completion'
complete -c chatgpt -n '__fish_use_subcommand' -a 'login-check'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-create'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-ensure'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-remove'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-resolve'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-source-add'
complete -c chatgpt -n '__fish_use_subcommand' -a 'project-source-remove'
complete -c chatgpt -n '__fish_use_subcommand' -a 'prompt'
complete -c chatgpt -n '__fish_use_subcommand' -a 'shell'
complete -c chatgpt -n '__fish_use_subcommand' -a 'state'
complete -c chatgpt -n '__fish_use_subcommand' -a 'state-clear'
complete -c chatgpt -n '__fish_use_subcommand' -a 'use'
complete -c chatgpt -n '__fish_seen_subcommand_from login-check' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-create' -l icon -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-create' -l color -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-create' -l memory-mode -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-create' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-resolve' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-ensure' -l icon -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-ensure' -l color -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-ensure' -l memory-mode -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-ensure' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-remove' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add' -l type -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add' -l value -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add' -l file -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add' -l name -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-remove' -l exact
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-remove' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from state' -l json
complete -c chatgpt -n '__fish_seen_subcommand_from prompt' -l json
complete -c chatgpt -n '__fish_seen_subcommand_from use' -l conversation-url -r
complete -c chatgpt -n '__fish_seen_subcommand_from use' -l project-name -r
complete -c chatgpt -n '__fish_seen_subcommand_from use' -l json
complete -c chatgpt -n '__fish_seen_subcommand_from use' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from ask' -l file -r
complete -c chatgpt -n '__fish_seen_subcommand_from ask' -l json
complete -c chatgpt -n '__fish_seen_subcommand_from ask' -l conversation-url -r
complete -c chatgpt -n '__fish_seen_subcommand_from ask' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from ask' -l retries -r
complete -c chatgpt -n '__fish_seen_subcommand_from shell' -l file -r
complete -c chatgpt -n '__fish_seen_subcommand_from shell' -l json
complete -c chatgpt -n '__fish_seen_subcommand_from shell' -l keep-open
complete -c chatgpt -n '__fish_seen_subcommand_from shell' -l retries -r
complete -c chatgpt -n '__fish_seen_subcommand_from project-source-add; and __fish_prev_arg_in --type' -a 'link text file'
