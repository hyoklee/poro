# Concept: seismogenic index (Σ)

## Definition

The seismogenic index is a site constant that measures how much seismicity a reservoir produces per unit of injected fluid (Shapiro and co-workers). With cumulative injected volume V (m³) and Gutenberg–Richter slope b:

    log10 N(≥M) = Σ + log10 V − b·M

The probability of at least one event of magnitude M or larger after injecting V is (Shapiro, Kim & Ree 2021, Eq. 5):

    P(≥M | V) = 1 − exp(−V · 10^(Σ − b·M))

A higher Σ means more seismically reactive rock. Their real-time worst-case version uses the running maximum of Σ and the running minimum of b.

## Values in this wiki

| Site | Σ | b | Source |
|---|---|---|---|
| Pohang EGS (2016–17) | about −2 to −1 | 0.65 or 0.73 | [source-shapiro-2021-pohang.md](source-shapiro-2021-pohang.md) |
| Brady, March 2016 (catalogue, b scenarios) | −5.45 (b=1), −5.32 (b=0.73), −5.28 (b=0.65) | assumed | [agent_induced_seismicity.md](agent_induced_seismicity.md) |
| Brady, DAS upper bound (uncalibrated) | −2.70 | 0.98 (relative) | [agent_induced_seismicity.md](agent_induced_seismicity.md) |

## Caveats

The model is driven by injected volume. At a balanced or net-producing hydrothermal field such as Brady, seismicity correlates with pumping *stops* rather than with volume, so Σ there describes an average rate, not a mechanism. The b-value controls the extrapolation to large magnitudes. Westaway (2021, Geothermics) argues Pohang's true b is about 1.12, which would make the Mw 5.5 probability much lower than Shapiro et al. claim.

## Related

- [concept-induced-seismicity-pohang.md](concept-induced-seismicity-pohang.md)
- [concept-poroelastic-tomography.md](concept-poroelastic-tomography.md)
