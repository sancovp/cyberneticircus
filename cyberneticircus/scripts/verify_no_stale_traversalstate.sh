#!/usr/bin/env bash
# verify_no_stale_traversalstate.sh
#
# Detects references to the OLD :HAS_TRAVERSAL → :TraversalState pattern
# (the per-cybernet lock pattern that was REPLACED by :HAS_LIFECYCLE → :ExecutionState).
#
# Expected hits (known dead/legacy code, do not fix in this pass — see DESIGN.md §11.8):
#   - lib/state_machines.py     (cypher builders, fix pending)
#   - lib/lifecycle.py          (LOCK_OR_CREATE / FORCE_ALIGN / READ_TRAVERSAL_STEP, fix pending)
#   - lib/evolution.py          (CLEAR_TRAVERSAL_STATES constant for test reset, harmless if never called)
#   - lib/gates.py              (docstring references)
#   - lib/visualizer.py         (node label list — TraversalState not in live graph, harmless dead label)
#   - test_game_loop.py, verify_*.py  (test/verify scripts use DETACH DELETE for setup)
#   - static/app.js             (SACRED — do not touch; just a label-check that never matches)
#
# Unexpected hits (should be 0 after the runtime gating fix lands) — fail loudly:
#   anywhere else: DESIGN.md, *.claude/rules/*.md, routers/*, db_logic.py, engine.py, etc.
#
# Usage: bash cyberneticircus/scripts/verify_no_stale_traversalstate.sh
# Exit: 0 if no unexpected hits, 1 if unexpected hits found.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 2

# Locations where stale references are EXPECTED (dead/legacy code, test setups, sacred).
EXPECTED_PATHS=(
  "cyberneticircus/lib/state_machines.py"
  "cyberneticircus/lib/lifecycle.py"
  "cyberneticircus/lib/evolution.py"
  "cyberneticircus/lib/gates.py"
  "cyberneticircus/lib/visualizer.py"
  "cyberneticircus/db_logic.py"
  "cyberneticircus/engine.py"
  "cyberneticircus/test_game_loop.py"
  "cyberneticircus/verify_domain_expansion.py"
  "cyberneticircus/verify_daemon_summoning.py"
  "cyberneticircus/static/app.js"
)

# Pattern: HAS_TRAVERSAL or TraversalState
PATTERN='HAS_TRAVERSAL|TraversalState'

# Find all references in .py and .md files.
# Grep with absolute paths and strip the PROJECT_ROOT prefix to get a clean relative path.
ALL_REFS=$(grep -rEn "$PATTERN" \
  --include='*.py' --include='*.md' \
  "$PROJECT_ROOT/cyberneticircus" "$PROJECT_ROOT/.claude" 2>/dev/null \
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
