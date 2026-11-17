#!/usr/bin/env python3
"""Run the "results" benchmark question on clio-agent >= 0.9.7 (no blueprints).

clio-agent 0.9.7 removed agent blueprints (and POST /v1/sessions/{sid}/agent-blueprint);
agents are now Python classes in plugin marketplaces. To compare with the
0.9.4.24 runs without porting the blueprint, this driver uses the built-in
`standard` agent and puts the tuned expert's instructions
(variants/porotomo-is-tuned/experts/main.md, minus its front matter) in front of
the question. Only shell tools are approved. Scoring is bench.py's.

Run it with the 0.9.7.x venv's python, against a server started from an empty
folder (0.9.7.1 adopts a session store in <cwd>/.clio/agent):

    bench_0971.py --n 60 --out ~/poro/agent/results/llm/bench_<stamp> --url http://127.0.0.1:8101

Answers are also checked for the #2369 truncation: the turn's submit args must
contain only `answer` / `workflow_state`, and the answer must be longer than
300 characters.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from clio_agent.client import ClioClient
from clio_agent.client.events import (
    MessageCompleted, MessagePartDelta, PermissionRequested, ToolCallCompleted,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import TASKS, expected_results, score_results  # noqa: E402

EXPERT = HERE / "variants/porotomo-is-tuned/experts/main.md"


def instructions(submit_hint=True):
    text = EXPERT.read_text()
    body = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)[-1]
    if not submit_hint:
        # The round-6 prompt: without the empty-workflow_state workaround for #2369.
        body = re.sub(r"^- When you call `submit`.*?(?=^\S|\n\n)", "", body, flags=re.M | re.S)
    return body.strip()


def answer_of(msg):
    parts = msg.parts or []
    ans = [p.text for p in parts if getattr(p, "type", "") == "text" and getattr(p, "text", "")
           and ((getattr(p, "metadata", None) or {}).get("signature_field_name") == "answer")]
    if not ans:
        texts = [p.text for p in parts if getattr(p, "type", "") == "text" and getattr(p, "text", "")]
        ans = texts[-1:]
    return "\n".join(ans).strip()


def ask(c, question, agent, timeout):
    log = dict(question=question, agent=agent, tools=[], permissions=[])
    t0 = time.time()
    s = c.sessions.create(title=f"bench0971: {question[:40]}")
    log["session_id"] = s.id
    # The session's agent comes from session defaults (clio/standard); the server
    # rejects the client's own agent_id argument (422) in 0.9.7.1.
    log["agent_ref"] = (s.metadata or {}).get("agent_ref")
    c.messages.post(s.id, question)
    with c.sessions.events(s.id, reconnect_attempts=3) as stream:
        for ev in stream:
            if time.time() - t0 > timeout:
                log["status"] = "timeout"
                break
            if isinstance(ev, PermissionRequested):
                p = ev.permission
                name = p.tool_call.tool_name or ""
                decision = "allow" if name.startswith("shell") else "deny"
                c.permissions.respond(p.id, decision)
                log["permissions"].append(dict(tool=name, decision=decision))
            elif isinstance(ev, ToolCallCompleted):
                log["tools"].append(dict(tool=ev.tool, ok=ev.ok))
            elif isinstance(ev, MessagePartDelta):
                pass
            elif isinstance(ev, MessageCompleted):
                log["stop_reason"] = ev.stop_reason
                err = ev.error_info
                if err:
                    log["error"] = err.model_dump() if hasattr(err, "model_dump") else str(err)
                log.setdefault("status", "completed")
                break
    log["elapsed_s"] = round(time.time() - t0, 1)
    msgs = [m for m in c.messages.list(s.id) if getattr(m, "role", "") == "assistant"]
    log["answer"] = answer_of(msgs[-1]) if msgs else ""
    try:
        sess = c.sessions.get(s.id)
        log["tokens_input"], log["tokens_output"] = sess.tokens_input, sess.tokens_output
    except Exception:  # noqa: BLE001
        pass
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8101")
    ap.add_argument("--agent", default="standard")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-submit-hint", action="store_true",
                    help="drop the empty-workflow_state line (round-6 prompt)")
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    (out / "runs").mkdir(parents=True, exist_ok=True)
    exp = expected_results()
    question = instructions(not a.no_submit_hint) + "\n\n---\n\n" + TASKS["results"]["question"]
    rows = []
    with ClioClient(a.url, timeout=a.timeout) as c, open(out / "runs.jsonl", "a") as fl:
        (out / "versions.json").write_text(json.dumps(
            dict(health=c.health().model_dump(), agents=[x.model_dump() for x in c.agents()]),
            indent=2, default=str))
        for i in range(1, a.n + 1):
            try:
                log = ask(c, question, a.agent, a.timeout)
            except Exception as ex:  # noqa: BLE001
                log = dict(status="exception", error=repr(ex), answer="", elapsed_s=None)
            acc, miss = score_results(log.get("answer", ""), exp)
            row = dict(i=i, status=log.get("status"), error=bool(log.get("error")),
                       elapsed_s=log.get("elapsed_s"), answer_chars=len(log.get("answer", "")),
                       tool_calls=len(log.get("tools", [])), accuracy=round(acc, 3), missed=miss,
                       tokens_input=log.get("tokens_input"), tokens_output=log.get("tokens_output"),
                       session_id=log.get("session_id"), at=time.strftime("%H:%M:%S"))
            rows.append(row)
            fl.write(json.dumps(row) + "\n"); fl.flush()
            (out / "runs" / f"r{i:02d}.json").write_text(json.dumps(log, indent=2, default=str))
            print(i, {k: row[k] for k in ("status", "elapsed_s", "answer_chars", "tool_calls",
                                          "accuracy", "missed")}, file=sys.stderr, flush=True)
    ok = [r for r in rows if r["status"] == "completed" and not r["error"]]
    full = [r for r in rows if r["accuracy"] == 1.0]
    w = sorted(r["elapsed_s"] for r in ok)
    summary = (f"agent {a.agent}: {len(ok)}/{len(rows)} completed, {len(full)}/{len(rows)} fully "
               f"correct; median wall {w[len(w)//2] if w else '-'} s\n")
    (out / "summary.md").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
