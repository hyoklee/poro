#!/usr/bin/env python3
"""Ask a clio-agent blueprint one question via the SDK.

`clio-agent --query` always runs the built-in `main` agent and auto-denies every
tool permission. This driver:
  1. creates a session and activates our blueprint on it
     (POST /v1/sessions/{sid}/agent-blueprint),
  2. posts the question,
  3. streams the turn, approving only the tools in --allow-prefix (default: the
     read-only hdf5_* tools; shell stays denied unless --allow-shell),
  4. prints the answer and writes a JSON transcript (tool calls, permission
     decisions, answer, reasoning trace, tokens, timings) to --out.

Start the server first with start-alcf-mistral.sh (no question argument), or
let this script fail fast if nothing listens on --url.

    run_query.py "List the datasets in ... with shape and dtype" --out result.json

`ask()` is also used by bench.py.
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

BLUEPRINT = "porotomo-is-tuned"


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


def session_tokens(c, sid):
    """Token totals for a session plus every child session it spawned.

    The ALCF gateway reports no usage, so clio-agent fills these from its own
    estimate; compare them between runs, not against provider bills.
    """
    tin = tout = 0
    n = 0
    for s in [c.sessions.get(sid)] + [x for x in c.sessions.list() if x.parent_session_id == sid]:
        tin += s.tokens_input or 0
        tout += s.tokens_output or 0
        n += 1
    return tin, tout, n


def ask(c, question, blueprint=BLUEPRINT, allow=("hdf5_",), timeout=900, verbose=True,
        effort=None):
    """Run one question on a fresh session; return the transcript dict.

    effort sets this turn's reasoning effort (off, minimal, low, medium, high,
    xhigh, max); child experts inherit it. None keeps the configured level.
    """
    say = (lambda *a: print(*a, file=sys.stderr)) if verbose else (lambda *a: None)
    log = dict(question=question, blueprint=blueprint, effort=effort, tools=[], permissions=[])
    t0 = time.time()
    s = c.sessions.create(title=f"{blueprint}: {question[:40]}")
    log["session_id"] = s.id
    r = c._request("POST", f"/v1/sessions/{s.id}/agent-blueprint",
                   json={"blueprint_id": blueprint})
    log["blueprint_activation"] = r.json()
    log["agents"] = [x.id for x in c.agents(session_id=s.id)]
    say(f"session {s.id}; agents {log['agents']}")

    body = {"parts": [{"type": "text", "text": question}]}
    if effort:
        # The SDK's messages.post has no behavior argument.
        body["behavior"] = {"reasoning_effort": effort}
    log["message_ack"] = c._request("POST", f"/v1/sessions/{s.id}/messages", json=body).json()
    text = []
    t_first = None
    with c.sessions.events(s.id, reconnect_attempts=3) as stream:
        for ev in stream:
            if time.time() - t0 > timeout:
                log["status"] = "timeout"
                break
            if isinstance(ev, PermissionRequested):
                p = ev.permission
                name = p.tool_call.tool_name or ""
                decision = "allow" if name.startswith(tuple(allow)) else "deny"
                c.permissions.respond(p.id, decision)
                log["permissions"].append(dict(tool=name, decision=decision))
                say(f"[permission] {name}: {decision}")
            elif isinstance(ev, ToolCallStarted):
                say(f"[tool] {ev.tool} ...")
            elif isinstance(ev, ToolCallCompleted):
                log["tools"].append(dict(tool=ev.tool, ok=ev.ok))
                say(f"[tool] {ev.tool} ok={ev.ok}")
            elif isinstance(ev, MessagePartDelta):
                if t_first is None and ev.text_append:
                    t_first = time.time() - t0
                text.append(ev.text_append)
            elif isinstance(ev, MessageCompleted):
                log["stop_reason"] = ev.stop_reason
                err = ev.error_info
                if err:
                    log["error"] = err.model_dump() if hasattr(err, "model_dump") else str(err)
                log.setdefault("status", "completed")
                break
    log["elapsed_s"] = round(time.time() - t0, 1)
    log["first_text_s"] = round(t_first, 1) if t_first is not None else None
    # The ledger holds the authoritative final text (deltas include reasoning
    # and tool chatter).
    msgs = c.messages.list(s.id)
    final = next((m for m in msgs if getattr(m, "role", "") == "assistant"), None)
    if final is not None:
        log["answer"], log["trace"] = split_answer(final.parts or [])
        log["answer"] = log["answer"] or "".join(text).strip()
        log["delegations"] = sum(1 for p in (final.parts or [])
                                 if getattr(p, "type", "") == "expert_handoff"
                                 and getattr(p, "text", "").find("->") >= 0)
    else:
        log["answer"] = "".join(text).strip()
    log["tokens_input"], log["tokens_output"], log["sessions"] = session_tokens(c, s.id)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--blueprint", default=BLUEPRINT)
    ap.add_argument("--allow-prefix", action="append", default=["hdf5_"],
                    help="tool-name prefixes to approve (repeatable)")
    ap.add_argument("--allow-shell", action="store_true")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--effort", default=None,
                    choices=["off", "minimal", "low", "medium", "high", "xhigh", "max"],
                    help="reasoning effort for this question (default: configured level)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    allow = tuple(a.allow_prefix) + (("shell_bash",) if a.allow_shell else ())
    with ClioClient(a.url) as c:
        log = ask(c, a.question, a.blueprint, allow, a.timeout, effort=a.effort)
    print(log["answer"])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(log, f, indent=2, default=str)
    return 0 if log.get("status") == "completed" and not log.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
