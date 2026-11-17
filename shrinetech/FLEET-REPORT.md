# FLEET-REPORT: dsh patch layer + sandboxed run (newest on top)

## 2026-11-17 — dsh-sandbox-1117 (Claude fleet worker)

**Verdict: the patched dsh CLI ran 3/3 small coding tasks against our local Bonsai 2 27B with zero outbound non-localhost
connections.** strace saw 22 `connect()` calls in total: all 22 went to `127.0.0.1:8100` (the relay to Bonsai), plus 10
local `nscd` unix-socket lookups that all failed with ENOENT. There were no DNS lookups and no other address.

### Steps (stopped at no failure)
1. **Install, in a Hokora box** (`hokora-try`, extra egress `registry.npmjs.org,cdn.sheetjs.com`). The copy came from
   `git archive` of fork `ca33fd6843` into `/mnt/storage/scratch/dsh-1117`. **[ran]** `pnpm install --frozen-lockfile`:
   "Done in 1m 58.4s", 1,434 packages.
   - Gate log: 52× `registry.npmjs.org`, 1× `cdn.sheetjs.com`, 0 DENY. The first try was DENIED `cdn.sheetjs.com` (a
     lockfile-pinned xlsx tarball, not a phone-home). Default-allowed `github.com` etc. were **never contacted**, and no
     electron binary was downloaded.
   - No offline mirror was used: the npm registry was open during install only.
2. **node_modules audit** **[ran]** (package list + `pnpm why` + host scan):
   - `@earendil-works/pi-telemetry@1.3.0` (the study's open item M) is **harmless**: types, a no-op context and an
     in-memory context only. It has no exporter and no network code (`dist/*.js` has no fetch/http/net). Its README says
     "no exporter … or dependency on a telemetry backend".
   - `@opentelemetry/otlp-exporter-base` is used only by `dsh-otel` and `dsh-host-product-telemetry-otel`. Both rows are
     off in the patch layer (path A), and product telemetry is desktop-only.
   - `chrome-devtools-mcp@1.9.0` sends Google Clearcut usage statistics by default. dsh's wrapper passes
     `--no-usage-statistics` (`packages/experimental/browser-use-chrome-devtools-mcp/src/index.ts:29`), the package is
     experimental and not in any bundle, and the box also sets `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1`. Its CrUX
     lookup (`--no-performance-crux`) is not switched off by dsh, so this is a residual for the box to block.
   - Desktop-only, never loaded by the CLI: `electron`, `electron-updater`, `electron-builder` → `simple-update-notifier`.
   - Docs website only: `@algolia/client-analytics` and `search-insights` (via `@docsearch/react`).
   - Static host scan: Segment and Sentry strings appear only inside `chrome-devtools-frontend`/`-mcp` data and
     `simple-icons`. No analytics SDK is loaded by the CLI.
3. **Patch layer** on branch `shrinetech/patch-layer-20261117` (pushed to **ShrineTech/deepseek-harness only**). Files:
   `cordis.patch.yml`, `dsh-box`, `relay.mjs`, `guard.mjs`, `README.md`.
   - **[ran]** `guard.mjs config` on the patched dump prints `PASS config`. On the stock dump (`--dump-default-config`) it
     prints `FAIL (12)`, so the guard works.
   - **[ran]** The strace guard fails on a synthetic external connect and on a DNS lookup.
4. **Build, offline** (Docker `--network none`, 4 CPUs):
   - Host libs, about 13 min.
   - The `system.node` flock addon.
   - `landlock-run`, statically linked against **glibc**, because upstream uses musl-gcc and the image has none.
5. **Run** in `dsh-box`: Docker `--network none`, `--cap-drop ALL`, read-only root, ≤ 4 CPUs, only the Bonsai port
   relayed over a unix socket. It ran under the card-0 `gpu-job-lock` (`dsh-sandbox-1117`).

   | task | result | steps | time |
   |---|---|---|---|
   | slugify (Python + unittest) | **[ran]** `python3 -m unittest test_slug` → OK | 5 | 55 s |
   | moving-average off-by-one (JS) | **[ran]** `node --test` → pass 2, fail 0 | 6 | 19 s |
   | `todo.py done <n>` + stderr error | **[ran]** `add milk; done 1; list` → `1. [x] milk`; `done 9` → error, rc=1 | 4 | 27 s |

   - Model: **Bonsai 2 27B** (:8100), not CRACK. Card 1 was held by `sando-spill-ab` (an A/B on CRACK), and I did not
     take it.
   - dsh's own Landlock confinement of its bash tool: the earlier attempt with no `landlock-run` built failed closed
     ("no sandbox backend is usable … refusing to run the command unconfined"), and the model's escalation to
     danger-full-access was rejected. After `landlock-run` was built, bash ran, and the image has no bwrap, so dsh must
     have used Landlock. That is an inference **[not checked]** in dsh's session log. The launcher itself **[ran]**:
     `landlock: fully enforced` inside Docker; it can write inside the repo and is blocked outside it.

### Host findings (worth knowing for every sandbox on the forge)
- `systemd-run --user -p IPAddressDeny=any` does **not** block egress: a test reached 1.1.1.1. The study's option 4 is out.
- bwrap cannot bring up loopback in a new network namespace here (`kernel.apparmor_restrict_unprivileged_userns=1`).
- Docker `--tmpfs` is noexec by default, and dsh copies native `.node` files into `/tmp` before loading them.

### Not done / limits
- No run against CRACK (card 1 busy). Three base rows didn't activate because they weren't built: typert,
  typert-loader, api-gateway. That is a warning only.
- The desktop app was never run. Nothing was installed on the host outside a box.
- The lockfile pins `pnpm@11.28.5` and Node ≥ 24.9. The Hokora box only has Node 22, so the install ran with
  `engine-strict=false`. The build and the run used our host Node 24.22 inside the offline container.

Evidence: `shrinetech/evidence-20261117/` (gate logs, 3 strace logs, task JSONL, patched dump, package list, task diff).
Scratch: `/mnt/storage/scratch/dsh-1117` (2.3 GB built tree, keep or delete).

### Needs Chuck (also posted as a form)
- Merge `shrinetech/patch-layer-20261117` into our fork's `master`? (yes/no)
- Repeat the 3 tasks on CRACK when card 1 is free? (yes/no)
- Add musl to the box image so `landlock-run` is built exactly as upstream builds it? (yes/no)
- Next use of dsh-box: Sando-vs-dsh head-to-head / keep as a reference only / nothing. (pick one)
- Delete the 2.3 GB scratch tree at `/mnt/storage/scratch/dsh-1117`? (yes/no)
