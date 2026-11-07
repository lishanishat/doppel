#!/usr/bin/env bash
# Local demo: correct PR, planted bug, chaos recovery. Real engine, cached twins.
set -u
PY=${PY:-.venv/bin/python}
PR=demo_target/prorate_refund/ai_pr/billing.py
T0=$(date +%s)

step() { # label, regex-for-verdict, cmd...
  local label=$1 pat=$2; shift 2
  local s=$(date +%s) out v
  out=$("$@" 2>&1)
  v=$(printf '%s\n' "$out" | grep -oE "$pat" | head -1 | tr -d '=: ')
  printf '%-28s %-10s %ss\n' "$label" "${v:-NO-VERDICT}" "$(( $(date +%s) - s ))"
}

step "correct AI PR"   '== [A-Z]+ =='  $PY -m engine.cli verify --fn prorate_refund --pr $PR
step "planted bug"     '[A-Z]+: '      $PY scripts/plant_bug.py $PR 44 off_by_one_const --variant 1
step "recovery (chaos)" '== [A-Z]+ ==' $PY -m engine.cli verify --fn prorate_refund --pr $PR --chaos twin_b
echo "total: $(( $(date +%s) - T0 ))s"
