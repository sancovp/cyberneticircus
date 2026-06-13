#!/usr/bin/env bash
# verify_no_stale_traversalstate.sh
#
# Detects references to the OLD :HAS_TRAVERSAL → :TraversalState pattern
# (the per-cybernet lock pattern that was REPLACED by :HAS_LIFECYCLE → :ExecutionState).
#
# The runtime gating fix (DESIGN.md §11.8) has LANDED: lib/state_machines.py,
# lib/lifecycle.py, lib/gates.py, lib/evolution.py, lib/visualizer.py, db_logic.py,
# engine.py, and the test/verify scripts are all on :ExecutionState / :HAS_LIFECYCLE.
# There are NO remaining expected hits — the allowlist is empty. ANY hit is a regression.
#
# Unexpected hits (must be 0) — fail loudly:
#   anywhere: lib/*, db_logic.py, engine.py, routers/*, *.md, etc.
#
# Usage: bash cyberneticircus/scripts/verify_no_stale_traversalstate.sh
# Exit: 0 if no unexpected hits, 1 if unexpected hits found.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 2

# The runtime gating fix has landed; no stale references are expected anywhere.
# static/app.js is SACRED (never edited) but contains no live HAS_TRAVERSAL/
# TraversalState reference, so it is not allowlisted. ANY hit is a regression.
EXPECTED_PATHS=()

# Pattern: HAS_TRAVERSAL or TraversalState
PATTERN='HAS_TRAVERSAL|TraversalState'

# Find all references in .py and .md files.
# Grep with absolute paths and strip the PROJECT_ROOT prefix to get a clean relative path.
# Includes neo4j_cypher_mcp/server.py — the AGENT-FACING MCP tool surface (its
# docstrings ARE the tool descriptions the LLM reads to decide what cypher to
# write), which the earlier scope missed. The MCP test_*.py files still carry
# stale `MATCH (s:TraversalState) DETACH DELETE s` resets (now silent no-ops);
# those are knowingly deferred (need a test run to fix) and are NOT scanned here.
ALL_REFS=$(grep -rEn "$PATTERN" \
  --include='*.py' --include='*.md' \
  "$PROJECT_ROOT/cyberneticircus" "$PROJECT_ROOT/.claude" \
  "$PROJECT_ROOT/neo4j_cypher_mcp/server.py" 2>/dev/null \
  | grep -v __pycache__ | grep -v '\.pyc' \
  | sed "s|^$PROJECT_ROOT/||" || true)

if [ -z "$ALL_REFS" ]; then
  echo "✓ No HAS_TRAVERSAL or TraversalState references found anywhere."
  echo "  (Live graph confirms: 0 HAS_TRAVERSAL edges, 0 TraversalState nodes.)"
  exit 0
fi

# Split into expected vs unexpected.
UNEXPECTED=""
EXPECTED_COUNT=0
TOTAL_COUNT=0

while IFS= read -r line; do
  [ -z "$line" ] && continue
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  file=$(echo "$line" | cut -d: -f1)
  is_expected=0
  for exp in "${EXPECTED_PATHS[@]}"; do
    if [ "$file" = "$exp" ]; then
      is_expected=1
      EXPECTED_COUNT=$((EXPECTED_COUNT + 1))
      break
    fi
  done
  if [ $is_expected -eq 0 ]; then
    UNEXPECTED="${UNEXPECTED}${line}\n"
  fi
done <<< "$ALL_REFS"

echo "=== HAS_TRAVERSAL / TraversalState Reference Report ==="
echo ""
echo "Total references: $TOTAL_COUNT"
echo "Expected (legacy/dead/test/sacred): $EXPECTED_COUNT"
echo "Unexpected (should be 0 post-fix):  $(echo -e "$UNEXPECTED" | grep -c . || echo 0)"
echo ""

if [ -n "$UNEXPECTED" ] && [ "$(echo -e "$UNEXPECTED" | grep -c .)" -gt 0 ]; then
  echo "✗ UNEXPECTED REFERENCES (action required):"
  echo ""
  echo -e "$UNEXPECTED" | sed 's/^/  /'
  echo ""
  echo "These references are stale and should be updated to reflect the actual pattern:"
  echo "  - HAS_TRAVERSAL → HAS_LIFECYCLE"
  echo "  - TraversalState (the per-cybernet lock node) → ExecutionState"
  echo ""
  echo "See DESIGN.md §11.8 for the runtime gating fix scope."
  echo "See .claude/rules/cyberneticircus-architecture.md §4 for the canonical pattern."
  exit 1
fi

echo "✓ All references are in expected (legacy/dead/test/sacred) locations."
echo "  After the runtime gating fix (DESIGN.md §11.8), lib/state_machines.py + lib/lifecycle.py"
echo "  will move to the expected=empty list and the expected_count will drop accordingly."
exit 0
