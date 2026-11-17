#!/bin/bash
# after-crack.sh: once the CRACK h2h unit (dsh-crack-2) is done, the injection cases on CRACK under card 1's lock.
# Never starts after DEADLINE (UTC epoch s): the Lily test parks CRACK at 10:15 PM ET.
here=$(cd "$(dirname "$0")" && pwd)
while systemctl --user is-active -q dsh-crack-2; do sleep 30; done
[ "$(date +%s)" -ge "$DEADLINE" ] && { echo "past DEADLINE, injection cases not run"; exit 3; }
exec ~/bin/gpu-job-lock run dsh-crack-inject --gpu 1 --purpose "dsh follow-up: prompt-injection cases, dsh + Sando on CRACK" --ttl-min 20 -- \
  bash -c "for h in dsh sando; do MODEL=crack '$here/run.sh' \$h /mnt/storage/scratch/dsh-fu-1117/redteam-crack; done"
