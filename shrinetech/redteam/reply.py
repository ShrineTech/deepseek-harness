# reply.py <out file>: the harness's final reply text only (dsh --json: the "final" event; Sando --json: "response"),
# so tool results the model merely READ (the attack text itself) are not mistaken for what it said.
import json, sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
try:
    print(json.loads(raw).get("response", ""))
except ValueError:
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "final":
            print(d.get("text", ""))
