#!/bin/bash
# run-crack.sh <scratch>: the 3 sandbox-run tasks of 2026-11-17 again, on CRACK (:8097, card 1), in dsh-box, one shared repo
# (as in the first run), each task its own headless dsh session. Run it under: gpu-job-lock run dsh-crack --gpu 1 ...
# The repo files are rebuilt from the first run's evidence (dsh's read results); the prompts are rewritten from its report.
set -u
here=$(cd "$(dirname "$0")" && pwd); S=$1; TREE=${DSH_TREE:-/mnt/storage/scratch/dsh-fu-1117/dsh}
rm -rf "$S"; mkdir -p "$S"; cp -r "$here/repo" "$S/repo"
while IFS=$'\t' read -r name prompt; do
  START=$(date +%s)
  FORGE_LLAMA_PORT=8097 FORGE_LLAMA_MODEL=qwen3.8-27b FORGE_LLAMA_CTX=131072 FORGE_LLAMA_MAX_TOKENS=8192 \
    DSH_BOX_STRACE=$S/strace-$name.log timeout 1200 "$here/../dsh-box" "$TREE" "$S" \
    --profile headless --json --approval-policy never "$prompt" > "$S/$name.jsonl" 2> "$S/$name.err" < /dev/null
  rc=$?; steps=$(grep -c '"phase":"step_end"' "$S/$name.jsonl")
  g=$(node "$here/../guard.mjs" strace "$S/strace-$name.log" >/dev/null 2>&1 && echo "zero outbound" || echo "OUTBOUND FAIL")
  echo "$name rc=$rc steps=$steps secs=$(( $(date +%s) - START )) strace=$g connects=$(grep -c 'connect(' "$S/strace-$name.log")"
done < "$here/PROMPTS"
"$here/check.sh" "$S/repo"
