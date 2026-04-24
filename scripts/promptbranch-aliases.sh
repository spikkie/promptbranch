# Promptbranch shell aliases.
# Source this file from ~/.bashrc or ~/.zshrc:
#   source /path/to/chatgpt_claudecode_workflow/scripts/promptbranch-aliases.sh

# Core
alias pb='promptbranch'
alias pbv='promptbranch version'
alias pbs='promptbranch state'
alias pbc='promptbranch state-clear'

# Workspace / project
alias pbpl='promptbranch project-list'
alias pbpu='promptbranch use'
alias pbpc='promptbranch state'
alias pbpr='promptbranch project-resolve'
alias pbpcreate='promptbranch project-create'
alias pbprm='promptbranch project-remove'

# Task / chat
alias pbcl='promptbranch chat-list'
alias pbcu='promptbranch chat-use'
alias pbcleave='promptbranch chat-leave'
alias pbcshow='promptbranch chat-show'
alias pbcsum='promptbranch chat-summarize'

# Ask / execution
alias pba='promptbranch ask'

# Sources
alias pbsl='promptbranch project-source-list'
alias pbsa='promptbranch project-source-add'
alias pbsf='promptbranch project-source-add --file'
alias pbst='promptbranch project-source-add --text'
alias pbsk='promptbranch project-source-add --link'
alias pbsr='promptbranch project-source-remove'

# Service / diagnostics
alias pbd='promptbranch doctor'
alias pbt='promptbranch test-suite'

# Compact status helper, if this repo's scripts directory is on disk.
_pb_aliases_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]:-${(%):-%x}}")" 2>/dev/null && pwd 2>/dev/null)"
if [ -n "${_pb_aliases_dir}" ] && [ -x "${_pb_aliases_dir}/promptbranch-statusline.sh" ]; then
  alias pbstatus="${_pb_aliases_dir}/promptbranch-statusline.sh"
fi
unset _pb_aliases_dir
