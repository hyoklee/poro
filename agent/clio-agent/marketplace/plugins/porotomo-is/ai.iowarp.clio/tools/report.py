"""porotomo_report: the headline numbers of a PoroTomo run, without the shell.

The digest itself is agent/report.py in the poro repo (POROTOMO_ROOT, default
~/poro), loaded from there so the tool and the script never drift apart. The
tool only reads <results>/run_*/summary.json.
"""

import importlib.util
import os
from pathlib import Path

from clio_agent.sdk import tool


def _root() -> Path:
    return Path(os.environ.get("POROTOMO_ROOT", "~/poro")).expanduser()


def _digest():
    spec = importlib.util.spec_from_file_location("porotomo_report_py", _root() / "agent" / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.report


# Offered up front (not via search_tools) and called directly, not from run_code.
@tool(read_only=True, defer=False, callers="direct")
def porotomo_report(run: str = "") -> str:
    """Headline numbers of a PoroTomo run, read from its summary.json: records,
    anomalies, DAS detections, pumping, catalogue, Sigma and P(M>=5.5) per b
    value, and the DAS upper bound. Authoritative; needs no cross-check.
    `run` is a run name such as run_20261115T155359Z_s20 or its path; empty means
    the latest run."""
    results = (_root() / "agent" / "results").resolve()
    runs = sorted(p for p in results.glob("run_*") if (p / "summary.json").is_file())
    if not runs:
        return f"no finished runs in {results}"
    if not run:
        target = runs[-1]
    else:
        target = (results / Path(run).name).resolve()
        if target not in runs:
            return f"no finished run {run!r}; finished runs: " + ", ".join(p.name for p in runs)
    return _digest()(target)
