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
| `pbpl` | `promptbranch project-list` |
| `pbpu` | `promptbranch use` |
| `pbcl` | `promptbranch chat-list` |
| `pbcu` | `promptbranch chat-use` |
| `pbcshow` | `promptbranch chat-show` |
| `pba` | `promptbranch ask` |
| `pbsl` | `promptbranch project-source-list` |
| `pbsa` | `promptbranch project-source-add` |
| `pbsf` | `promptbranch project-source-add --file` |
| `pbst` | `promptbranch project-source-add --text` |
| `pbsk` | `promptbranch project-source-add --link` |
| `pbsr` | `promptbranch project-source-remove` |
| `pbt` | `promptbranch test-suite` |
| `pbstatus` | compact Promptbranch state line |

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
