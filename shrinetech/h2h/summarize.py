# summarize.py <results.txt> [label-prefix]: per-task and per-harness tables (markdown) from run.sh result lines.
import re, statistics, sys
from collections import defaultdict

rows = []
for line in open(sys.argv[1]):
    m = re.match(r"(\S+) (\S+) (dsh|sando) (\S+) rc=(\S+) secs=(\d+) score=\[(.*?)\] outbound=(\S+) (.*)", line.strip())
    if not m:
        continue
    label, model, h, task, rc, secs, score, outb, rest = m.groups()
    if len(sys.argv) > 2 and not label.startswith(sys.argv[2]):
        continue
    kv = dict(x.split("=") for x in rest.split())
    rows.append(dict(label=label, model=model, h=h, task=task, rc=rc, secs=int(secs), ok=score == "PASS", score=score,
                     outb=outb, **{k: int(v) for k, v in kv.items()}))

by_task = defaultdict(lambda: defaultdict(list))
for r in rows:
    by_task[r["task"]][r["h"]].append(r)


def cell(rs):
    if not rs:
        return "—"
    ok = sum(r["ok"] for r in rs)
    return (f"{ok}/{len(rs)} · {round(statistics.mean(r['secs'] for r in rs))} s · "
            f"{round(statistics.mean(r['pt'] for r in rs) / 1000)}k pt · {round(statistics.mean(r['req'] for r in rs))} req · "
            f"err {sum(r['err'] + r['bad'] for r in rs)} · reread {sum(r['reread'] + r['spill'] for r in rs)}")


print("| task | dsh | Sando |")
print("|---|---|---|")
for t in sorted(by_task):
    print(f"| {t} | {cell(by_task[t]['dsh'])} | {cell(by_task[t]['sando'])} |")
print()
print("| harness | pass | total s | median s | requests | prompt tok | completion tok | tool calls | tool-call errors | re-reads | outbound |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for h in ("dsh", "sando"):
    rs = [r for r in rows if r["h"] == h]
    if not rs:
        continue
    print(f"| {h} | {sum(r['ok'] for r in rs)}/{len(rs)} | {sum(r['secs'] for r in rs)} | {statistics.median(r['secs'] for r in rs):.0f} | "
          f"{sum(r['req'] for r in rs)} | {sum(r['pt'] for r in rs) / 1e6:.2f} M | {sum(r['ct'] for r in rs) / 1e3:.1f} k | "
          f"{sum(r['calls'] for r in rs)} | {sum(r['err'] + r['bad'] for r in rs)} | {sum(r['reread'] + r['spill'] for r in rs)} | "
          f"{sum(r['outb'] != '0' for r in rs)} |")
fails = [r for r in rows if not r["ok"]]
if fails:
    print()
    for r in fails:
        print(f"- {r['label']} {r['h']} {r['task']}: rc={r['rc']} {r['secs']} s, check: `{r['score'][:120]}`")
