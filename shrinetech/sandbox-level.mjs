// Print the sandbox backend and enforcement level dsh's own LocalSandboxProvider selects on this host
// (the same selection + probe its bash tool uses), without booting the whole app. Copy it next to the built
// package and run it inside the box:
//   cp shrinetech/sandbox-level.mjs <tree>/packages/sandbox/sandbox-local/
//   DSH_BOX_ENTRY=packages/sandbox/sandbox-local/sandbox-level.mjs shrinetech/dsh-box <tree> <scratch>
// Prints e.g. {"runner":"landlock","enforcement":"full","argv0":".../landlock-run"}; exit 1 if no backend is usable.
import { LocalSandboxProvider } from './lib/index.js'

const p = Object.create(LocalSandboxProvider.prototype)
Object.assign(p, { internals: {}, runnerCommand: undefined, probeTimeoutMs: 5000, workspaceGrants: new Map(), tempCapabilities: new Map() })
const ws = process.cwd()
try {
  const sel = p.selectRunner('workspace-write')
  const c = await p.confine(['/bin/true'], { mode: 'workspace-write', workspaceRoot: ws, writableRoots: [], readableRoots: [] })
  console.log(JSON.stringify({ runner: sel.runner, enforcement: c.enforcement, argv0: c.argv[0] }))
} catch (e) {
  console.log(JSON.stringify({ error: String(e?.code ?? ''), message: String(e?.message ?? e) }))
  process.exit(1)
}
