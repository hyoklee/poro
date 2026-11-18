"""porotomo_h5_layout: the whole layout of an HDF5 record in one read-only call.

Replaces open / analyze / get_shape / get_dtype / list_attributes round trips
through the HDF5 MCP server for the common question "what is in this file".
Reads metadata only (no dataset values), and only under CLIO_ALLOWED_ROOTS.
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


@tool(read_only=True, defer=False, callers="direct")
def porotomo_h5_layout(path: str) -> str:
    """Every group and dataset of an HDF5 file in one call, read from the file:
    for each dataset its path, shape, dtype, chunks, compression and attributes;
    then the root attributes. Metadata only, no data values. Authoritative; needs
    no cross-check with other HDF5 tools. `path` is the .h5 file."""
    import h5py  # noqa: PLC0415 - only when the tool runs

    p = Path(path).expanduser().resolve()
    if not any(p == r or r in p.parents for r in _roots()):
        return f"{p} is outside the allowed roots: " + ", ".join(map(str, _roots()))
    if not p.is_file():
        return f"no such file: {p}"
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
