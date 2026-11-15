# Source: Brady well pumping during the PoroTomo deployment (GDR 917)

"Corrected Deployment Data.csv" from GDR submission 917 (https://gdr.openei.org/submissions/917). It corrects GDR 844/845 (DOI 10.15121/1334283) and adds wells missing from the original. Fetched 2026-11-15 to `agent/sources/brady_pumping_corrected_gdr917.csv` (1,733,526 B, CR line endings).

## Layout

One row per minute, 2016-03-11 08:00 to 2016-03-27 07:00 UTC (23,042 rows, 15.96 days). Columns:
- `Full UTC Date Time` (`m/d/yy H:MM`) and `ms`.
- Extraction flow in gpm for wells 48A-1, 47C-1, 18-1, 27-1, 82A-11.
- Injection flow in gpm for wells 18D-31, 18B-31, 81A-1, 73-25.
- Downhole pressure in PSI for 82A-11, 27-1, 18-1, 48A-1, 47C-1.

## Derived (agent run 2026-11-15)

- Injection stopped 2016-03-13 21:17 and restarted 2016-03-18 12:12. It stopped again 2016-03-25 19:13 and restarted 2016-03-26 00:28 (injection under 100 gpm).
- Totals: injected 465,448 m³, extracted 505,933 m³, net −40,485 m³. Mean flows 5,336 gpm in and 5,800 gpm out.

## Used by

- [agent_induced_seismicity.md](agent_induced_seismicity.md)
