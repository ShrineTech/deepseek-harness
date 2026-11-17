// Guard for the ShrineTech patch layer (no dependencies).
//   node guard.mjs config <dump-config.yml>   every call-home row is disabled, the model route is local
//   node guard.mjs strace <strace.log>        no connect/send to anything but loopback or unix sockets
// Exit 0 = pass, 1 = fail (the reasons are printed).
import { readFileSync } from 'node:fs'

const MUST_BE_OFF = [
  'otel', 'session-telemetry-otel', 'session-log-deepseek', 'plugin-package-inventory-deepseek',
  'llm-deepseek', 'llm-deepseek-account', 'deepseek-account', 'web-search-deepseek',
  'web-deepseek-api', 'web-fetch-http', 'tool-web', 'upstream-skills',
]
// Rows that must never be mounted in a CLI profile at all.
const MUST_BE_ABSENT = ['desktop-product-telemetry', 'product-analytics']

const [mode, file] = process.argv.slice(2)
const text = readFileSync(file, 'utf8')
const fails = []

if (mode === 'config') {
  // The dump lists each layer's rows in order; the last `- id: X` block decides.
  const last = new Map()
  const blocks = text.split(/^(?=\s*- id: )/mu)
  for (const block of blocks) {
    const id = /^\s*- id: ([\w-]+)/u.exec(block)?.[1]
    if (!id) continue
    const prev = last.get(id) ?? { disabled: false }
    if (/^\s*disabled: true\s*$/mu.test(block)) prev.disabled = true
    else if (/^\s*disabled: false\s*$/mu.test(block)) prev.disabled = false
    last.set(id, { ...prev, block })
  }
  for (const id of MUST_BE_OFF) {
    if (!last.has(id)) continue // not mounted by this profile at all
    if (!last.get(id).disabled) fails.push(`row ${id} is not disabled`)
  }
  for (const id of MUST_BE_ABSENT) {
    if (last.has(id) && !last.get(id).disabled) fails.push(`row ${id} is mounted`)
  }
  if (!/provider: forge-llama/u.test(last.get('agent-default-model')?.block ?? '')) {
    fails.push('agent-default-model does not point at forge-llama')
  }
  if (/api\.deepseek\.com|deepseeksvc\.com/u.test(last.get('llm-pi-ai')?.block ?? '')) {
    fails.push('llm-pi-ai names a DeepSeek host')
  }
} else if (mode === 'strace') {
  for (const line of text.split('\n')) {
    if (!/\b(connect|sendto|sendmsg|sendmmsg)\(/u.test(line)) continue
    if (/AF_UNIX|AF_NETLINK/u.test(line)) continue
    const ip4 = /inet_addr\("([\d.]+)"\)/u.exec(line)?.[1]
    const ip6 = /inet_pton\(AF_INET6, "([^"]+)"/u.exec(line)?.[1]
    // A DNS query to a loopback resolver still means something tried to reach a host by name.
    if (/htons\(53\)/u.test(line)) { fails.push(`dns lookup: ${line.trim()}`); continue }
    if (ip4?.startsWith('127.') || ip6 === '::1') continue
    if (!ip4 && !ip6 && !/AF_INET/u.test(line)) continue // send on an already-connected fd
    fails.push(`outbound: ${line.trim()}`)
  }
} else {
  console.error('usage: guard.mjs config|strace <file>')
  process.exit(2)
}

if (fails.length) {
  console.log(`FAIL (${fails.length})\n${fails.join('\n')}`)
  process.exit(1)
}
console.log(`PASS ${mode}`)
