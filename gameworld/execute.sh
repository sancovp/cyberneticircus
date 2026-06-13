#!/usr/bin/env bash
# =============================================================================
# execute.sh — the CybernetiCircus economy engine (Phase 04: Autopoietic Economics)
#
# Neo4j IS the source of truth; every verb below is a thin curl wrapper over the
# live graph API (default http://localhost:8000 — override with $CYBERCITY_API).
# The visualizer at the same URL is the GM's table view (the operational mirror).
#
# Verbs:
#   status                   scoreboard: all Cybernets + economy fields
#   quests                   list StateMachines (id, name, description)
#   inspect <cybernet>       full node properties + live ExecutionState view
#   equip <cybernet> <sm_id> POST /api/equip  {character_name, state_machine_id}
#   act <cybernet> '<cypher>' POST /api/query with cybernet_name (the gated verb)
#   progress <cybernet>      POST /api/traversal/progress
#   mirror                   dashboard URL + last 5 agent_logs entries
# =============================================================================
set -euo pipefail

API="${CYBERCITY_API:-http://localhost:8000}"

# --- plumbing ----------------------------------------------------------------

need() { command -v "$1" >/dev/null 2>&1 || { echo "error: '$1' is required" >&2; exit 1; }; }
need curl
need jq

# api_call METHOD PATH [JSON_BODY]
# Prints the response body; pretty-prints when it is JSON, raw otherwise.
# Exits nonzero on transport failure or HTTP >= 400 (body still shown).
api_call() {
  local method="$1" path="$2" body="${3:-}"
  local resp http
  if [ -n "$body" ]; then
    resp=$(curl -sS -X "$method" "$API$path" \
      -H 'Content-Type: application/json' \
      -d "$body" \
      -w $'\n%{http_code}') || { echo "error: cannot reach $API$path" >&2; exit 1; }
  else
    resp=$(curl -sS -X "$method" "$API$path" \
      -w $'\n%{http_code}') || { echo "error: cannot reach $API$path" >&2; exit 1; }
  fi
  http="${resp##*$'\n'}"
  resp="${resp%$'\n'*}"
  if jq -e . >/dev/null 2>&1 <<<"$resp"; then
    jq . <<<"$resp"
  else
    printf '%s\n' "$resp"
  fi
  if [ "$http" -ge 400 ]; then
    echo "error: HTTP $http from $method $path" >&2
    return 1
  fi
}

# raw_query CYPHER -> ungated read of the graph (no cybernet_name)
raw_query() {
  local cypher="$1"
  api_call POST /api/query "$(jq -n --arg q "$cypher" '{query: $q}')"
}

usage() {
  cat <<EOF
usage: $(basename "$0") <verb> [args]

  status                     scoreboard of all Cybernets (persona, fitness, tokens, cost)
  quests                     list StateMachines (id, name, description)
  inspect <cybernet>         full properties + ExecutionState (step, turn, phase)
  equip <cybernet> <sm_id>   equip a StateMachine (creates fresh ExecutionState at entry step)
  act <cybernet> '<cypher>'  run a cypher AS that cybernet (gated by its current step)
  progress <cybernet>        advance the active ExecutionState one step
  mirror                     dashboard URL + last 5 agent_logs entries

  API base: $API   (override with \$CYBERCITY_API)
EOF
  exit 1
}

# --- verbs -------------------------------------------------------------------

cmd_status() {
  echo "== CYBERNET SCOREBOARD (live graph @ $API) =="
  raw_query 'MATCH (c:Cybernet)
             RETURN c.name AS name,
                    c.persona AS persona,
                    c.fitness_score AS fitness_score,
                    c.total_tokens_consumed AS total_tokens_consumed,
                    c.accumulated_cost AS accumulated_cost
             ORDER BY coalesce(c.fitness_score, -1) DESC, name' \
  | jq -r '
      (["NAME","PERSONA","FITNESS","TOKENS","COST"] | @tsv),
      (.[] | [
        (.name // "-"),
        (.persona // "-"),
        (.fitness_score // "-" | tostring),
        (.total_tokens_consumed // "-" | tostring),
        (.accumulated_cost // "-" | tostring)
      ] | @tsv)' \
  | column -t -s $'\t'
}

cmd_quests() {
  echo "== STATEMACHINES (the equippable quest list) =="
  raw_query 'MATCH (sm:StateMachine)
             RETURN sm.id AS id, sm.name AS name, sm.description AS description
             ORDER BY sm.id' \
  | jq -r '.[] | "* \(.id)\n    name: \(.name // "-")\n    desc: \(.description // "-")"'
}

cmd_inspect() {
  local name="$1"
  echo "== GRAPH NODE PROPERTIES: $name =="
  api_call POST /api/query "$(jq -n --arg n "$name" \
    '{query: "MATCH (c:Cybernet {name: $name}) RETURN properties(c) AS props", parameters: {name: $n}}')" \
  | jq '.[].props'
  echo
  echo "== LIVE EXECUTION STATE (GET /api/status/$name) =="
  api_call GET "/api/status/$name" \
  | jq '{equipped_sm_id, equipped_sm_name, turn_number, phase,
         current_step_id, current_step_text, required_pattern,
         pattern_description, current_layer, completed_layers, call_stack}'
}

cmd_equip() {
  local name="$1" sm_id="$2"
  echo "== EQUIP: $name <- $sm_id =="
  api_call POST /api/equip "$(jq -n --arg c "$name" --arg s "$sm_id" \
    '{character_name: $c, state_machine_id: $s}')"
}

cmd_act() {
  local name="$1" cypher="$2"
  echo "== ACT AS $name (gated by current step) =="
  api_call POST /api/query "$(jq -n --arg q "$cypher" --arg c "$name" \
    '{query: $q, cybernet_name: $c}')"
}

cmd_progress() {
  local name="$1"
  echo "== PROGRESS: $name =="
  api_call POST /api/traversal/progress "$(jq -n --arg c "$name" \
    '{cybernet_name: $c}')"
}

cmd_mirror() {
  echo "== THE OPERATIONAL MIRROR =="
  echo "dashboard: $API"
  echo
  api_call GET /api/agent_logs \
  | jq '{active_cybernet, active_step_id, last_5_logs: (.logs[-5:])}'
}

# --- dispatch ----------------------------------------------------------------

[ $# -ge 1 ] || usage
verb="$1"; shift

case "$verb" in
  status)   cmd_status ;;
  quests)   cmd_quests ;;
  inspect)  [ $# -eq 1 ] || usage; cmd_inspect "$1" ;;
  equip)    [ $# -eq 2 ] || usage; cmd_equip "$1" "$2" ;;
  act)      [ $# -eq 2 ] || usage; cmd_act "$1" "$2" ;;
  progress) [ $# -eq 1 ] || usage; cmd_progress "$1" ;;
  mirror)   cmd_mirror ;;
  *)        usage ;;
esac
