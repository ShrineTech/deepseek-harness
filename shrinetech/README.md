# ShrineTech patch layer for dsh (2026-11-17)

How ShrineTech runs the dsh **CLI** (never the Electron desktop app): call-home rows switched off, our local llama-server as
the only model, and the whole run in a Docker box that has no network. This directory is ours. Nothing else in the tree
is changed, so a rebase onto upstream stays trivial. Never open a PR with this to deepseek-ai.

| File | What it does |
|---|---|
| `cordis.patch.yml` | Home patch layer (`$DSH_HOME/cordis.patch.yml`, applies to every profile). It disables OTel, the DeepSeek session-log and plugin-inventory fields, the DeepSeek account and model routes, web search/fetch and upstream skills, then adds the `forge-llama` OpenAI-compatible route and makes it the default. |
| `dsh-box` | Launcher. It runs `apps/cli/lib/bin.js` in Docker `--network none` (loopback only), with no capabilities, a read-only root and ≤ 4 CPUs. It sets the telemetry env switches and relays exactly one host port (the llama-server) in through a unix socket. Every `connect`/`send*` call is strace-logged. |
| `relay.mjs` | The one-port TCP ↔ unix-socket relay used by `dsh-box`. |
| `box-image/Dockerfile` | The box image `shrinetech-dsh-box:0.2`: `shrineai-egress-lab:0.2` (Ubuntu 24.04 + build-essential + strace) plus `musl-tools` (so upstream's `build.ts` builds `landlock-run` with `musl-gcc` unchanged), `ripgrep` and `git` (0.2, 2026-11-17: the 0.1 box had neither, which skewed the head-to-head against Sando's `rg` prompt line). |
| `sandbox-level.mjs` | Asks dsh's own `LocalSandboxProvider` which backend and enforcement level it picks (`{"runner":"landlock","enforcement":"full"}` in the box). |
| `h2h/` | The Sando-vs-dsh head-to-head: runner, harness-neutral wire metrics, fair setup and results. |
| `guard.mjs` | `config <dump>` checks that every call-home row is off and the route is local. `strace <log>` checks that no connect or send went anywhere except loopback or unix sockets, and flags any DNS lookup. |

## Use
```sh
# 1. install in a Hokora box (egress: registry.npmjs.org + cdn.sheetjs.com only), copy the tree out
# 2. build the box image once (egress-lab + musl-tools + ripgrep + git):  docker build -t shrinetech-dsh-box:0.2 shrinetech/box-image
#    then build offline in it (docker run --network none ... shrinetech-dsh-box:0.2, ~2 min on 4 CPUs):
#      node --import tsx/esm scripts/compile-referenced-projects.ts host-libraries
#      node --max-old-space-size=8192 node_modules/typescript/bin/tsc -p tsconfig.host.json
#      node --import tsx/esm native/system/scripts/build.ts      # upstream's own script: landlock-run with musl-gcc
#                                                                 # (static, ~38 KB) + glibc and musl system.node
#      (Without landlock-run dsh's bash tool fails closed: "no sandbox backend is usable")
# 3. check the sandbox level dsh will use:
cp shrinetech/sandbox-level.mjs <built-tree>/packages/sandbox/sandbox-local/
DSH_BOX_ENTRY=packages/sandbox/sandbox-local/sandbox-level.mjs shrinetech/dsh-box <built-tree> <scratch>
# 4. run:
FORGE_LLAMA_PORT=8100 FORGE_LLAMA_MODEL=bonsai2-27b FORGE_LLAMA_CTX=65536 \
  shrinetech/dsh-box <built-tree> <scratch> headless --approval-policy never "task"
shrinetech/dsh-box <built-tree> <scratch> --profile headless --dump-config > dump.yml && node shrinetech/guard.mjs config dump.yml
node shrinetech/guard.mjs strace <scratch>/strace-connect.log
```

## Env switches (set by `dsh-box`)
`DSH_TELEMETRY_DISABLED=1`, `DSH_TELEMETRY_MODE=DISABLED`, `DSH_TELEMETRY_OTLP_URL` and `DSH_PRODUCT_ANALYTICS_OTLP_URL`
pointed at `127.0.0.1:9`, `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1`, `NO_UPDATE_NOTIFIER=1`, `DO_NOT_TRACK=1`. `DEEPSEEK_API_KEY`
and `DEEPSEEK_BASE_URL` are never passed.

## Host notes (Phoenix Forge)
- bwrap cannot bring up loopback in an unprivileged network namespace here (`kernel.apparmor_restrict_unprivileged_userns=1`).
- systemd **user** units do not enforce `IPAddressDeny`: a test unit still reached 1.1.1.1.
- That is why the box is Docker `--network none`.
- Docker `--tmpfs` is noexec by default, and dsh's native-addon loader copies `.node` files into `/tmp` before loading them,
  so the box mounts `/tmp` with `exec`.
- Updates and crash reports: the CLI has no auto-updater. The 10-minute updater is desktop-only (`apps/desktop/src/update-schedule.ts`).
  Crash reports are local files only. The box blocks any network attempt either way.
