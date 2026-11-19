#!/bin/bash
S="$1"; shift
PY=/c/Users/abdou/ols-prime/python/.venv/Scripts/python.exe
export PYTHONDONTWRITEBYTECODE=1
for name in "$@"; do
  cd "$S/mut/$name/python" || exit 1
  PYTHONPATH="$S/mut/$name/python" $PY -m pytest tests/test_detectors.py tests/test_detector_classes.py tests/test_detector_stats.py -q -p no:cacheprovider --basetemp="$S/tmp-$name" -k "not worker_count" > "$S/mut/$name.log" 2>&1
  echo "== $name: $(tail -1 "$S/mut/$name.log")"
  grep "^FAILED\|^ERROR" "$S/mut/$name.log" | cut -c1-170
done
