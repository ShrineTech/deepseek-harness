// One-port TCP <-> unix-socket relay for the dsh box (no dependencies).
//   node relay.mjs out <unix.sock> <port>   host side: socket -> 127.0.0.1:<port>
//   node relay.mjs in  <unix.sock> <port>   box side:  127.0.0.1:<port> -> socket
// The box has its own network namespace with only loopback, so this socket is
// the one way out, and it reaches exactly one host port (the llama-server).
import { createConnection, createServer } from 'node:net'
import { rmSync } from 'node:fs'

const [mode, sock, port] = process.argv.slice(2)
if (!['in', 'out'].includes(mode) || !sock || !/^\d+$/u.test(port ?? '')) {
  console.error('usage: relay.mjs in|out <unix.sock> <port>')
  process.exit(2)
}
const pipe = (client, target) => {
  const upstream = createConnection(target)
  client.pipe(upstream).pipe(client)
  const close = () => { client.destroy(); upstream.destroy() }
  client.on('error', close)
  upstream.on('error', close)
}
if (mode === 'out') {
  rmSync(sock, { force: true })
  createServer(c => pipe(c, { host: '127.0.0.1', port: Number(port) })).listen(sock)
} else {
  createServer(c => pipe(c, { path: sock })).listen(Number(port), '127.0.0.1')
}
