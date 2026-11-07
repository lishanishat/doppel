#!/usr/bin/env bash
# Verify your own version of prorate_refund with Doppel (live "judge edits the code" demo).
#   scripts/check.sh path/to/file.py
# Prints the verdict, the input where versions disagree, each version's answer, and the time.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-.venv/bin/python}
start=$(date +%s)
$PY -m engine.cli verify --fn prorate_refund --pr "$1" --max-examples 1000 2>/dev/null \
  | sed -n '/^== /,/^inputs=/p' \
  | sed -e 's/^pr=/your code=/' -e 's/twin_a=/Rebuild 1 (Meta)=/' -e 's/twin_b=/Rebuild 2 (Gemini)=/' \
        -e 's/PR outvoted/your code is outvoted/' -e 's/twin_a/Rebuild 1/g' -e 's/twin_b/Rebuild 2/g' -e 's/^input: /input:  /'
echo "time: $(( $(date +%s) - start ))s"
