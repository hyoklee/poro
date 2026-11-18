"""Read-only HDF5 tools for PoroTomo records, each answering in one call.

porotomo_h5_layout: every dataset with shape, dtype, chunks, compression and
    attributes (metadata only). Replaces open / analyze / get_shape / get_dtype /
    list_attributes round trips through the HDF5 MCP server.
porotomo_h5_slice: the values and statistics of a hyperslab. The MCP server's
    hdf5_read_partial_dataset shows only five values of a slice and
    hdf5_aggregate_stats works on whole datasets only.

Both open files read-only, and only under CLIO_ALLOWED_ROOTS.
"""

import os
from pathlib import Path

from clio_agent.sdk import tool

# Internal HDF5 dimension-scale bookkeeping: object references, not readable values.
_SKIP = {"DIMENSION_LIST", "REFERENCE_LIST", "CLASS", "NAME"}
_WIDTH = 80


def _roots() -> list[Path]:
    raw = os.environ.get("CLIO_ALLOWED_ROOTS") or "~/poro:~/cae_test_data"
    return [Path(p).expanduser().resolve() for p in raw.split(":") if p]


def _value(v) -> str:
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    elif hasattr(v, "tolist"):
        v = v.tolist()
        if isinstance(v, list):
            v = [x.decode("utf-8", "replace") if isinstance(x, bytes) else x for x in v]
            if len(v) == 1:
                v = v[0]
    s = str(v)
    return s if len(s) <= _WIDTH else s[: _WIDTH - 3] + "..."


def _attrs(obj) -> str:
    out = []
    for k in obj.attrs:
        if k in _SKIP:
            continue
        try:
            out.append(f"{k}={_value(obj.attrs[k])}")
        except Exception:  # noqa: BLE001 - an unreadable attribute is skipped, not fatal
            out.append(f"{k}=<unreadable>")
    return "; ".join(out)


def _check(path: str):
    """The resolved file path, or an error message."""
    p = Path(path).expanduser().resolve()
    if not any(p == r or r in p.parents for r in _roots()):
        return None, f"{p} is outside the allowed roots: " + ", ".join(map(str, _roots()))
    if not p.is_file():
        return None, f"no such file: {p}"
    return p, ""


@tool(read_only=True, defer=False, callers="direct")
def porotomo_h5_layout(path: str) -> str:
    """Every group and dataset of an HDF5 file in one call, read from the file:
    for each dataset its path, shape, dtype, chunks, compression and attributes;
    then the root attributes. Metadata only, no data values. Authoritative; needs
    no cross-check with other HDF5 tools. `path` is the .h5 file."""
    import h5py  # noqa: PLC0415 - only when the tool runs

    p, err = _check(path)
    if err:
        return err
    lines = [f"file: {p} ({p.stat().st_size:,} bytes)", "datasets (path  shape  dtype  chunks  compression  attributes):"]
    groups = []
    with h5py.File(p, "r", locking=False) as f:
        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                lines.append(
                    f"  /{name}  shape {obj.shape}  {obj.dtype}  chunks {obj.chunks}  "
                    f"compression {obj.compression}  | {_attrs(obj)}"
                )
            else:
                groups.append(f"  /{name}  | {_attrs(obj)}")
        f.visititems(visit)
        if groups:
            lines += ["groups:", *groups]
        lines += ["root attributes:"] + [f"  {a}" for a in _attrs(f).split("; ") if a]
    return "\n".join(lines)


# 1M elements (4 MB of float32) per call: a few seconds of /das, never the whole
# 30000 x 384 record.
MAX_ELEMENTS = 1_000_000
MAX_SHOW = 1000


def _ints(text: str, name: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in str(text).replace("(", "").replace(")", "").split(",") if x.strip())
    except ValueError:
        raise ValueError(f"{name} must be comma-separated integers, got {text!r}") from None


@tool(read_only=True, defer=False, callers="direct")
def porotomo_h5_slice(path: str, dataset: str, start: str, count: str, show: int = 10) -> str:
    """Read a slice of an HDF5 dataset in one call and return its statistics
    (n, NaN count, min, max, mean, std, computed in float64 over the whole slice)
    and its first `show` values in row-major order, at full precision.
    `start` and `count` are comma-separated per dimension, e.g. start "0,200",
    count "100,1" for rows 0-99 of column 200. At most 1,000,000 elements per call;
    `show` at most 1000. Authoritative; needs no cross-check."""
    import h5py  # noqa: PLC0415 - only when the tool runs
    import numpy as np  # noqa: PLC0415

    p, err = _check(path)
    if err:
        return err
    try:
        st, ct = _ints(start, "start"), _ints(count, "count")
    except ValueError as ex:
        return str(ex)
    with h5py.File(p, "r", locking=False) as f:
        if dataset not in f or not isinstance(f[dataset], h5py.Dataset):
            return f"no dataset {dataset!r} in {p}; datasets: " + ", ".join(
                k for k in f if isinstance(f[k], h5py.Dataset))
        d = f[dataset]
        if len(st) != d.ndim or len(ct) != d.ndim:
            return f"{dataset} has {d.ndim} dimensions (shape {d.shape}); give that many start and count values"
        if any(s < 0 or c < 1 or s + c > n for s, c, n in zip(st, ct, d.shape)):
            return f"slice start {st} count {ct} is outside {dataset} shape {d.shape}"
        size = int(np.prod(ct))
        if size > MAX_ELEMENTS:
            return f"slice has {size:,} elements; the limit is {MAX_ELEMENTS:,} per call"
        v = d[tuple(slice(s, s + c) for s, c in zip(st, ct))]
    x = v.astype(np.float64).ravel() if v.dtype.kind in "fiub" else None
    end = tuple(s + c - 1 for s, c in zip(st, ct))
    lines = [f"{p}:{dataset} shape {d.shape} {v.dtype}; slice start {st} count {ct} "
             f"(indices {st} to {end} inclusive), {size} values"]
    if x is not None:
        nan = int(np.isnan(x).sum())
        ok = x[~np.isnan(x)]
        lines.append(f"n {size}, NaN {nan}")
        if ok.size:
            lines.append(f"min {float(ok.min())!r}, max {float(ok.max())!r}, "
                         f"mean {float(ok.mean())!r}, std {float(ok.std())!r}")
    k = max(0, min(int(show), MAX_SHOW, size))
    if k:
        flat = v.ravel()[:k]
        vals = [repr(a.item()) for a in flat]
        lines.append(f"first {k} values: " + ", ".join(vals))
    return "\n".join(lines)
