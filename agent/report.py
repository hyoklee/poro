#!/usr/bin/env python3
"""Print the headline numbers of an agent run in about 1 KB of plain text.

    report.py <run_dir>

Reads <run_dir>/summary.json (written by hazard.py) and prints only what an LLM
needs to answer the usual questions: coverage, anomalies, detections, the
catalogue-based seismogenic index and probabilities for each b scenario, and
the DAS upper bound. Values are printed with 4 significant figures; read
summary.json for full precision. This keeps an LLM agent from loading the
whole 7 KB summary into its context.
"""
import json
import sys
from pathlib import Path


def g(x):
    return f"{x:.4g}"


def main(run):
    s = json.loads((Path(run) / "summary.json").read_text())
    r, a, e = s["records"], s["anomalies"], s["das_events"]
    p, cat = s["pumping"], s["catalog"]
    out = [
        f"run: {Path(run).resolve()}",
        f"records analysed: {r['analysed']} (stride {r['stride']}, "
        f"{r['first']} to {r['last']}, {g(100 * r['sampled_fraction_of_time'])} % of time)",
        f"anomalous records (|robust z| > {g(a['z_threshold'])}): {a['n_anomalous']}",
        f"DAS detections: {e['n']} in {e['records_with_events']} records; "
        f"relative b {g(e['b_relative'])} ({e['n_above_mc']} above Mc)",
        f"pumping: injected {g(p['injected_m3'])} m3, extracted {g(p['extracted_m3'])} m3, "
        f"net {g(p['net_injected_m3'])} m3 over {g(p['days'])} days",
        f"catalogue: {cat.get('n')} events, ML {cat.get('mc')} to {cat.get('mag_max')} "
        f"({cat.get('source', 'LBNL/NCEDC')})",
        "",
        "CALIBRATED (catalogue-based, Shapiro et al. 2021 Eq. 5):",
        "  b     Sigma     P(M>=5.5)/yr  P(M>=5.5) observed volume  P(M>=3)/yr",
    ]
    for b, h in s["hazard_catalog_based"].items():
        out.append(f"  {b[2:]:<5} {g(h['sigma']):<9} {g(h['p_per_year_at_observed_rate']['M>=5.5']):<13} "
                   f"{g(h['p_over_observed_volume']['M>=5.5']):<26} {g(h['p_per_year_at_observed_rate']['M>=3.0'])}")
    u = s["hazard_das_upper_bound"]
    out += [
        "",
        "UPPER BOUND (DAS-based, uncalibrated magnitudes; every detection counted "
        "as an event at or above the catalogue Mc, so it over-counts):",
        f"  b {g(u['b_used'])}, Sigma {g(u['sigma'])}, "
        f"P(M>=5.5)/yr {g(u['p_per_year_at_observed_rate']['M>=5.5'])}",
    ]
    print("\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
