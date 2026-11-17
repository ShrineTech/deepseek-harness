#!/bin/bash
# card1-queue.sh: wait for card 1's gpu-job-lock (poll, never force), then on CRACK: the 3-task dsh repeat, then the
# head-to-head (1 rep). Never inside the Lily-test park (10:15 PM-1:30 AM ET) or the V4.1-Flash block (2:30-6:30 AM ET):
# START_BY / STOP_AT are UTC epoch seconds (no start after START_BY; no new h2h pair after STOP_AT).
here=$(cd "$(dirname "$0")" && pwd)
while :; do
  now=$(date +%s)
  [ "$now" -ge "$START_BY" ] && { echo "$(date -u +%TZ) card 1 not free before START_BY; giving up"; exit 3; }
  [ -e ~/.config/forge/gpu_fallen.1 ] && { echo "card 1 fallen; giving up"; exit 4; }
  if [ ! -e ~/.config/forge/one_card_only ] && ~/bin/gpu-job-lock status --gpu 1 | grep -q '^free'; then break; fi
  sleep 60
done
echo "$(date -u +%TZ) card 1 free; CRACK=$(systemctl --user is-active llama-server-crack.service)"
exec ~/bin/gpu-job-lock run dsh-crack --gpu 1 --purpose "dsh follow-up on CRACK: 3-task repeat + Sando vs dsh h2h (SAN-4472)" \
  --ttl-min "${TTL_MIN:-240}" -- bash -c "
    '$here/../crack-repeat/run-crack.sh' /mnt/storage/scratch/dsh-fu-1117/crack-repeat
    MODEL=crack STOP_AT=$STOP_AT '$here/queue.sh' crack 1"
