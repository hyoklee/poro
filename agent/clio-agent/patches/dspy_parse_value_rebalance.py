"""Local patch for dspy.adapters.utils.parse_value (dspy 3.3.0b1, clio-agent 0.9.4.24).

parse_value() sends every field through json_repair.loads first. When a model's
tool-call JSON lacks one closing brace, json_repair 0.63.5 re-splits string
values at ", " and ":" (clio-agent #2369), which truncates the agent's answer.

This block, inserted before the json_repair call, tries a strict json.loads,
then a structural rebalance (insert missing } / ] outside string literals) and
a strict parse again; only then does the original json_repair path run.
"""

import json as _clio_json
import logging as _clio_logging

_clio_log = _clio_logging.getLogger("clio_local_patch")


def _clio_rebalance(s: str):
    pairs = {"{": "}", "[": "]"}
    out, stack, in_str, esc = [], [], False, False
    for i, ch in enumerate(s):
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in pairs:
            stack.append(pairs[ch])
        elif ch in "}]":
            if ch not in stack:
                # Extra closers after the top-level value is already closed
                # (e.g. "}]}}" where "}" belongs before "]"): drop the tail.
                if not stack and s[i:].strip(" \t\r\n}]") == "":
                    break
                return None  # any other extra closer: leave it to json_repair
            while stack[-1] != ch:
                out.append(stack.pop())
            stack.pop()
        out.append(ch)
    if in_str:
        return None
    out.extend(reversed(stack))
    return "".join(out)


def _clio_strict_or_rebalanced(value: str):
    try:
        return True, _clio_json.loads(value)
    except Exception:
        pass
    fixed = _clio_rebalance(value)
    if fixed is not None and fixed != value:
        try:
            obj = _clio_json.loads(fixed)
        except Exception:
            return False, None
        _clio_log.warning("CLIO-LOCAL-PATCH rebalanced JSON field (length change %+d)", len(fixed) - len(value))
        return True, obj
    return False, None
