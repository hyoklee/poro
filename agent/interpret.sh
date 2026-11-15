#!/bin/bash
# LLM interpretation of one run with clio-coder (headless, ALCF Metis target).
# Writes <run>/interpretation.md. Usage: agent/interpret.sh <run_dir>
set -eu
RUN=$(cd "$1" && pwd)
cd "$(dirname "$0")/.."
clio-coder run "Read $RUN/summary.json and the first 30 lines of $RUN/anomalies.csv. \
Do not modify any files. Write a markdown report for a geothermal operator with sections: \
(1) What was analysed (records, time span, sampling). (2) Anomalies: what the flagged records \
have in common and whether they line up with pumping changes, using correlations_hourly. \
(3) Probability of a Pohang-like Mw>=5.5 event: quote hazard_catalog_based for b=1.0, 0.73 and 0.65 \
and hazard_das_upper_bound, and say which is calibrated. Compare with the recomputed Pohang values in pohang.p_mw55_recomputed \
and with pohang.sigma_needed_at_brady_for_1pct_mw55_over_observed_volume. \
(4) Limitations. Quote numbers exactly as they appear in the JSON, with 2 significant figures; never invent numbers." \
  | sed '1{/^clio-coder run: session/d}' > "$RUN/interpretation.md"
echo "wrote $RUN/interpretation.md ($(wc -l < "$RUN/interpretation.md") lines)"
