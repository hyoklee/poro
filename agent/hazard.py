#!/usr/bin/env python3
"""Aggregate DASV detections, flag anomalies, and estimate the probability of a
Pohang-like (Mw >= 5.5) induced earthquake at Brady from the observations.

Inputs
  <run>/detect/*.jsonl                      per-record output of detect.py
  agent/sources/brady_pumping_corrected_gdr917.csv   GDR 917 per-minute flows (gpm)
  agent/sources/brady_meq_ncedc_march2016.txt        LBNL/NCEDC catalog, March 2016

Model (Shapiro et al. 2021, Nat. Commun. 12:6397, Eq. 5)
  log10 N(>=M) = Sigma + log10 V - b M
  P(at least one event >= M | V) = 1 - exp(-V * 10**(Sigma - b M))
Sigma is the seismogenic index of the site, V the injected volume in m^3.

Outputs (in <run>/): summary.json, anomalies.csv, events.csv, hourly.csv,
fig_timeseries.png, fig_mfd.png
"""
import argparse
import csv
import datetime as dt
import glob
import io
import json
import math
import os

import numpy as np

GPM_TO_M3_PER_MIN = 3.785411784e-3
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")

# Pohang reference values, all from Shapiro, Kim & Ree (2021), PMC8568929.
POHANG = dict(
    sigma_range=(-2.0, -1.0), b_values=(0.65, 0.73), mainshock_mw=5.5,
    worst_case_probability_reported=(0.15, 0.17),
    v_fig3c_m3=5850.0,
)
POHANG_TOTAL_INJECTED_M3 = 12800.0  # wiki/concept-induced-seismicity-pohang.md


def parse_time(s):
    return dt.datetime.strptime(s.strip(), "%m/%d/%y %H:%M").replace(tzinfo=dt.timezone.utc)


def load_pumping(path):
    text = open(path, newline="").read().replace("\r\n", "\n").replace("\r", "\n")
    rows = list(csv.reader(io.StringIO(text)))
    hdr = rows[0]
    inj = [i for i, h in enumerate(hdr) if "injection flow" in h]
    ext = [i for i, h in enumerate(hdr) if "extraction flow" in h]
    t, qi, qe = [], [], []
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        try:
            t.append(parse_time(r[0]).timestamp())
            qi.append(sum(float(r[i] or 0) for i in inj))
            qe.append(sum(float(r[i] or 0) for i in ext))
        except ValueError:
            continue
    t, qi, qe = map(np.asarray, (t, qi, qe))
    o = np.argsort(t)
    return dict(t=t[o], inj_gpm=qi[o], ext_gpm=qe[o],
                inj_wells=[hdr[i] for i in inj], ext_wells=[hdr[i] for i in ext])


def load_catalog(path):
    ev = []
    for line in open(path):
        p = line.split()
        if p and p[0].startswith("2016/"):
            ev.append(dict(time=f"{p[0]}T{p[1]}", lat=float(p[2]), lon=float(p[3]),
                           depth_km_msl=float(p[4]), mag=float(p[5]), magtype=p[6]))
    return ev


def robust_z(x):
    x = np.asarray(x, float)
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med)) * 1.4826
    return (x - med) / (mad if mad > 0 else np.nanstd(x) + 1e-30)


def aki_b(m, mc, dm=0.1):
    m = m[m >= mc - 1e-9]
    if len(m) < 30:
        return None, len(m)
    return float(math.log10(math.e) / (m.mean() - (mc - dm / 2))), len(m)


