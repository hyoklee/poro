#!/usr/bin/env python3
"""Benchmark clio-agent blueprint variants on fixed questions.

    bench.py --reps 3 --out ~/poro/agent/results/llm/bench_<stamp>

For every repetition it runs each (task, blueprint) pair once, interleaved so
gateway load drifts affect all variants alike. Per run it records wall time,
time to first streamed text, tokens (main + child sessions; clio-agent's own
estimate, because the ALCF gateway reports none), tool calls, delegations, and
an accuracy score: the fraction of expected values from summary.json (or h5py)
that appear in the answer. Writes runs.jsonl, one transcript per run, and
summary.md.
"""
import argparse
import json
import re
import statistics as st
import sys
import time
from pathlib import Path

try:
    from clio_agent.sdk import ClioClient

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_query import ask  # noqa: E402
except ImportError:  # clio-agent >= 0.9.7: bench_0971.py imports only the scoring
    ClioClient = ask = None

RUN = Path.home() / "poro/agent/results/run_20261115T155359Z_s20"
H5 = Path.home() / "cae_test_data/porotomo/dasv_native_PoroTomo_iDAS025_160318160317.h5"

TASKS = {
    "results": dict(
        question=(f"Report the headline results of the agent run in {RUN}: the number of "
                  "records analysed, anomalous records and DAS detections, the seismogenic "
                  "index Sigma and P(Mw>=5.5) per year for each b scenario, and the DAS-based "
                  "upper bound. Say which is calibrated and which is an upper bound. "
                  "Read-only: do not submit PBS jobs and do not run hazard.py."),
        allow=("shell_bash",),
    ),
    "hdf5": dict(
        question=f"List every dataset in {H5} with its shape and dtype.",
        allow=("hdf5_",),
    ),
}

SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
NUM = re.compile(r"[-−–]?\d[\d,]*(?:\.\d+)?(?:[eE][-+−]?\d+)?"
                 r"(?:\s*(?:×|x|\*)\s*10\^?\(?[-−]?\d+\)?)?\s*%?")


def numbers(text):
    """Every number in the text, including '1.2 × 10⁻⁴', '1.2e-4' and '0.49 %'."""
    out = []
    for m in NUM.finditer(text.translate(SUP)):
        tok = m.group(0).replace("−", "-").replace("–", "-").replace(",", "").strip()
        pct = tok.endswith("%")
        tok = tok.rstrip("%").strip()
        mm = re.match(r"(-?[\d.]+(?:[eE][-+]?\d+)?)\s*(?:×|x|\*)\s*10\^?\(?(-?\d+)\)?", tok)
        try:
            v = float(mm.group(1)) * 10 ** int(mm.group(2)) if mm else float(tok)
        except ValueError:
            continue
        out.append(v)
        if pct:
            out.append(v / 100)
    return out


def expected_results():
    s = json.loads((RUN / "summary.json").read_text())
    exp = {"records": s["records"]["analysed"], "anomalous": s["anomalies"]["n_anomalous"],
           "detections": s["das_events"]["n"]}
    for b, h in s["hazard_catalog_based"].items():
        exp[f"sigma {b}"] = h["sigma"]
        exp[f"P5.5/yr {b}"] = h["p_per_year_at_observed_rate"]["M>=5.5"]
    u = s["hazard_das_upper_bound"]
    exp["DAS sigma"] = u["sigma"]
    exp["DAS P5.5/yr"] = u["p_per_year_at_observed_rate"]["M>=5.5"]
    return exp


def score_results(answer, exp, tol=0.02):
    vals = numbers(answer)
    hits = {k: any(abs(v - e) <= tol * abs(e) for v in vals) for k, e in exp.items()}
    low = answer.lower()
    hits["says calibrated"] = "calibrat" in low
    hits["says upper bound"] = "upper bound" in low or "upper-bound" in low
    return sum(hits.values()) / len(hits), [k for k, ok in hits.items() if not ok]


def expected_hdf5():
    import h5py
    with h5py.File(H5, "r") as f:
        return {k: (f[k].shape, str(f[k].dtype)) for k in f}


