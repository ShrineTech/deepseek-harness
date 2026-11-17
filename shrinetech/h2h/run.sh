#!/bin/bash
# run.sh <harness: dsh|sando> <label> <task>... : each task once, in the same dsh-box (Docker --network none,
# 4 CPUs, read-only root, strace), on one local model through a host logging proxy. Fair setup: FAIR-SETUP.md.
# Env: MODEL=bonsai|crack (bonsai), RUN_TIMEOUT (1200 s), H2H_OUT (/mnt/storage/scratch/dsh-fu-1117/h2h),
#      DSH_TREE (built dsh tree), SANDO_TREE (~/apps/sando-release), TASKS (~/apps/fleet/work/sando-lean/tasks)
set -u
here=$(cd "$(dirname "$0")" && pwd); box=$here/../dsh-box
H=$1; LABEL=$2; shift 2
OUT=${H2H_OUT:-/mnt/storage/scratch/dsh-fu-1117/h2h}; T=${TASKS:-$HOME/apps/fleet/work/sando-lean/tasks}
DSH_TREE=${DSH_TREE:-/mnt/storage/scratch/dsh-fu-1117/dsh}; SANDO_TREE=${SANDO_TREE:-$HOME/apps/sando-release}
case ${MODEL:-bonsai} in
  bonsai) PORT=8100; PROXY=18120; MID=bonsai2-27b; PID=forge-bonsai2; CTX=65536 ;;
  crack)  PORT=8097; PROXY=18121; MID=qwen3.8-27b; PID=forge-crack;   CTX=131072 ;;
  *) echo "MODEL must be bonsai or crack" >&2; exit 2 ;;
esac
LOG=$OUT/proxy-${MODEL:-bonsai}.jsonl; mkdir -p "$OUT"; touch "$LOG"
if ! curl -s -m 2 -o /dev/null "127.0.0.1:$PROXY/health"; then
  LOG=$LOG UPSTREAM=http://127.0.0.1:$PORT PORT=$PROXY node "$here/logproxy.mjs" > "$OUT/proxy-$PROXY.out" 2>&1 & proxy=$!
  trap 'kill $proxy 2>/dev/null' EXIT; sleep 0.5
fi
for t in "$@"; do
  RD=$OUT/$LABEL/$H/$t; rm -rf "$RD"; mkdir -p "$RD/home"
  cp -r "$T/$t" "$RD/repo"; rm -f "$RD/repo/PROMPT"; find "$RD/repo" -name __pycache__ -prune -exec rm -rf {} +
  PROMPT=$(cat "$T/$t/PROMPT")
  L0=$(wc -l < "$LOG"); START=$(date +%s.%N)
  if [ "$H" = dsh ]; then
    FORGE_LLAMA_PORT=$PORT FORGE_LLAMA_UPSTREAM_PORT=$PROXY FORGE_LLAMA_MODEL=$MID FORGE_LLAMA_CTX=$CTX FORGE_LLAMA_MAX_TOKENS=8192 \
      timeout --kill-after=20 "${RUN_TIMEOUT:-1200}" "$box" "$DSH_TREE" "$RD" \
      --profile headless --json --approval-policy never "$PROMPT" > "$RD/out.jsonl" 2> "$RD/err.log"
  else
    python3 "$here/mkhome-sando.py" "$RD/home" $PID $MID $PORT $CTX
    SANDO_PROMPT_PROFILE=lean-local SANDO_SHELL_GATE=off DSH_BOX_PASSENV="SANDO_PROMPT_PROFILE SANDO_SHELL_GATE" DSH_BOX_ENTRY=bin/zcode.mjs \
      FORGE_LLAMA_PORT=$PORT FORGE_LLAMA_UPSTREAM_PORT=$PROXY \
      timeout --kill-after=20 "${RUN_TIMEOUT:-1200}" "$box" "$SANDO_TREE" "$RD" \
      -p "$PROMPT" --cwd "$RD/repo" --mode yolo --json --model $PID/$MID > "$RD/out.json" 2> "$RD/err.log"
  fi
  RC=$?; END=$(date +%s.%N)
  SCORE=$(cd /tmp && timeout 120 python3 -I "$T/hidden/$t.py" "$RD/repo" 2>&1 | tail -1)
  L1=$(wc -l < "$LOG"); sed -n "$((L0+1)),$((L1))p" "$LOG" > "$RD/proxy.jsonl"
  OUTB=$(node "$here/../guard.mjs" strace "$RD/strace-connect.log" >/dev/null 2>&1 && echo 0 || echo FAIL)
  M=$(python3 "$here/metrics.py" "$RD/proxy.jsonl")
  printf '%s\n' "$LABEL ${MODEL:-bonsai} $H $t rc=$RC secs=$(printf '%.0f' "$(echo "$END - $START" | bc)") score=[$SCORE] outbound=$OUTB $M" \
    | tee -a "$OUT/results.txt"
done
