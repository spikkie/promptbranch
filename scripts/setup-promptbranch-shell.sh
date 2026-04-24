#!/usr/bin/env bash
set -euo pipefail

# Install Promptbranch shell aliases and optionally print tmux footer instructions.
# This script is intentionally conservative: it appends one managed source line only.

shell_rc=""
install_tmux="false"
print_only="false"

usage() {
  cat <<'HELP'
Usage: setup-promptbranch-shell.sh [--bash|--zsh] [--rc FILE] [--tmux] [--print-only]

Installs Promptbranch aliases by adding this line to your shell rc file:
  source <repo>/scripts/promptbranch-aliases.sh

Useful aliases include:
  pbs   -> promptbranch state
  pbv   -> promptbranch version
  pba   -> promptbranch ask
  pbsl  -> promptbranch project-source-list
  pbsf  -> promptbranch project-source-add --file
  pbsr  -> promptbranch project-source-remove
  pbstatus -> <repo>/scripts/promptbranch-statusline.sh

For tmux footer/status line, add something like:
  set -g status-right '#(<repo>/scripts/promptbranch-statusline.sh --tmux) %H:%M %Y-%m-%d'
HELP
}

while [ $# -gt 0 ]; do
  case "$1" in
    --bash) shell_rc="$HOME/.bashrc" ;;
    --zsh) shell_rc="$HOME/.zshrc" ;;
    --rc)
      shift
      shell_rc="${1:-}"
      ;;
    --tmux) install_tmux="true" ;;
    --print-only) print_only="true" ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
alias_file="$script_dir/promptbranch-aliases.sh"
status_script="$script_dir/promptbranch-statusline.sh"
source_line="source '$alias_file'"

if [ -z "$shell_rc" ]; then
  case "${SHELL:-}" in
    */zsh) shell_rc="$HOME/.zshrc" ;;
    *) shell_rc="$HOME/.bashrc" ;;
  esac
fi

if [ "$print_only" = "true" ]; then
  echo "$source_line"
  if [ "$install_tmux" = "true" ]; then
    echo "set -g status-right '#($status_script --tmux) %H:%M %Y-%m-%d'"
  fi
  exit 0
fi

touch "$shell_rc"
if ! grep -Fq "$alias_file" "$shell_rc"; then
  {
    echo ""
    echo "# Promptbranch aliases"
    echo "$source_line"
  } >> "$shell_rc"
  echo "Added Promptbranch aliases to $shell_rc"
else
  echo "Promptbranch aliases already configured in $shell_rc"
fi

if [ "$install_tmux" = "true" ]; then
  cat <<MSG

Add this to ~/.tmux.conf if you want Promptbranch state in the tmux footer/status line:

set -g status-right '#($status_script --tmux) %H:%M %Y-%m-%d'

Then reload tmux:
  tmux source-file ~/.tmux.conf
MSG
fi

cat <<MSG

Reload your shell:
  source "$shell_rc"

Check:
  pbs
  pbstatus
MSG
