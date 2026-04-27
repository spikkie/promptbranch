# Promptbranch shell aliases.
# Source this file from ~/.bashrc or ~/.zshrc:
#   source /path/to/chatgpt_claudecode_workflow/scripts/promptbranch-aliases.sh

# Core
alias pb='promptbranch'
alias pbv='promptbranch version'
alias pbs='promptbranch state'
alias pbc='promptbranch state-clear'

# Workspace / project
alias pbwl='promptbranch ws list'
alias pbwu='promptbranch ws use'
alias pbwc='promptbranch ws current'
alias pbwleave='promptbranch ws leave'
alias pbpl='promptbranch project-list'        # legacy project alias
alias pbpu='promptbranch use'                 # legacy project/chat selector
alias pbpc='promptbranch state'
alias pbpr='promptbranch project-resolve'
alias pbpcreate='promptbranch project-create'
alias pbprm='promptbranch project-remove'

# Task / chat
alias pbtl='promptbranch task list'
alias pbtu='promptbranch task use'
alias pbtc='promptbranch task current'
alias pbtleave='promptbranch task leave'
alias pbtshow='promptbranch task show'
alias pbtmsgs='promptbranch task messages list'
alias pbcl='promptbranch chat-list'           # legacy chat alias
alias pbcu='promptbranch chat-use'            # legacy chat alias
alias pbcleave='promptbranch chat-leave'      # legacy chat alias
alias pbcshow='promptbranch chat-show'        # legacy chat alias
alias pbcsum='promptbranch chat-summarize'    # legacy chat alias

# Ask / execution
alias pba='promptbranch ask'

# Sources
alias pbsl='promptbranch src list'
alias pbsa='promptbranch src add'
alias pbsf='promptbranch src add --type file --file'
alias pbst='promptbranch src add --type text --value'
alias pbsk='promptbranch src add --type link --value'
alias pbsr='promptbranch src rm'
alias pbss='promptbranch src sync'
alias pbssn='promptbranch src sync . --no-upload'

# Artifacts
alias pbac='promptbranch artifact current'
alias pbal='promptbranch artifact list'
alias pbar='promptbranch artifact release'
alias pbav='promptbranch artifact verify'

# Service / diagnostics
alias pbd='promptbranch doctor'
alias pbt='promptbranch test-suite'

# Compact status helper, if this repo's scripts directory is on disk.
_pb_aliases_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]:-${(%):-%x}}")" 2>/dev/null && pwd 2>/dev/null)"
if [ -n "${_pb_aliases_dir}" ] && [ -x "${_pb_aliases_dir}/promptbranch-statusline.sh" ]; then
  alias pbstatus="${_pb_aliases_dir}/promptbranch-statusline.sh"
fi
unset _pb_aliases_dir
