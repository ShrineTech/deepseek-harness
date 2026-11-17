#!/bin/bash
# check.sh <repo>: the three task checks, run on the host after the harness exits. Prints PASS/FAIL per task.
cd "$1" || exit 2
python3 -m unittest -q test_slug >/dev/null 2>&1 && echo "task1 PASS" || echo "task1 FAIL"
node --test stats.test.mjs >/dev/null 2>&1 && echo "task2 PASS" || echo "task2 FAIL"
d=$(mktemp -d); cp todo.py "$d"; ( cd "$d" && python3 todo.py add milk && python3 todo.py done 1 && out=$(python3 todo.py list) \
  && [ "$out" = "1. [x] milk" ] && ! python3 todo.py done 9 2>err && [ -s err ] ) >/dev/null 2>&1 && echo "task3 PASS" || echo "task3 FAIL"
rm -rf "$d"
