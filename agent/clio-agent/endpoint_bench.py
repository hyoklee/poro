#!/usr/bin/env python3
"""Time raw chat completions on ALCF inference endpoints, without clio-agent.

    endpoint_bench.py --reps 3 --out endpoints.jsonl

Sends the same prompt (the ~1 KB report.py output plus a question) as a
streaming chat completion and records time to first token, total time, output
length and output rate. Uses clio-agent's stored Globus token (never printed).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
from clio_agent.providers.argonne_auth import get_access_token

BASE = "https://inference-api.alcf.anl.gov/resource_server"
TARGETS = {
    "minerva/mistral-large-4-nvfp4": f"{BASE}/minerva/api/v1",
    "tara/mistral-large-4": f"{BASE}/tara/api/v1",
}
RUN = Path.home() / "poro/agent/results/run_20261115T155359Z_s20"


def one(client, url, model, prompt, max_tokens):
    t0 = time.time()
    ttft, chunks, usage, text, fields = None, 0, None, [], set()
    body = dict(model=model, stream=True, max_tokens=max_tokens, temperature=0,
                stream_options={"include_usage": True},
                messages=[{"role": "user", "content": prompt}])
    with client.stream("POST", f"{url}/chat/completions", json=body) as r:
        if r.status_code != 200:
            return dict(status=r.status_code, error=r.read().decode()[:300], total_s=round(time.time() - t0, 2))
        for line in r.iter_lines():
            if not line.startswith("data:") or line.strip() == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            if d.get("usage"):
                usage = d["usage"]
            for ch in d.get("choices") or []:
                delta = ch.get("delta") or {}
                # Reasoning models stream thinking under reasoning_content/reasoning.
                for field in ("content", "reasoning_content", "reasoning"):
                    piece = delta.get(field) or ""
                    if piece:
                        if ttft is None:
                            ttft = time.time() - t0
                        chunks += 1
                        fields.add(field)
                        if field == "content":
                            text.append(piece)
    total = time.time() - t0
    out_tok = (usage or {}).get("completion_tokens") or chunks
    gen = total - (ttft or total)
    return dict(status=200, ttft_s=round(ttft, 2) if ttft else None, total_s=round(total, 2),
                prompt_tokens=(usage or {}).get("prompt_tokens"), output_tokens=out_tok,
                usage_reported=bool(usage), delta_fields=sorted(fields), tok_per_s=round(out_tok / gen, 1) if gen > 0 else None,
                answer_head="".join(text)[:120])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    report = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "report.py"), str(RUN)],
                            capture_output=True, text=True, check=True).stdout
    prompt = (report + "\n\nFrom the report above, give the number of records analysed, "
              "Sigma and P(Mw>=5.5) per year for each b, and the DAS upper bound, and say "
              "which is calibrated. Be brief.")
    tok = get_access_token(allow_interactive=False)
    with httpx.Client(headers={"Authorization": f"Bearer {tok}"}, timeout=a.timeout) as client, \
            open(a.out, "a") as f:
        for rep in range(1, a.reps + 1):
            for name, url in TARGETS.items():
                model = name.split("/", 1)[1]
                try:
                    row = one(client, url, model, prompt, a.max_tokens)
                except Exception as ex:
                    row = dict(status="exception", error=repr(ex)[:300])
                row.update(target=name, rep=rep, at=time.strftime("%H:%M:%S"))
                f.write(json.dumps(row) + "\n"); f.flush()
                print(json.dumps({k: v for k, v in row.items() if k != "answer_head"}), flush=True)


if __name__ == "__main__":
    main()
