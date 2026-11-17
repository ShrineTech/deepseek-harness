# metrics.py <proxy.jsonl> [--json]: harness-neutral numbers for one run, read from the wire (the logging proxy),
# so dsh and Sando are measured the same way.
#   req   chat/completions requests          pt/ct  prompt / completion tokens (server `usage`; `timings` fallback)
#   calls tool calls the model made          bad    tool calls with unparseable JSON arguments
#   err   tool results that report a harness/tool error (unknown tool, bad args, missing file, edit mismatch, denied,
#         timeout); a test run that exits non-zero, or prints "Error:", is NOT an error
#   reread  a file read again with no write to it in between (read/view tools, or cat/head/tail/sed -n/nl in bash)
#   spill   reads of a harness spill/overflow file (truncated tool output stored outside the repo)
import json, re, shlex, sys

READ_TOOLS = {"read", "view", "read_file", "readfile"}
WRITE_TOOLS = {"write", "edit", "multiedit", "multi_edit", "apply_patch", "write_file", "str_replace", "notebookedit"}
ERR_RE = re.compile(
    r"^\s*(<tool_use_error>|error\b|Error:|\[error\]|Tool error|Invalid (tool|input|arguments)|Unknown tool|"
    r"File (does not exist|not found)|No such file|String to replace not found|old_string|Permission denied|"
    r"Command timed out|Timed out|refus)", re.I)
# A shell result carries the program's own output (which may well start with "Error:"), so for shell tools only the
# harness's own failure markers count.
SHELL_ERR_RE = re.compile(r"(<tool_use_error>|Command timed out|timed out after|\[sandbox: |no sandbox backend|Unknown tool|"
                          r"Invalid (tool|input|arguments)|refusing to run)", re.I)
SHELL_TOOLS = {"bash", "shell", "run_command"}
SPILL_RE = re.compile(r"(spill|tool-results?|overflow|\.dsh/|dsh-home/|/\.zcode/)", re.I)


def sse_tool_calls(text):
    """Tool calls in one (streamed or plain) chat/completions response: [(id, name, args_str)]."""
    calls = {}
    chunks = []
    for line in text.splitlines():
        if line.startswith("data: ") and line[6:].strip() not in ("", "[DONE]"):
            try:
                chunks.append(json.loads(line[6:]))
            except ValueError:
                pass
    if not chunks:
        try:
            chunks = [json.loads(text)]
        except ValueError:
            return []
    for c in chunks:
        for ch in c.get("choices") or []:
            msg = ch.get("delta") or ch.get("message") or {}
            for i, tc in enumerate(msg.get("tool_calls") or []):
                k = tc.get("index", i)
                cur = calls.setdefault(k, {"id": None, "name": "", "args": ""})
                cur["id"] = tc.get("id") or cur["id"]
                fn = tc.get("function") or {}
                cur["name"] += fn.get("name") or ""
                a = fn.get("arguments")
                cur["args"] += a if isinstance(a, str) else (json.dumps(a) if a is not None else "")
    return [(v["id"], v["name"], v["args"]) for _, v in sorted(calls.items())]


def usage(text):
    i = text.rfind('"usage":{')
    if i >= 0:
        seg = text[i:i + 600]
        p = re.search(r'"prompt_tokens":(\d+)', seg)
        c = re.search(r'"completion_tokens":(\d+)', seg)
        if p or c:
            return int(p.group(1)) if p else 0, int(c.group(1)) if c else 0
    tm = re.findall(r'"timings":\{[^}]*\}', text)
    if tm:
        t = json.loads(tm[-1][10:])
        return t.get("prompt_n", 0) + t.get("cache_n", 0), t.get("predicted_n", 0)
    return 0, 0


def content_text(c):
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c if isinstance(c, str) else json.dumps(c)


def touched_paths(name, args):
    """('read'|'write'|None, [paths]) for a tool call."""
    n = name.lower()
    try:
        a = json.loads(args) if args else {}
    except ValueError:
        return None, []
    if not isinstance(a, dict):
        return None, []
    p = a.get("file_path") or a.get("path") or a.get("filePath")
    if n in READ_TOOLS and p:
        return "read", [p]
    if n in WRITE_TOOLS and p:
        return "write", [p]
    if n in ("bash", "shell", "run_command"):
        cmd = a.get("command") or a.get("cmd") or ""
        if not isinstance(cmd, str) or any(x in cmd for x in "|;&><`$("):
            return None, []
        try:
            w = shlex.split(cmd)
        except ValueError:
            return None, []
        if w and w[0] in ("cat", "head", "tail", "nl") or w[:2] == ["sed", "-n"]:
            return "read", [x for x in w[1:] if not x.startswith("-") and not re.fullmatch(r"[\d,p]+", x)]
    return None, []


def main(path):
    req = pt = ct = calls = bad = 0
    results = {}  # tool_call_id -> text
    order = []  # (id, name, args) in call order
    for line in open(path):
        d = json.loads(line)
        if not d["path"].endswith("/chat/completions"):
            continue
        req += 1
        p, c = usage(d["responseText"])
        pt += p
        ct += c
        for m in (d.get("body") or {}).get("messages", []) if isinstance(d.get("body"), dict) else []:
            if m.get("role") == "tool" and m.get("tool_call_id"):
                results.setdefault(m["tool_call_id"], content_text(m.get("content")))
        for tc in sse_tool_calls(d["responseText"]):
            if not tc[1]:
                continue  # a fragment of a response the proxy cut short
            calls += 1
            order.append(tc)
            try:
                json.loads(tc[2] or "{}")
            except ValueError:
                bad += 1
    err = sum(1 for (i, n, _) in order if i in results
              and (SHELL_ERR_RE if n.lower() in SHELL_TOOLS else ERR_RE).search(results[i][:300] or ""))
    reread = spill = 0
    seen = set()
    for _, name, args in order:
        kind, paths = touched_paths(name, args)
        for p in paths:
            key = p.rstrip("/").split("/repo/")[-1].lstrip("./")
            if kind == "read":
                if "/repo/" not in p and p.startswith("/") and SPILL_RE.search(p):
                    spill += 1
                if key in seen:
                    reread += 1
                seen.add(key)
            elif kind == "write":
                seen.discard(key)
    out = dict(req=req, pt=pt, ct=ct, calls=calls, bad=bad, err=err, reread=reread, spill=spill)
    if "--json" in sys.argv:
        print(json.dumps(out))
    else:
        print(" ".join(f"{k}={v}" for k, v in out.items()))


if __name__ == "__main__":
    main(sys.argv[1])