def p_exceed(V, sigma, b, M):
    return 1.0 - math.exp(-V * 10 ** (sigma - b * M))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--stride", type=int, default=20, help="manifest stride (records kept 1 in N)")
    ap.add_argument("--zthr", type=float, default=5.0)
    a = ap.parse_args()
    R = a.run_dir

    recs = []
    for f in sorted(glob.glob(os.path.join(R, "detect", "*.jsonl"))):
        recs += [json.loads(l) for l in open(f) if l.strip()]
    best = {}  # one row per key; a later retry that succeeded replaces a failure
    for r in recs:
        if r.get("status") == "ok" or r["key"] not in best:
            best[r["key"]] = r
    recs = list(best.values())
    ok = sorted((r for r in recs if r.get("status") == "ok"), key=lambda r: r["start"])
    status = {}
    for r in recs:
        status[r.get("status")] = status.get(r.get("status"), 0) + 1
    ts = np.array([dt.datetime.fromisoformat(r["start"].replace("Z", "+00:00")).timestamp() for r in ok])

    # ---- record-level anomalies -------------------------------------------
    feats = {
        "log_band_rms": np.log10([r["band_rms"] + 1e-30 for r in ok]),
        "log_kurtosis": np.log10([r["kurtosis"] + 1e-30 for r in ok]),
        "max_sta_lta": np.array([r["max_sta_lta_median"] for r in ok]),
        "spectral_centroid_hz": np.array([r["spectral_centroid_hz"] for r in ok]),
        "n_events": np.array([r["n_events"] for r in ok], float),
    }
    Z = {k: robust_z(v) for k, v in feats.items()}
    zmax = np.max(np.abs(np.vstack(list(Z.values()))), axis=0)
    anomalous = zmax > a.zthr
    with open(os.path.join(R, "anomalies.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start", "key", "zmax", *[f"z_{k}" for k in Z], "n_events"])
        for i in np.argsort(-zmax):
            if not anomalous[i]:
                break
            w.writerow([ok[i]["start"], ok[i]["key"], round(zmax[i], 2),
                        *[round(Z[k][i], 2) for k in Z], ok[i]["n_events"]])

    # ---- event catalogue ----------------------------------------------------
    events = []
    for r, t in zip(ok, ts):
        for e in r["events"]:
            events.append(dict(time=dt.datetime.fromtimestamp(t + e["t_s"], dt.timezone.utc).isoformat(),
                               key=r["key"], **e, mrel=math.log10(e["peak_amp"] + 1e-30)))
    with open(os.path.join(R, "events.csv"), "w", newline="") as f:
        if events:
            w = csv.DictWriter(f, fieldnames=list(events[0]))
            w.writeheader()
            w.writerows(events)
    mrel = np.array([e["mrel"] for e in events])
    b_das, mc_rel, n_b = None, None, len(mrel)
    if len(mrel) >= 30:
        h, edges = np.histogram(mrel, bins=np.arange(mrel.min(), mrel.max() + 0.2, 0.1))
        mc_rel = float(edges[np.argmax(h)])  # maximum-curvature Mc
        b_das, n_b = aki_b(mrel, mc_rel)

    # ---- pumping ------------------------------------------------------------
    pump = load_pumping(os.path.join(SRC, "brady_pumping_corrected_gdr917.csv"))
    pt = pump["t"]
    dtm = np.diff(pt, append=pt[-1] + 60) / 60.0  # minutes per sample
    v_inj = float(np.sum(pump["inj_gpm"] * dtm) * GPM_TO_M3_PER_MIN)
    v_ext = float(np.sum(pump["ext_gpm"] * dtm) * GPM_TO_M3_PER_MIN)
    days = (pt[-1] - pt[0]) / 86400.0
    # window covered by the DAS records
    if len(ts):
        m = (pt >= ts.min()) & (pt <= ts.max() + 30)
        v_inj_das = float(np.sum(pump["inj_gpm"][m] * dtm[m]) * GPM_TO_M3_PER_MIN)
        das_hours = (ts.max() + 30 - ts.min()) / 3600.0
    else:
        v_inj_das, das_hours = 0.0, 0.0

    # hourly series: detections per sampled record vs. pumping
    hourly = []
    if len(ts):
        h0 = math.floor(ts.min() / 3600) * 3600
        for hs in np.arange(h0, ts.max() + 3600, 3600):
            sel = (ts >= hs) & (ts < hs + 3600)
            pm = (pt >= hs) & (pt < hs + 3600)
            if not sel.any() or not pm.any():
                continue
            hourly.append(dict(hour=dt.datetime.fromtimestamp(hs, dt.timezone.utc).isoformat(),
                               records=int(sel.sum()),
                               events_per_record=float(feats["n_events"][sel].mean()),
                               anomalous_records=int(anomalous[sel].sum()),
                               inj_gpm=float(pump["inj_gpm"][pm].mean()),
                               ext_gpm=float(pump["ext_gpm"][pm].mean())))
        with open(os.path.join(R, "hourly.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(hourly[0]))
            w.writeheader()
            w.writerows(hourly)
    corr = {}
    if len(hourly) > 10:
        epr = np.array([h["events_per_record"] for h in hourly])
        net = np.array([h["inj_gpm"] - h["ext_gpm"] for h in hourly])
        dnet = np.abs(np.diff(net, prepend=net[0]))
        inj = np.array([h["inj_gpm"] for h in hourly])
        corr = dict(spearman_events_vs_net_injection=spearman(epr, net),
                    spearman_events_vs_abs_change_in_net=spearman(epr, dnet),
                    spearman_events_vs_injection=spearman(epr, inj))

    # ---- seismogenic index and probabilities -----------------------------------
    cat = load_catalog(os.path.join(SRC, "brady_meq_ncedc_march2016.txt"))
    mags = np.array([c["mag"] for c in cat])
    mc_cat = float(mags.min()) if len(mags) else None
    n_cat = int(len(mags))
    out_sigma = {}
    targets = [3.0, 4.0, 5.5]
    v_year = v_inj / days * 365.25
    if n_cat == 0 or v_inj <= 0:
        raise SystemExit("hazard: need a non-empty catalogue and positive injected volume")
    for b in (1.0, 0.73, 0.65):
        sig = math.log10(n_cat) - math.log10(v_inj) + b * mc_cat
        out_sigma[f"b={b}"] = dict(
            sigma=sig,
            p_over_observed_volume={f"M>={M}": p_exceed(v_inj, sig, b, M) for M in targets},
            p_per_year_at_observed_rate={f"M>={M}": p_exceed(v_year, sig, b, M) for M in targets},
            p_if_pohang_volume={f"M>={M}": p_exceed(POHANG_TOTAL_INJECTED_M3, sig, b, M) for M in targets},
        )
    # DAS-based upper bound: treat every DAS detection as an event >= the catalog's Mc
    n_das = len(events)
    frac_sampled = len(ok) * 30.0 / max(das_hours * 3600.0, 1)
    n_das_scaled = n_das / max(frac_sampled, 1e-9)
    das_sigma = None
    if n_das > 0 and v_inj_das > 0:
        b = b_das if b_das else 1.0
        sig = math.log10(n_das_scaled) - math.log10(v_inj_das) + b * mc_cat
        das_sigma = dict(b_used=b, b_source="DAS relative-magnitude Aki MLE" if b_das else "assumed 1.0",
                         sigma=sig,
                         p_over_observed_volume={f"M>={M}": p_exceed(v_inj_das, sig, b, M) for M in targets},
                         p_per_year_at_observed_rate={f"M>={M}": p_exceed(v_year, sig, b, M) for M in targets})
    pohang_check = {f"sigma={s},b={b}": p_exceed(POHANG_TOTAL_INJECTED_M3, s, b, 5.5)
                    for s in POHANG["sigma_range"] for b in POHANG["b_values"]}
    sigma_needed = {f"b={b}": math.log10(-math.log(1 - 0.01) / v_inj) + b * 5.5 for b in (1.0, 0.73, 0.65)}

    summary = dict(
        generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        records=dict(by_status=status, analysed=len(ok), stride=a.stride,
                     first=ok[0]["start"] if ok else None, last=ok[-1]["start"] if ok else None,
                     sampled_fraction_of_time=frac_sampled,
                     mean_ms_per_record=float(np.mean([r["total_ms"] for r in ok])) if ok else None),
        anomalies=dict(z_threshold=a.zthr, n_anomalous=int(anomalous.sum()),
                       top=[dict(start=ok[i]["start"], zmax=round(float(zmax[i]), 2),
                                 drivers=[k for k in Z if abs(Z[k][i]) > a.zthr])
                            for i in np.argsort(-zmax)[:10] if anomalous[i]]),
        das_events=dict(n=n_das, n_scaled_to_full_time=n_das_scaled, records_with_events=int((feats["n_events"] > 0).sum()),
                        b_relative=b_das, mc_relative=mc_rel, n_above_mc=n_b),
        pumping=dict(source="GDR 917 corrected deployment data", start=dt.datetime.fromtimestamp(pt[0], dt.timezone.utc).isoformat(),
                     end=dt.datetime.fromtimestamp(pt[-1], dt.timezone.utc).isoformat(), days=days,
                     injected_m3=v_inj, extracted_m3=v_ext, net_injected_m3=v_inj - v_ext,
                     injected_m3_during_das_window=v_inj_das,
                     mean_injection_gpm=float(pump["inj_gpm"].mean()), mean_extraction_gpm=float(pump["ext_gpm"].mean()),
                     injection_wells=pump["inj_wells"], extraction_wells=pump["ext_wells"]),
        correlations_hourly=corr,
        catalog=dict(source="GDR 859, LBNL/NCEDC March 2016", n=n_cat, mc=mc_cat,
                     mag_max=float(mags.max()) if len(mags) else None, events=cat),
        hazard_catalog_based=out_sigma,
        hazard_das_upper_bound=das_sigma,
        pohang=dict(reference=POHANG, total_injected_m3=POHANG_TOTAL_INJECTED_M3,
                    p_mw55_recomputed=pohang_check,
                    sigma_needed_at_brady_for_1pct_mw55_over_observed_volume=sigma_needed),
    )
    with open(os.path.join(R, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ---- figures --------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
        pdt = [dt.datetime.fromtimestamp(x, dt.timezone.utc) for x in pt]
        ax[0].plot(pdt, pump["inj_gpm"], lw=0.6, label="injection")
        ax[0].plot(pdt, pump["ext_gpm"], lw=0.6, label="extraction")
        ax[0].set_ylabel("flow [gpm]"); ax[0].legend(loc="upper right")
        rdt = [dt.datetime.fromtimestamp(x, dt.timezone.utc) for x in ts]
        ax[1].plot(rdt, feats["n_events"], ".", ms=3)
        ax[1].set_ylabel("DAS detections / 30 s record")
        ax[2].plot(rdt, zmax, ".", ms=3)
        ax[2].axhline(a.zthr, color="r", lw=0.8)
        ax[2].set_ylabel("max |robust z|"); ax[2].set_yscale("log")
        fig.suptitle("PoroTomo DASV: pumping, detections, record anomalies")
        fig.tight_layout(); fig.savefig(os.path.join(R, "fig_timeseries.png"), dpi=120)
        if len(mrel):
            fig, ax = plt.subplots(figsize=(6, 4))
            s = np.sort(mrel)[::-1]
            ax.semilogy(s, np.arange(1, len(s) + 1), ".")
            ax.set_xlabel("relative magnitude log10(peak strain rate)"); ax.set_ylabel("N(>=M)")
            ax.set_title(f"DAS detections (b_rel={b_das if b_das is None else round(b_das, 2)})")
            fig.tight_layout(); fig.savefig(os.path.join(R, "fig_mfd.png"), dpi=120)
    except Exception as ex:
        print("figures skipped:", ex)
    print(json.dumps({k: summary[k] for k in ("records", "das_events", "hazard_catalog_based")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
