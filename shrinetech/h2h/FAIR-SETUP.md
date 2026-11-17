# Sando vs dsh head-to-head: fair setup (written 2026-11-17 21:20 UTC, BEFORE the scored runs)

Goal: compare the two harnesses, not the models. Everything except the harness is held equal. Results go in
`RESULTS.md`; anything dsh does better feeds Sando's port list (SAN-4472).

## Held equal
| | both harnesses |
|---|---|
| **Model** | Bonsai 2 27B (`llama-server-bonsai2`, :8100, card 0, n_ctx 65,536, 1 slot), then CRACK (`forge-crack-27b`, :8097, card 1, n_ctx 131,072) if time allows. Same server, same sampler defaults (the server's: temp 1.0, top_p 0.95, top_k 20). Neither harness sends thinking/reasoning settings. |
| **Context window told to the harness** | the server's real n_ctx (65,536 on Bonsai, 131,072 on CRACK) |
| **Output cap per request** | 8,192 tokens (Sando's provider config; dsh via `FORGE_LLAMA_MAX_TOKENS=8192`) |
| **Sandbox** | the same `dsh-box`: Docker `--network none` (loopback only), `--cap-drop ALL`, `no-new-privileges`, read-only root, `/tmp` tmpfs, ≤ 4 CPUs, 8 GB RAM, our uid. Image `shrinetech-dsh-box:0.1` (Ubuntu 24.04, python3 3.12, no git). The only way out is one unix-socket relay to the model port. Every connect/send is strace-logged and checked by `guard.mjs strace`. |
| **Wire logging** | the relay dials a host logging proxy (`h2h/logproxy.mjs`, :18120 Bonsai / :18121 CRACK) in front of the server. Every number below is read from the wire by `h2h/metrics.py`, the same way for both. |
| **Tasks** | Sando's lean bench, all 9 (`~/apps/fleet/work/sando-lean/tasks`, t1–t9), same `PROMPT` text, a fresh copy per run, `__pycache__` removed. Scored by the bench's **hidden** checks (stricter than the visible tests), run on the host after the harness exits. |
| **Autonomy** | no approvals and no questions: dsh `--profile headless --approval-policy never`; Sando `-p … --mode yolo`. Each run is a single prompt with no follow-up. |
| **Time limit** | 1,200 s wall per run (`timeout`), the same limit the lean bench used |
| **Order** | interleaved per task (rep 1: dsh then Sando; rep 2: Sando then dsh) to spread server drift; one run at a time |
| **GPU** | under `gpu-job-lock` for that card. Nothing else is switched or loaded. |

## Each harness as it ships for local models (not tuned for this test)
- **dsh**: fork master (rc.4 + ShrineTech patch layer: call-home rows off, `forge-llama` route, compaction headroom 16k).
  Its bash tool runs under its own Landlock sandbox (`workspace-write`, enforcement `full`) **inside** the box. That is
  stricter than Sando, and it counts against dsh if it gets in the way.
- **Sando**: the deployed release (`~/apps/sando-release`, zcode 0.16.9), `SANDO_PROMPT_PROFILE=lean-local` (its local-model
  profile). `SANDO_SHELL_GATE=off`: the shell gate is a shadow classifier that calls CRACK directly on :8097. On Bonsai runs it
  would only hit a closed port, and on CRACK runs it would add model calls the proxy doesn't count as the agent's, so it is
  off for every run. Sando's HOME is fresh per run, with exactly one provider (the model behind the relay) and no keys.

## Metrics (per run)
- **success**: the hidden check prints `PASS`
- **wall s**: harness start to exit, box start-up included (same box for both)
- **requests, prompt tokens, completion tokens**: the server's `usage`, summed over the run's chat/completions requests
- **tool calls**: tool calls the model emitted (streamed `tool_calls`)
- **tool-call errors**: unparseable arguments, plus tool results that report a harness/tool failure (unknown tool, bad
  arguments, missing file, edit mismatch, denied, timed out). A failing test run is NOT an error.
- **log re-reads**: reading a file again (read tool, or `cat/head/tail/sed -n/nl` in bash) with no write to it in between,
  plus reads of a harness spill/overflow file
- **outbound**: any non-loopback connect or DNS lookup in strace = the run is void

## What would make this unfair (checked)
- One harness gets more context or a bigger output cap → both are set to the server's n_ctx and 8,192.
- One harness's extra side calls are counted → the shadow gate is off; title/summary side calls, if any, are counted
  because they are part of what the harness costs.
- Model warm-up or caching favours the second run → order alternates per rep. llama.cpp prompt caching helps whoever
  re-sends the same prefix, and that is a real harness property, so it stays.
- n is small (9 tasks × 1–2 reps): differences of one task are noise. The report says so.
