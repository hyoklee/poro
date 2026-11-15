#!/usr/bin/env python3
"""Per-record anomaly detector for PoroTomo DASV HDF5 files (numpy + h5py only).

For one 30 s record (/das: time x channel strain rate, 1 kHz) it:
  1. removes each channel's mean and the common-mode (median over channels)
     signal, which on a single borehole fiber is mostly interrogator noise;
  2. band-passes 10-150 Hz with an FFT mask (microearthquake band);
  3. computes a classic STA/LTA (0.05 s / 2 s) on every channel and takes the
     median over channels, so a trigger needs most of the fiber to light up
     (a coherent arrival, not one noisy channel);
  4. declares an event wherever that median ratio exceeds --thr, merging
     triggers closer than 0.5 s, and records its time, duration, peak ratio,
     peak band-passed amplitude, fraction of channels above threshold and the
     depth of the channel whose peak comes first (a crude proxy for the
     channel nearest the source, not a picked onset).
Record-level features (band RMS, kurtosis, spectral centroid, ...) are also
kept so the aggregator can flag anomalous records by robust z-score.

Output: one JSON object per record on stdout (or appended to --out).
"""
import argparse
import json
import os
import sys
import time

import h5py
import numpy as np


def bandpass(x, fs, lo, hi):
    n = x.shape[0]
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    taper = np.clip((f - lo * 0.8) / (lo * 0.2), 0, 1) * np.clip((hi * 1.2 - f) / (hi * 0.2), 0, 1)
    return np.fft.irfft(X * taper[:, None].astype(np.float32), n=n, axis=0).astype(np.float32)


def moving_mean(e, w):
    c = np.cumsum(e, axis=0, dtype=np.float64)
    out = np.empty_like(c)
    out[:w] = c[:w] / np.arange(1, w + 1)[:, None]
    out[w:] = (c[w:] - c[:-w]) / w
    return out


def analyse(path, thr=3.0, lo=10.0, hi=150.0, sta=0.05, lta=2.0):
    t0 = time.time()
    with h5py.File(path, "r") as h:
        das = h["/das"][...].astype(np.float32)
        tt = h["/t"][...] if "/t" in h else None
        z = h["/z"][...] if "/z" in h else np.arange(das.shape[1], dtype=np.float32)
    nt, nc = das.shape
    fs = 1.0 / np.median(np.diff(tt)) if tt is not None and len(tt) > 1 else 1000.0
    if not np.isfinite(fs) or fs <= 0 or fs > 1e6:
        fs = 1000.0
    read_ms = (time.time() - t0) * 1e3

    das -= das.mean(axis=0, keepdims=True)
    raw_rms = float(np.sqrt(np.mean(das.astype(np.float64) ** 2)))
    das -= np.median(das, axis=1, keepdims=True)
    y = bandpass(das, fs, lo, hi)
    del das

    e = y.astype(np.float64) ** 2
    ns = max(1, int(sta * fs))
    nl = max(ns + 1, int(lta * fs))
    r = moving_mean(e, ns) / (moving_mean(e, nl) + 1e-30)
    r[:nl] = 1.0  # LTA not yet warmed up
    med = np.median(r, axis=1)
    frac = np.mean(r > thr, axis=1)

    trig = med > thr
    events = []
    if trig.any():
        idx = np.flatnonzero(trig)
        gap = int(0.5 * fs)
        starts = [idx[0]]
        ends = []
        for a, b in zip(idx[:-1], idx[1:]):
            if b - a > gap:
                ends.append(a)
                starts.append(b)
        ends.append(idx[-1])
        for s, en in zip(starts, ends):
            w0, w1 = max(0, s - int(0.1 * fs)), min(nt, en + int(0.5 * fs))
            seg = np.abs(y[w0:w1])
            pk_ch = seg.max(axis=0)
            first = int(np.argmin(np.argmax(seg, axis=0)))
            events.append(
                dict(
                    t_s=round(s / fs, 3),
                    dur_s=round((en - s) / fs, 3),
                    peak_ratio=round(float(med[s:en + 1].max()), 3),
                    peak_amp=float(pk_ch.max()),
                    median_ch_amp=float(np.median(pk_ch)),
                    frac_channels=round(float(frac[s:en + 1].max()), 3),
                    first_depth=float(z[first]),
                )
            )

    yb = y.astype(np.float64)
    band_rms = float(np.sqrt(np.mean(yb ** 2)))
    ch_rms = np.sqrt(np.mean(yb ** 2, axis=0))
    k = float(np.mean((yb / (yb.std() + 1e-30)) ** 4))
    spec = np.abs(np.fft.rfft(yb[:, :: max(1, nc // 32)], axis=0)).mean(axis=1)
    f = np.fft.rfftfreq(nt, 1.0 / fs)
    centroid = float((f * spec).sum() / (spec.sum() + 1e-30))
    return dict(
        nt=nt, nc=nc, fs=fs,
        raw_rms=raw_rms, band_rms=band_rms,
        ch_rms_p95_over_p50=float(np.percentile(ch_rms, 95) / (np.median(ch_rms) + 1e-30)),
        kurtosis=k, spectral_centroid_hz=centroid,
        max_sta_lta_median=float(med.max()),
        n_events=len(events), events=events,
        read_ms=round(read_ms, 1), total_ms=round((time.time() - t0) * 1e3, 1),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("h5")
    ap.add_argument("--key", default=None, help="S3 key recorded in the output")
    ap.add_argument("--thr", type=float, default=3.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    name = os.path.basename(a.key or a.h5)
    stamp = name.rsplit("_", 1)[-1].split(".")[0]  # yymmddHHMMSS
    rec = dict(key=a.key or a.h5, start=f"20{stamp[0:2]}-{stamp[2:4]}-{stamp[4:6]}T{stamp[6:8]}:{stamp[8:10]}:{stamp[10:12]}Z")
    try:
        rec.update(analyse(a.h5, thr=a.thr))
        rec["status"] = "ok"
    except Exception as ex:  # keep the record so failures are counted
        rec.update(status="error", error=f"{type(ex).__name__}: {ex}")
    line = json.dumps(rec)
    if a.out:
        with open(a.out, "a") as f:
            f.write(line + "\n")
    else:
        print(line)
    return 0 if rec["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
