#!/usr/bin/env python3
"""Apply (or --revert) the local DSPy parse_value patch for clio-agent #2369.

    ~/.local/share/clio/clio-agent/.venv/bin/python apply_dspy_patch.py [--revert]

Backs up dspy/adapters/utils.py to utils.py.orig-clio-patch on first use, then
inserts dspy_parse_value_rebalance.py ahead of the json_repair call. A clio-agent
reinstall or upgrade replaces the venv and drops the patch; rerun this then.
Restart the clio-agent server afterwards.
"""
import pathlib
import shutil
import sys

import dspy.adapters.utils as target

u = pathlib.Path(target.__file__)
orig = u.with_name(u.name + ".orig-clio-patch")
if "--revert" in sys.argv:
    if orig.exists():
        shutil.copy2(orig, u)
        print(f"reverted {u}")
    else:
        print("no backup; nothing to revert")
    sys.exit(0)
if not orig.exists():
    shutil.copy2(u, orig)
t = orig.read_text()
call = '    candidate = json_repair.loads(value)  # json_repair.loads returns "" on failure.\n'
if t.count(call) != 1:
    sys.exit("unexpected dspy/adapters/utils.py (version changed?); patch not applied")
helper = pathlib.Path(__file__).with_name("dspy_parse_value_rebalance.py").read_text()
t = t.replace(call, '    _clio_ok, candidate = _clio_strict_or_rebalanced(value)  # clio local patch (#2369)\n'
              '    if not _clio_ok:\n' + "    " + call)
t += ("\n\n# ---- clio local patch (clio-agent #2369), from poro/agent/clio-agent/patches ----\n"
      + helper.split('"""', 2)[2])
u.write_text(t)
print(f"patched {u}")
