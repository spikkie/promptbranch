# Promptbranch shell aliases and terminal footer

## Alias file

Source the alias file from your shell:

```bash
source /path/to/chatgpt_claudecode_workflow/scripts/promptbranch-aliases.sh
```

Recommended shortcuts:

| Alias | Command |
|---|---|
| `pb` | `promptbranch` |
| `pbv` | `promptbranch version` |
| `pbs` | `promptbranch state` |
| `pbc` | `promptbranch state-clear` |
| `pbwl` | `promptbranch ws list` |
| `pbwu` | `promptbranch ws use` |
| `pbwc` | `promptbranch ws current` |
| `pbtl` | `promptbranch task list` |
| `pbtu` | `promptbranch task use` |
| `pbtc` | `promptbranch task current` |
| `pbtshow` | `promptbranch task show` |
| `pbtmsgs` | `promptbranch task messages list` |
| `pba` | `promptbranch ask` |
| `pbsl` | `promptbranch src list` |
| `pbsa` | `promptbranch src add` |
| `pbsf` | `promptbranch src add --type file --file` |
| `pbst` | `promptbranch src add --type text --value` |
| `pbsk` | `promptbranch src add --type link --value` |
| `pbsr` | `promptbranch src rm` |
| `pbss` | `promptbranch src sync` |
| `pbssn` | `promptbranch src sync . --no-upload` |
| `pbac` | `promptbranch artifact current` |
| `pbal` | `promptbranch artifact list` |
| `pbar` | `promptbranch artifact release` |
| `pbav` | `promptbranch artifact verify` |
| `pbd` | `promptbranch doctor` |
| `pbt` | `promptbranch test-suite` |
| `pbstatus` | compact Promptbranch state line |

Legacy `pbcl`, `pbcu`, `pbcleave`, `pbcshow`, and `pbcsum` remain available for old chat-oriented workflows, but new scripts should use `task` aliases.


## Setup script

```bash
scripts/setup-promptbranch-shell.sh --bash
# or
scripts/setup-promptbranch-shell.sh --zsh
```

To only print the lines without modifying shell config:

```bash
scripts/setup-promptbranch-shell.sh --print-only --tmux
```

## Terminal footer / tmux status line

The status helper resolves the nearest inherited `.pb_profile`, the same model as Promptbranch state.

Plain output:

```bash
scripts/promptbranch-statusline.sh
```

JSON output:

```bash
scripts/promptbranch-statusline.sh --json
```

Tmux status segment:

```tmux
set -g status-right '#(/path/to/chatgpt_claudecode_workflow/scripts/promptbranch-statusline.sh --tmux) %H:%M %Y-%m-%d'
```

Reload tmux:

```bash
tmux source-file ~/.tmux.conf
```
