#!/usr/bin/env bash
set -euo pipefail

# Print compact Promptbranch state for shell prompts, tmux status bars, or terminal footers.
# It resolves the nearest ancestor .pb_profile directory, matching promptbranch state behavior.
# Usage:
#   scripts/promptbranch-statusline.sh
#   scripts/promptbranch-statusline.sh --tmux
#   scripts/promptbranch-statusline.sh --json
#   scripts/promptbranch-statusline.sh --path /repo/subdir

mode="plain"
start_dir="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --tmux) mode="tmux" ;;
    --json) mode="json" ;;
    --plain) mode="plain" ;;
    --path)
      shift
      start_dir="${1:-$PWD}"
      ;;
    --help|-h)
      cat <<'HELP'
Usage: promptbranch-statusline.sh [--plain|--tmux|--json] [--path DIR]

Shows compact Promptbranch state from the nearest inherited .pb_profile.
Useful examples:
  # Bash/Zsh prompt segment
  export PS1='$(/path/scripts/promptbranch-statusline.sh) '$PS1

  # tmux footer/status line
  set -g status-right '#(/path/scripts/promptbranch-statusline.sh --tmux) %H:%M %Y-%m-%d'
HELP
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

find_profile_dir() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    dir="$(dirname -- "$dir")"
  fi
  dir="$(cd -- "$dir" 2>/dev/null && pwd -P)" || return 1
  while :; do
    if [ -d "$dir/.pb_profile" ]; then
      printf '%s\n' "$dir/.pb_profile"
      return 0
    fi
    [ "$dir" = "/" ] && return 1
    dir="$(dirname -- "$dir")"
  done
}

json_get_string() {
  local key="$1"
  local file="$2"
  [ -f "$file" ] || return 0
  # Sufficient for promptbranch's simple state JSON string fields.
  sed -nE 's/^[[:space:]]*"'"$key"'"[[:space:]]*:[[:space:]]*"(.*)"[[:space:]]*,?[[:space:]]*$/\1/p' "$file" | head -n 1 | sed 's/\\"/"/g'
}

compact_tail() {
  local value="${1:-}"
  [ -z "$value" ] && { printf '%s' '-'; return; }
  value="${value%/}"
  value="${value##*/}"
  if [ "${#value}" -gt 29 ]; then
    printf '%s…' "${value:0:28}"
  else
    printf '%s' "$value"
  fi
}

truncate_to() {
  local value="$1"
  local max="$2"
  if [ "${#value}" -gt "$max" ]; then
    printf '%s…' "${value:0:$((max-1))}"
  else
    printf '%s' "$value"
  fi
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

profile_dir="$(find_profile_dir "$start_dir" 2>/dev/null || true)"
state_file=""
project_name=""
project_url=""
conversation_url=""
conversation_id=""

if [ -n "$profile_dir" ]; then
  state_file="$profile_dir/.promptbranch_state.json"
  if [ -f "$state_file" ]; then
    project_name="$(json_get_string project_name "$state_file")"
    project_url="$(json_get_string project_url "$state_file")"
    conversation_url="$(json_get_string conversation_url "$state_file")"
    conversation_id="$(json_get_string conversation_id "$state_file")"
  fi
fi

if [ -n "$project_name" ]; then
  project_display="$project_name"
else
  project_display="$(compact_tail "$project_url")"
fi

if [ -n "$conversation_id" ]; then
  task_display="$conversation_id"
else
  task_display="$(compact_tail "$conversation_url")"
fi

project_display="$(truncate_to "$project_display" 32)"
task_display="$(truncate_to "$task_display" 24)"

case "$mode" in
  json)
    printf '{"has_profile":%s,"has_state":%s,"profile_dir":"%s","state_file":"%s","project":"%s","task":"%s"}\n' \
      "$([ -n "$profile_dir" ] && echo true || echo false)" \
      "$([ -n "$state_file" ] && [ -f "$state_file" ] && echo true || echo false)" \
      "$(json_escape "$profile_dir")" \
      "$(json_escape "$state_file")" \
      "$(json_escape "$project_display")" \
      "$(json_escape "$task_display")"
    ;;
  tmux)
    if [ -z "$profile_dir" ]; then
      printf '%s\n' '#[fg=colour240]pb:-'
    else
      printf '#[fg=colour45]pb #[fg=colour250]ws:%s #[fg=colour244]task:%s\n' "$project_display" "$task_display"
    fi
    ;;
  *)
    if [ -z "$profile_dir" ]; then
      printf '%s\n' 'pb:-'
    else
      printf 'pb ws:%s task:%s\n' "$project_display" "$task_display"
    fi
    ;;
esac

exit 0