def score_hdf5(answer, exp):
    """A dataset counts if its name, dtype and every shape number appear on one line."""
    lines = answer.splitlines()
    miss = []
    for name, (shape, dtype) in exp.items():
        ok = any(re.search(rf"\b{name}\b", ln) and dtype in ln
                 and all(str(n) in ln.replace(",", "") for n in shape) for ln in lines)
        if not ok:
            miss.append(name)
    return 1 - len(miss) / len(exp), miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--configs", default="results:porotomo-induced-seismicity,"
                    "results:porotomo-is-digest,results:porotomo-is-single-heavy,"
                    "results:porotomo-is-single-light,hdf5:porotomo-induced-seismicity,"
                    "hdf5:porotomo-is-single-light")
    ap.add_argument("--timeout", type=float, default=600)
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    (out / "runs").mkdir(parents=True, exist_ok=True)
    # task:blueprint[:effort]
    configs = [tuple((x.split(":") + [""])[:3]) for x in a.configs.split(",")]
    exp = {"results": expected_results(), "hdf5": expected_hdf5()}
    scorer = {"results": score_results, "hdf5": score_hdf5}
    rows = []
    with ClioClient(a.url, timeout=a.timeout) as c, open(out / "runs.jsonl", "a") as fl:
        for rep in range(1, a.reps + 1):
            for task, bp, eff in configs:
                t = TASKS[task]
                print(f"rep {rep} {task} {bp} {eff or 'default'} ...", file=sys.stderr, flush=True)
                try:
                    log = ask(c, t["question"], bp, t["allow"], a.timeout, verbose=False,
                              effort=eff or None)
                except Exception as ex:  # keep the benchmark going
                    log = dict(status="exception", error=repr(ex), answer="", elapsed_s=None)
                acc, miss = scorer[task](log.get("answer", ""), exp[task])
                row = dict(rep=rep, task=task, blueprint=bp, effort=eff or "default", status=log.get("status"),
                           error=bool(log.get("error")), elapsed_s=log.get("elapsed_s"),
                           first_text_s=log.get("first_text_s"),
                           tokens_input=log.get("tokens_input"), tokens_output=log.get("tokens_output"),
                           sessions=log.get("sessions"), tool_calls=len(log.get("tools", [])),
                           delegations=log.get("delegations"), accuracy=round(acc, 3), missed=miss,
                           session_id=log.get("session_id"), at=time.strftime("%H:%M:%S"))
                rows.append(row)
                fl.write(json.dumps(row) + "\n"); fl.flush()
                (out / "runs" / f"{task}_{bp}{'_' + eff if eff else ''}_r{rep}.json").write_text(json.dumps(log, indent=2, default=str))
                print("   ", {k: row[k] for k in ("status", "elapsed_s", "tokens_input",
                                                   "tokens_output", "tool_calls", "accuracy", "missed")},
                      file=sys.stderr, flush=True)
    summarize(rows, out / "summary.md")


def summarize(rows, path):
    def med(xs):
        xs = [x for x in xs if x is not None]
        return st.median(xs) if xs else None
    lines = ["| task | blueprint | effort | runs ok | wall s (median, min–max) | input tokens | output tokens | "
             "tool calls | delegations | accuracy (mean) |", "|---|---|---|---|---|---|---|---|---|---|"]
    keys = []
    for r in rows:
        k = (r["task"], r["blueprint"], r.get("effort", "default"))
        if k not in keys:
            keys.append(k)
    for task, bp, eff in keys:
        rs = [r for r in rows if (r["task"], r["blueprint"], r.get("effort", "default")) == (task, bp, eff)]
        ok = [r for r in rs if r["status"] == "completed" and not r["error"]]
        w = [r["elapsed_s"] for r in ok]
        lines.append(
            f"| {task} | {bp} | {eff} | {len(ok)}/{len(rs)} | "
            + (f"{med(w):.1f} ({min(w):.1f}–{max(w):.1f})" if w else "–") + " | "
            + f"{med([r['tokens_input'] for r in ok]) or 0:,.0f} | {med([r['tokens_output'] for r in ok]) or 0:,.0f} | "
            + f"{med([r['tool_calls'] for r in ok]) or 0:g} | {med([r['delegations'] for r in ok]) or 0:g} | "
            + (f"{st.mean(r['accuracy'] for r in rs):.2f}" if rs else "–") + " |")
    Path(path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
