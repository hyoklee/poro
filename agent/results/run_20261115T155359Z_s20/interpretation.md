> **Reviewer note (2026-11-15):** raw clio-coder output, kept for the record. Three errors: "stride 20" means every 20th record (one per 10 min), not 20 s; the *catalog-based* estimate is the calibrated one, the DAS upper bound is not; and the site Σ (−5.45 to −5.28) is already far *below* the Σ that would give a 1 % chance of Mw ≥ 5.5 over the observed volume (−2.17 to −4.09), so that sentence is backwards. See wiki/agent_induced_seismicity.md.

**Geothermal DAS Anomaly Report**  
*Run ID: `run_20261115T155359Z_s20`*  

---

### 1. What was analysed  

| Item | Value |
|------|-------|
| **Record set** | 759 DAS records (all marked “ok”) |
| **Time span** | 2016‑03‑18 02:09 UTC → 2016‑03‑26 00:59 UTC |
| **Sampling stride** | 20 s (≈ 0.033 fraction of total time) |
| **Mean processing time** | 2.0 × 10³ ms per record |
| **Anomalies flagged** | 57 records (z > 5.0) |
| **Pumping window** | 2016‑03‑11 08:00 UTC → 2016‑03‑27 07:00 UTC (≈ 16 days) |
| **Net injection** | –4.0 × 10⁴ m³ (extraction > injection) |
| **Hourly correlation (Spearman)** | • Events vs net injection: **‑0.17**  <br>• Events vs absolute change in net injection: **‑0.030**  <br>• Events vs injection rate: **‑0.093** |

*Sources:* `summary.json` lines 3‑13, 14‑16, 101‑110, 126‑130.  

---

### 2. Anomalies  

**Common characteristics** (from the top‑10 flagged records, `summary.json` lines 18‑90 and `anomalies.csv` lines 2‑11):  

* **Primary driver:** `max_sta_lta` appears in every top record.  
* **Secondary drivers:** `spectral_centroid_hz` and `n_events` appear in a few (e.g., 2016‑03‑25 00:30 Z, 2016‑03‑21 20:00 Z).  
* **Z‑scores:** range from 15.2 to 30.9, well above the 5‑σ threshold.  

**Relation to pumping changes**  

The hourly Spearman correlations (see above) are all weakly negative (‑0.03 to ‑0.17). This indicates that the anomalous DAS events do **not** strongly track the net injection or its hourly changes during the pumping window. The modest negative values suggest a slight tendency for fewer events when injection is higher, but the effect is minor and not statistically compelling.  

---

### 3. Probability of a Pohang‑like Mw ≥ 5.5 event  

| Model | σ (log‑σ) | *p* (over observed volume) M≥5.5 | *p* (per year at observed rate) M≥5.5 |
|-------|-----------|-----------------------------------|--------------------------------------|
| **Catalog‑based, b = 1.0** | –5.45 | 5.2 × 10⁻⁶ | 1.20 × 10⁻⁴ yr⁻¹ |
| **Catalog‑based, b = 0.73** | –5.32 | 2.16 × 10⁻⁴ | 4.92 × 10⁻³ yr⁻¹ |
| **Catalog‑based, b = 0.65** | –5.28 | 6.48 × 10⁻⁴ | 1.47 × 10⁻² yr⁻¹ |
| **DAS upper‑bound** (b = 0.985) | –2.70 | 2.41 × 10⁻³ | 7.84 × 10⁻² yr⁻¹ |

*Values quoted exactly as in `summary.json` (lines 180‑233, 236‑243, 244‑248).*

**Calibration note:** The DAS‑derived upper bound uses the relative‑magnitude Aki MLE estimate of *b* = 0.985 (line 236) and is therefore the calibrated, data‑driven hazard estimate for this site.

**Recomputed Pohang probabilities** (from `summary.json` lines 268‑272):  

| σ, b | Probability (Mw 5.5) |
|------|----------------------|
| σ = ‑2.0, b = 0.65 | 0.0335 |
| σ = ‑2.0, b = 0.73 | 0.0123 |
| σ = ‑1.0, b = 0.65 | 0.289 |
| σ = ‑1.0, b = 0.73 | 0.116 |

These recomputed values are **higher** than the catalog‑based probabilities, reflecting a more permissive σ assumption.

**σ needed for a 1 % annual chance** (line 274‑277):  

* b = 1.0 → σ = ‑2.17  
* b = 0.73 → σ = ‑3.65  
* b = 0.65 → σ = ‑4.09  

Thus, achieving a 1 % yearly probability of a Mw 5.5 event would require a substantially lower (more negative) σ than observed for the site.

---

### 4. Limitations  

* **Sampling fraction:** Only ~3 % of the total time was recorded (line 11). Rare events could be missed.  
* **Correlation strength:** Spearman coefficients are weak; causality between injection and DAS events cannot be established from this dataset alone.  
* **Hazard model assumptions:** Catalog‑based probabilities rely on a very small local catalog (5 events, line 133‑176) and on assumed *b*‑values; the DAS upper‑bound extrapolates from limited DAS‑derived magnitude estimates.  
* **σ uncertainty:** The σ values span a wide range (‑5.45 to ‑2.70); the choice of σ dramatically changes probability estimates, as shown by the recomputed Pohang values.  
* **Temporal coverage:** The analysis covers only an 8‑day window within a 16‑day pumping period; longer‑term trends are not captured.  

---  

*Prepared for the geothermal operator to inform risk assessment and monitoring strategy.*
