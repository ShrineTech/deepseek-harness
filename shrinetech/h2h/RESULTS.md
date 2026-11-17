# Sando vs dsh head-to-head: results (2026-11-17, 21:16–22:52 UTC)

Setup: `FAIR-SETUP.md` (committed at 6d449ca260, before any scored run). It used the same box, the same model server,
the same 9 lean-bench tasks with hidden checks, the same 1,200 s limit and an 8,192-token output cap, with every number
read from the wire. Raw lines: `../evidence-20261117-followup/h2h-results.txt` (metrics recomputed from each run's proxy
log with the final `metrics.py`) and `h2h-results-raw.txt` (as printed during the runs).
- dsh: fork master (rc.4 + patch layer), Landlock `full` inside the box.
- Sando: the deployed release (zcode 0.16.9), `lean-local`.

## Totals (68 runs, 0 outbound: every AF_INET connect was 127.0.0.1:8100 or :8097)
| model | harness | pass | total s | median s | requests | prompt tok | completion tok | tool calls | tool-call errors | re-reads |
|---|---|---|---|---|---|---|---|---|---|---|
| Bonsai 2 27B (rep 1 all 9 tasks, rep 2 t1–t7) | dsh | **16/16** | **1,960** | 78 | 330 | **4.18 M** | **80 k** | 325 | **0** | 3 |
| | Sando | 15/16 | 3,473 | 67 | 396 | 5.07 M | 131 k | 407 | 4 | 11 |
| CRACK 27B (2 reps, all 9 tasks) | dsh | 16/18 | **1,951** | 49 | 290 | 4.58 M | 83 k | 301 | 4 | 5 |
| | Sando | 16/18 | 2,193 | 47 | 332 | **3.50 M** | 90 k | 368 | 4 | 4 |
| **all** | dsh | **32/34** | **3,911** | | 620 | 8.76 M | 163 k | 626 | 4 | 8 |
| | Sando | 31/34 | 5,666 | | 728 | 8.57 M | 221 k | 775 | 8 | 15 |

Failures:
- **t5_inventory** (the sort tie-break that only the docstring states): Sando failed 3 of 4 runs and dsh failed 1 of 4.
  Both made the model read the same files, so the difference is in what the model chose to fix, not in what it saw. A
  plausible push for Sando is the lean prompt's "smallest correct edit" line, but that is a guess.
- **t8_config, CRACK rep 1, dsh:** it missed one re-opened-section collision case.
- **t8_config, CRACK rep 2, dsh:** it ended with rc=1 because one model step hit the 8,192-token cap and dsh stops the
  whole run on `max-tokens`. Its edits were already done and pass the hidden check.

## What the numbers say
- **Success is a tie** (32/34 vs 31/34). That is one task apart at n = 34, so it is noise.
- **dsh was faster overall: 31% less wall time** (3,911 s vs 5,666 s). The gap is almost all Sando's long tails on Bonsai:
  - t6 rep 2: 692 s against dsh's 162 s;
  - t8 rep 1: 1,098 s against 562 s.

  On CRACK the two were close (−11%). Median runs are equal, so the gap is in how a run that goes wrong recovers.
- **Tokens:**
  - Sando's fixed prompt is about 3× smaller: the first agent request is a median 1,917 prompt tokens against dsh's
    5,660 (5 tools, 4.2 k chars of schemas, against 21 tools, 20.1 k chars). dsh also makes a title call each run.
  - On short tasks Sando sends far fewer prompt tokens (t1/t2/t4: 2–4× fewer).
  - On long tasks Sando takes more steps, and the total evens out. CRACK: Sando −24%. Bonsai: dsh −18%.
  - Sando spends 36% more completion tokens overall (221 k vs 163 k).
- **Errors and re-reads:** about even on tool-call errors (4 dsh vs 8 Sando). Sando re-reads more (15 vs 8).
  - **Sando refused 33 reads** with "Wasted call — file unchanged since your last Read".
  - The model then fell back to `cat`/`sed`/`head` in bash 10 times, against Sando's own prompt.
  - In Bonsai t6 rep 2 the model asked for README.md 5 times in a row and was refused each time.
  - dsh never refuses a read. Its guard only nudges after 3/5/8 identical calls.

## What dsh does better → SAN-4472 port list (ranked by what the runs show)
1. **Recover from a lost read instead of refusing it.** Sando's "Wasted call" refusal is the main driver of its long tails
   here: 33 refusals, 10 bash workarounds, the README loop. A small local model often no longer holds the earlier
   content (or never attended to it). Port dsh's behaviour: allow the re-read, or return the cached content, plus a nudge
   on the 3rd/5th/8th identical call (`packages/guard` repeat-tool-reminder). At minimum, return the content again after
   the first refusal.
2. **Bring the search tools with the harness.** The lean prompt says "search with `rg`", but `rg` is not on every box. It
   was missing in this image, so every t4 run hit `rg: command not found` once. dsh ships `glob`/`grep` tools and tells the
   model to use them. Give lean a Grep/Glob tool, or check for `rg` and fall back to `grep -rn` in the prompt line.
3. **Stop a run cleanly on an over-long step.** dsh ends the run with `reason: max-tokens` when a step hits the output cap
   (t8 CRACK r2). That is not better than Sando. It is listed so the port does **not** copy it: Sando should continue with
   a "you hit the output cap, continue" turn.
4. **Prompt line to test:** drop or soften "smallest correct edit" in lean-local, and A/B it on t5. One hypothesis, n = 4
   per side so far.

What Sando already does better (keep): a smaller fixed prompt, no side call per run, and fewer prompt tokens on short
tasks.

## Limits
- n is small: 2 reps on CRACK, 1.8 on Bonsai (rep 2 stopped at t7 at the 22:45 UTC card-0 cut-off). One task apart is noise.
- Both harnesses ran in Docker `--network none`, so neither could reach anything. Whether either *tries* to phone home
  outside a box is covered by the dsh patch layer's guard and Sando's own phonehome test, not by this run.
- The box image has no `git` and no `rg`. That hurt Sando's prompt (item 2) more than dsh's.
- `SANDO_SHELL_GATE=off` for all runs (it is a shadow classifier that calls CRACK directly).
- Wall time includes the CRACK server being shared: `gmail-triage-new` also uses CRACK (1 slot). Both harnesses saw the
  same server and were interleaved.
