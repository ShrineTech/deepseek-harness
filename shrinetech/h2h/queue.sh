#!/bin/bash
# queue.sh <label-prefix> <reps> [task...]: interleaved dsh/Sando runs (rep 1 dsh first, rep 2 Sando first). MODEL as in run.sh.
# STOP_AT (UTC epoch s): don't start a new pair after this time.
here=$(cd "$(dirname "$0")" && pwd); P=$1; R=$2; shift 2
TASKS=${@:-t1_median t2_slugify t3_duration t4_refactor t5_inventory t6_ttlcache t7_todo_cli t8_config t9_buildlog}
for rep in $(seq 1 "$R"); do
  order="dsh sando"; [ $((rep % 2)) = 0 ] && order="sando dsh"
  for t in $TASKS; do
    if [ -n "${STOP_AT:-}" ] && [ "$(date +%s)" -ge "$STOP_AT" ]; then echo "STOP_AT reached before $P-r$rep $t"; exit 0; fi
    for h in $order; do "$here/run.sh" "$h" "$P-r$rep" "$t"; done
  done
done
