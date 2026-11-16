#!/usr/bin/env python3
"""Ask the porotomo-induced-seismicity clio-agent blueprint one question via the SDK.

`clio-agent --query` always runs the built-in `main` agent and auto-denies every
tool permission. This driver:
  1. creates a session and activates our blueprint on it
     (POST /v1/sessions/{sid}/agent-blueprint),
  2. posts the question,
  3. streams the turn, approving only the tools in --allow (default: the
     read-only hdf5_* tools; shell stays denied unless --allow-shell),
  4. prints the answer and writes a JSON transcript (tool calls, permission
     decisions, answer, timings) to --out.

Start the server first with start-alcf-mistral.sh (no question argument), or
let this script fail fast if nothing listens on --url.

    run_query.py "List the datasets in ... with shape and dtype" --out result.json
"""
import argparse
import json
import sys
import time

from clio_agent.sdk import ClioClient
from clio_agent.sdk.events import (
    MessageCompleted, MessagePartDelta, PermissionRequested,
    ToolCallCompleted, ToolCallStarted,
)

BLUEPRINT = "porotomo-induced-seismicity"


def _field(p):
    md = getattr(p, "metadata", None) or {}
    return md.get("signature_field_name", "") if isinstance(md, dict) else ""


def split_answer(parts):
    """Return (answer, trace) from an assistant message's parts.

    The agent's final answer is the text part(s) whose metadata
    signature_field_name is "answer". Thinking parts and intermediate text
    ("next_thought") are reasoning; they go to the trace, not the answer.
    Without an "answer" part, the last text part is the answer.
    """
    trace, answer = [], []
    texts = [p for p in parts if getattr(p, "type", "") == "text" and getattr(p, "text", "")]
    for p in parts:
        kind, t = getattr(p, "type", ""), getattr(p, "text", "") or ""
        if kind == "text" and _field(p) == "answer":
            answer.append(t)
        elif t:
            trace.append(dict(type=kind, agent=getattr(p, "agent_id", ""), text=t))
    if not answer and texts:
        answer = [texts[-1].text]
        trace = [x for x in trace if x["text"] != texts[-1].text]
    return "\n".join(answer).strip(), trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--blueprint", default=BLUEPRINT)
    ap.add_argument("--allow-prefix", action="append", default=["hdf5_"],
                    help="tool-name prefixes to approve (repeatable)")
    ap.add_argument("--allow-shell", action="store_true")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    allow = tuple(a.allow_prefix) + (("shell_bash",) if a.allow_shell else ())

    log = dict(question=a.question, blueprint=a.blueprint, tools=[], permissions=[])
    t0 = time.time()
    with ClioClient(a.url) as c:
        s = c.sessions.create(title=f"{a.blueprint}: {a.question[:40]}")
        log["session_id"] = s.id
        r = c._request("POST", f"/v1/sessions/{s.id}/agent-blueprint",
                       json={"blueprint_id": a.blueprint})
        log["blueprint_activation"] = r.json()
        agents = [x.id for x in c.agents(session_id=s.id)]
        log["agents"] = agents
        print(f"session {s.id}; agents {agents}", file=sys.stderr)

        ack = c.messages.post(s.id, text=a.question)
        log["message_ack"] = ack.model_dump() if hasattr(ack, "model_dump") else str(ack)
        text = []
        with c.sessions.events(s.id, reconnect_attempts=3) as stream:
            for ev in stream:
                if time.time() - t0 > a.timeout:
                    log["status"] = "timeout"
                    break
                if isinstance(ev, PermissionRequested):
                    p = ev.permission
                    name = p.tool_call.tool_name or ""
                    decision = "allow" if name.startswith(allow) else "deny"
                    c.permissions.respond(p.id, decision)
                    log["permissions"].append(dict(tool=name, decision=decision))
                    print(f"[permission] {name}: {decision}", file=sys.stderr)
                elif isinstance(ev, ToolCallStarted):
                    print(f"[tool] {ev.tool} ...", file=sys.stderr)
                elif isinstance(ev, ToolCallCompleted):
                    log["tools"].append(dict(tool=ev.tool, ok=ev.ok))
                    print(f"[tool] {ev.tool} ok={ev.ok}", file=sys.stderr)
                elif isinstance(ev, MessagePartDelta):
                    text.append(ev.text_append)
                elif isinstance(ev, MessageCompleted):
                    log["stop_reason"] = ev.stop_reason
                    err = ev.error_info
                    if err:
                        log["error"] = err.model_dump() if hasattr(err, "model_dump") else str(err)
                    log.setdefault("status", "completed")
                    break
        # The ledger holds the authoritative final text (deltas include reasoning
        # and tool chatter).
        msgs = c.messages.list(s.id)
        final = next((m for m in msgs if getattr(m, "role", "") == "assistant"), None)
        if final is not None:
            log["answer"], log["trace"] = split_answer(final.parts or [])
            log["answer"] = log["answer"] or "".join(text).strip()
        else:
            log["answer"] = "".join(text).strip()
    log["elapsed_s"] = round(time.time() - t0, 1)
    print(log["answer"])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(log, f, indent=2, default=str)
    return 0 if log.get("status") == "completed" and not log.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
