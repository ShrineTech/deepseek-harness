// Logging reverse proxy for OpenAI-compatible chat endpoints.
// ShrineTech copy for the dsh-vs-Sando head-to-head: keeps up to 4 MB of each response (was 20 kB) so tool calls can be counted.
// Usage: LOG=/path/requests.jsonl UPSTREAM=http://127.0.0.1:8100 PORT=18100 node logproxy.mjs
// Writes one JSON line per request: {ts, path, body, status, responseText (truncated)}.
import http from "node:http";
import https from "node:https";
import fs from "node:fs";

const upstream = new URL(process.env.UPSTREAM ?? "http://127.0.0.1:8100");
const port = Number(process.env.PORT ?? 18100);
const log = process.env.LOG ?? "/tmp/logproxy.jsonl";

http
  .createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks);
      const headers = { ...req.headers, host: upstream.host };
      // AUTH_ENV names an env var holding the real key; it replaces the placeholder Authorization header.
      if (process.env.AUTH_ENV) headers.authorization = `Bearer ${process.env[process.env.AUTH_ENV]}`;
      delete headers["content-length"];
      if (raw.length) headers["content-length"] = String(raw.length);
      const client = upstream.protocol === "https:" ? https : http;
      const basePath = upstream.pathname.replace(/\/$/, "");
      const up = client.request(
        { hostname: upstream.hostname, port: upstream.port || undefined, path: basePath + req.url, method: req.method, headers },
        (upRes) => {
          res.writeHead(upRes.statusCode ?? 502, upRes.headers);
          const out = [];
          upRes.on("data", (c) => {
            out.push(c);
            res.write(c);
          });
          upRes.on("end", () => {
            res.end();
            let body = null;
            try {
              body = raw.length ? JSON.parse(raw.toString("utf8")) : null;
            } catch {
              body = raw.toString("utf8").slice(0, 2000);
            }
            const responseText = Buffer.concat(out).toString("utf8");
            fs.appendFileSync(
              log,
              JSON.stringify({
                ts: new Date().toISOString(),
                path: req.url,
                body,
                status: upRes.statusCode,
                responseText: responseText.length > 4000000 ? responseText.slice(-4000000) : responseText,
              }) + "\n",
            );
          });
        },
      );
      up.on("error", (e) => {
        res.writeHead(502);
        res.end(String(e));
      });
      up.end(raw);
    });
  })
  .listen(port, "127.0.0.1", () => console.log(`logproxy :${port} -> ${upstream.href} log=${log}`));
