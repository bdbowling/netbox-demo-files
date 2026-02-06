#!/usr/bin/env bash
# netbox-changelog.sh
# Version: 1.0.0
# Last updated: 2026-01-28
#
# Usage examples:
#   ./netbox-changelog.sh latest
#   ./netbox-changelog.sh who
#   ./netbox-changelog.sh today
#   ./netbox-changelog.sh since "2026-01-28T00:00:00Z"
#   ./netbox-changelog.sh user admin
#   ./netbox-changelog.sh type dcim.device
#   ./netbox-changelog.sh action update
#   ./netbox-changelog.sh object-id 1234
#   ./netbox-changelog.sh csv 500
#
# Requirements:
#   - curl
#   - jq (for formatted outputs)

set -euo pipefail

: "${NETBOX_TOKEN:?NETBOX_TOKEN is required. Export it first (see script header).}"
BASE_URL="${BASE_URL:-https://yourinstance.cloud.netboxapp.com}"

AUTH_HEADERS=(
  -H "Authorization: Token ${NETBOX_TOKEN}"
  -H "Accept: application/json"
)

OBJ_CHANGES_ENDPOINT="${BASE_URL}/api/core/object-changes/"

die() { echo "Error: $*" >&2; exit 1; }

need_jq() {
  command -v jq >/dev/null 2>&1 || die "jq is required for this command. Install jq and try again."
}

api_get() {
  local url="$1"
  curl -sS "${AUTH_HEADERS[@]}" "$url"
}

latest_json() {
  local limit="${1:-100}"
  api_get "${OBJ_CHANGES_ENDPOINT}?ordering=-time&limit=${limit}"
}

cmd_latest() {
  local limit="${1:-100}"
  latest_json "$limit" | jq
}

cmd_who() {
  need_jq
  local limit="${1:-100}"
  latest_json "$limit"   | jq -r '.results[] |
    "\(.time) | \(.user.username // "unknown") | \(.action.value // .action) | \(.changed_object_type // "unknown") | \(.object_repr // "unknown")"'
}

cmd_today() {
  need_jq
  local date_utc
  date_utc="$(date -u +%F)T00:00:00Z"
  api_get "${OBJ_CHANGES_ENDPOINT}?time__gte=${date_utc}&ordering=-time&limit=1000" | jq
}

cmd_since() {
  need_jq
  local iso="${1:-}"
  [[ -n "$iso" ]] || die "since requires an ISO timestamp, e.g. 2026-01-28T00:00:00Z"
  api_get "${OBJ_CHANGES_ENDPOINT}?time__gte=${iso}&ordering=-time&limit=1000" | jq
}

cmd_user() {
  need_jq
  local username="${1:-}"
  [[ -n "$username" ]] || die "user requires a username"
  api_get "${OBJ_CHANGES_ENDPOINT}?user__username=${username}&ordering=-time&limit=1000" | jq
}

cmd_type() {
  need_jq
  local objtype="${1:-}"
  [[ -n "$objtype" ]] || die "type requires a changed_object_type (e.g. dcim.device)"
  api_get "${OBJ_CHANGES_ENDPOINT}?changed_object_type=${objtype}&ordering=-time&limit=1000" | jq
}

cmd_action() {
  need_jq
  local action="${1:-}"
  [[ -n "$action" ]] || die "action requires create|update|delete"
  api_get "${OBJ_CHANGES_ENDPOINT}?action=${action}&ordering=-time&limit=1000" | jq
}

cmd_object_id() {
  need_jq
  local id="${1:-}"
  [[ -n "$id" ]] || die "object-id requires a numeric id"
  api_get "${OBJ_CHANGES_ENDPOINT}?changed_object_id=${id}&ordering=-time&limit=1000" | jq
}

cmd_group_request() {
  need_jq
  local limit="${1:-200}"
  api_get "${OBJ_CHANGES_ENDPOINT}?ordering=-time&limit=${limit}"   | jq -r '
    .results
    | group_by(.request_id)[]
    | "REQUEST: \((.[0].request_id // "no_request_id")) USER: \((.[0].user.username // "unknown"))\n"
      + (map("  - \(.time) \(.action.value // .action) \(.changed_object_type // "unknown") \(.object_repr // "unknown")") | join("\n"))
      + "\n"
  '
}

cmd_csv() {
  need_jq
  local limit="${1:-1000}"
  api_get "${OBJ_CHANGES_ENDPOINT}?ordering=-time&limit=${limit}"   | jq -r '
    .results[]
    | [.time, (.user.username // "unknown"), (.action.value // .action), (.changed_object_type // "unknown"), (.object_repr // "unknown")]
    | @csv
  '
}

usage() {
  cat <<'EOF'
netbox-changelog.sh (v1.0.0)

Required env vars:
  export NETBOX_TOKEN="..."
Optional:
  export BASE_URL="https://yourinstance.cloud.netboxapp.com"

Commands:
  latest [N]          Pretty JSON of latest N changes (default 100)
  who [N]             Human-readable list of latest N changes (default 100)
  today               Pretty JSON of changes since 00:00 UTC today
  since <ISO>         Pretty JSON since ISO time, e.g. 2026-01-28T00:00:00Z
  user <username>     Pretty JSON filtered by username
  type <objtype>      Pretty JSON filtered by changed_object_type (e.g. dcim.device)
  action <a>          Pretty JSON filtered by action (create|update|delete)
  object-id <id>      Pretty JSON filtered by changed_object_id
  group-request [N]   Group latest N changes by request_id (default 200)
  csv [N]             CSV rows for latest N changes (default 1000)

EOF
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    latest) cmd_latest "${1:-100}" ;;
    who) cmd_who "${1:-100}" ;;
    today) cmd_today ;;
    since) cmd_since "${1:-}" ;;
    user) cmd_user "${1:-}" ;;
    type) cmd_type "${1:-}" ;;
    action) cmd_action "${1:-}" ;;
    object-id) cmd_object_id "${1:-}" ;;
    group-request) cmd_group_request "${1:-200}" ;;
    csv) cmd_csv "${1:-1000}" ;;
    ""|help|-h|--help) usage ;;
    *) die "Unknown command: $cmd (run with --help)" ;;
  esac
}

main "$@"
