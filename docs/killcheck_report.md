# Kill check: heat-death recording in India (2026-11-12)

**Verdict: PASS. Reframe from "reconciling three sources" to "exposure-adjusted ascertainment of heat-stroke deaths by state".**

## Data built for this check (shared panel)

`shared_adsi_panel/` extracts the NCRB ADSI 2014–2024 state × sex × cause tables:

- forces of nature: Table 1.8 for 2014–19, Table 1.9 for 2020–24;
- other causes: Table 1.9 for 2014–19, Table 1.10 for 2020–24, covering cases, injured and died.

The result is 77 harmonised causes × 35 constant-geography units × 11 years.

**Checks**
- Every page passes: states sum to TOTAL (STATES), UTs to TOTAL (UTs), and both to All-India.
- Every cause-year reproduces the printed All-India deaths exactly.

**Published defects (logged, not fatal)**
- 2020 Suffocation page: 5 rows where the sex split does not sum to the total, and the died-male column is corrupt.
- Forces of nature: 1-death differences against the total page in 2014 (Uttar Pradesh) and 2023 (UT total).
- 2024 prints an all-zero legacy "Railway Accidents" page next to its replacement.
- 2014–15 use a shorter list of other causes.

## Findings

1. **The signal is valid.** In a Poisson model with state and year fixed effects across 15 states, each extra Mar–Jun day with Tmax ≥40 °C (population-weighted IMD grid) raises recorded heat-stroke deaths by 2.7% (RR 1.027, 95% CI 1.014–1.040). That is about +31% per within-state SD (10 days). Tmax anomaly gives RR 1.21 per °C (1.05–1.39).
2. **Recording varies roughly 100-fold between states at the same heat.**

   | State | Days ≥40 °C per season | Recorded deaths 2014–24 |
   |---|---|---|
   | Madhya Pradesh | 46 | 254 |
   | Rajasthan | 43 | 383 |
   | Delhi | 37 | 12 |
   | Andhra Pradesh | 11 | 1,888 |
   | Odisha | 10 | 720 |
   | Bihar | 12 | 1,418 |

   Exposure does not explain this.
3. **Recording changes over time, beyond exposure.**
   - The 2014–23 model predicts 600 deaths for 2024; 1,824 were observed.
   - 2022 (30 hot days) recorded 724 deaths against 1,323 in 2016 (31 hot days).
   - The 2020–21 lows coincide with COVID.

   Before any claim, test hot nights (Tmin) and heat duration (the 2024 heatwave was long, with warm nights).
4. **No peer-reviewed pre-emption.** PubMed has only descriptive NCRB tabulations (Kumar & Singh, J Therm Biol 2021;95:102792) and a BMJ news feature (Chakraborty, BMJ 2024;386:q1437). The three-source disagreement (NCRB 8,171 / NCDC 3,812 / IMD 3,436, 2015–22) is widely reported in the press but has not been modelled.

## Proposed paper

**Working title:** *How many heat deaths does India record? Exposure-adjusted ascertainment of heat-stroke deaths across states, 2014–2024.*

**Model.** A Bayesian hierarchical Poisson model:

  deaths[s,t] ~ Poisson(pop[s,t] × exp(α_s + β·heat[s,t] + γ_t))

- exp(α_s − mean α) is the relative recording sensitivity of each state.
- γ_t is a national recording drift.
- β is shared, with sensitivity analyses that let β vary with outdoor-worker share (PLFS, on disk) and with age ≥60 share.

**Benchmarks**
- Heat-attributable mortality from the Million Death Study case-crossover (Fu et al., PLoS Med 2018). It is a coarse absolute anchor and should be labelled as such.
- NCDC/IHIP and IMD state-year counts, if obtainable (see below).

**Outputs**
- Each state's position on recorded versus expected heat deaths.
- Recording drift, including 2024.
- What recorded counts imply for Heat Action Plan evaluation: a falling count can mean worse recording, not fewer deaths.

**Policy hooks (verify each from primary documents before writing; † = unverified)**
- National Programme on Climate Change and Human Health heat-related illness and death surveillance (IHIP)†.
- NDMA heatwave guidelines and state Heat Action Plans†.
- State notification of heatwave as a state-specific disaster for SDRF ex-gratia: a candidate explanation for high recording in AP, Telangana and Odisha†.
- Whether the 16th Finance Commission added heatwave to the notified disasters†.

## Data still needed (user action; sites return 403 or are unreachable from the agent)

- Rajya Sabha unstarred question 1693, 6 Aug 2024 (MoHFW): annexure of National Heat-Related Illness and Death Surveillance cases and deaths by state, 2021 to Jul 2024.
- Lok Sabha AU232 / AU418, 24 Jul 2024, and MoES 4381 (2025): state-wise heat deaths (IMD/NCRB, 2013–2022).

These strengthen the paper but are not required: the core analysis runs on data already on disk.

## Next kill-level test before writing

- Add hot nights and heatwave duration, and use IMD heatwave-day definitions (Tmax ≥40 °C and departure ≥4.5 °C) in place of ≥40 °C days.
- If 2024 is still under-predicted more than 2-fold, recording drift is real.
- If the state recording index survives adjustment for age and outdoor work, proceed.

Script: `src/00_kill_check.py`.

## Update (2026-11-12): NCDC surveillance (Rajya Sabha USQ 1693, 6 Aug 2024)

**Data.** The annexure gives **national totals only**: no state breakdown, and only for 2021 to 28 Jul 2024. Values are saved in `data/ncdc_hri_national_2021_2024.csv`. ADSI figures are calendar-year deaths from our panel.

| Year | NCDC suspected cases | NCDC confirmed deaths | ADSI (police) deaths | Confirmed / ADSI |
|---|---|---|---|---|
| 2022 | 4,481 | 33 | 730 | 4.5% |
| 2023 | 19,402 | 189 | 804 | 23.5% |
| 2024* | 48,385 | 185 | 1,832 | 10.1% |

\*NCDC 2024 runs only to 28 Jul.

**Interpretation**
- Suspected cases rose about tenfold in two years, consistent with the surveillance system still being rolled out.
- Confirmed deaths stayed flat from 2023 to 2024 (189 → 185), while police-recorded deaths more than doubled (804 → 1,832). That fits recording drift in the police series: by NCDC's standard, the 2024 rise is not seen.
- The comparison is confounded by NCDC's strict confirmation rule (core temperature ≥40.6 °C before death) and by its partial 2024 window.
- Use this only as supporting evidence at national level. It cannot be used for state-level reconciliation.

**Annexure II (FY 2024-25 programme funds by state)** could serve as an exploratory covariate for "surveillance investment".

**Lok Sabha AU232/AU418.** The debates PDF of 24.07.2024 carries only links to written answers, so the state tables still need the answer PDFs themselves.

## Update (2026-11-12): kill-level test 2 — better exposures (`src/01_build_heat_exposures.py`, `src/02_exposure_test.py`)

**Exposures built.** From IMD gridded daily Tmax/Tmin (1°, 1991–2024) I computed population-weighted Mar–Jun state-year metrics:
- IMD heat-wave days: Tmax ≥40 °C and ≥4.5 °C above the 1991–2020 day-of-year normal, or ≥45 °C;
- severe heat-wave days;
- heat-wave days within runs of 2 or more;
- IMD warm nights;
- nights with Tmin ≥28 °C;
- degree-days above 40 °C.

On every metric, 2024 is the most extreme or near-most extreme season of 2014–24. Hot nights reached a record 12.7 per season across the 15 units.

**(a) Within-state signal.** Poisson model with state and year fixed effects, 15 units, 11,987 deaths. RR per within-state SD (95% CI):

| Exposure | RR per within-state SD | ΔAIC vs fixed effects only |
|---|---|---|
| Degree-days >40 °C | 1.30 (1.17–1.43) | −352 |
| Days ≥40 °C | 1.31 (1.15–1.49) | −327 |
| Hot nights ≥28 °C | 1.20 (1.09–1.31) | −223 |
| IMD heat-wave days | 1.15 (1.05–1.25) | −187 |

- Best combined model: degree-days + hot nights, ΔAIC −365.
- IMD warm nights add nothing (RR 1.01).

The signal holds under every definition, which strengthens the "valid but under-ascertained" premise.

**(b) The 2024 jump.** Fit with state FE + trend + exposure on 2014–23 and predict 2024 (observed 1,824):

| Exposure | obs/pred (fit 2014–23) | obs/pred (excluding 2020–21) |
|---|---|---|
| None | 3.49 | 2.61 |
| Days ≥40 °C | 3.04 | 2.63 |
| Degree-days + hot nights (best) | 2.54 | 2.37 |
| Heat-wave days + hot nights | 2.45 | 2.30 |

The pre-specified rule (still >2× under the best exposure) is **met**. Better exposure measurement closes only about a quarter of the gap.

**Calibration (leave-one-year-out; `outputs/loyo_calibration.csv`).** The same model predicts each held-out year from the other non-COVID years. Obs/pred, degree-days + hot nights:

| Year | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| obs/pred | 0.94 | **1.69** | 0.93 | 0.92 | 0.75 | 0.68 | 0.60 | 0.51 | **0.59** | 0.90 | **2.37** |

2024 is the largest miss in 11 years, under all three exposure sets. But it is not alone:
- 2015 (the Andhra Pradesh / Telangana heatwave) ran 1.7–2.0×;
- 2022 ran about 0.6× despite near-record heat.

**Where the 2024 excess sits.** It is concentrated in the eastern Indo-Gangetic plain:

| Unit | obs/pred 2024 |
|---|---|
| Bihar | 5.4 (422 vs 79) |
| Jharkhand | 3.4 |
| Odisha | 3.3 |
| Punjab | 3.2 |
| Uttar Pradesh | 2.3 |
| Andhra Pradesh | 0.36 (50 vs 137) |

Andhra Pradesh was the historic top recorder.

**Verdict: PASS, with reframing.** The national recording effect is not a smooth drift. It behaves as **year- and region-specific recording shocks**:
- the 2015 surge in AP/Telangana;
- the 2022 deficit;
- the 2024 surge in the eastern Indo-Gangetic plain.

All three are large relative to the heat signal. This sharpens the policy message: year-on-year changes in NCRB heat deaths cannot be used to evaluate Heat Action Plans. A 0.6× to 2.4× swing in recording, at fixed exposure, swamps any plausible programme effect.

**Model implications**
- γ_t should be modelled as exchangeable year effects with a reported variance, not as a trend.
- State-by-period interactions, or a random walk in α_s, should test whether the recording leader rotates between states.

**Caveats**
- *Possible non-linear dose-response.* A 1° grid smooths extremes, and the 2024 eastern-plain heat may have been deadlier per degree than the model allows. Two pieces of evidence argue against heat alone:
  - NCDC confirmed deaths were flat from 2023 to 2024 (189 → 185);
  - AP fell below prediction in the same season.

  Test with a spline or threshold in degree-days before writing.
- *Selected sample.* The 15-unit sample was chosen on the outcome (≥20 deaths). The Bayesian model should use all 35 units.

**Next gate.** The state recording index α_s must survive a population offset plus age ≥60 share and outdoor-work share (PLFS). Then add a dose-response spline check.

## Update (2026-11-12): gate 3 — state index vs population, age, outdoor work; dose-response (`src/03_plfs_covariates.py`, `src/04_state_index.py`)

**Covariates.** From PLFS unit-level data, 2017-18 to CY2024, I computed weighted state shares of persons aged ≥60, of outdoor workers (usual-status work in agriculture, mining or construction) and of casual labourers. Only aggregates are written. The loaders and the 35-unit map come from the occupation-suicide project. Populations are Technical Group projections.

**Andaman & Nicobar.** It lies outside the IMD land grid. Its exposure was silently zero (missing flags were counted as "no heat days") until a mask fixed it, and `pivot_table` then silently dropped the rows. It is now kept as explicit missing and dropped visibly (0 deaths).

**Recording index.** Observed ÷ expected heat-stroke deaths, 2014–24, where expected is population × heat dose-response × year effects, rescaled to the national total.

**Pre-specified rule:** among units with ≥50 deaths, the index survives if, after adjustment, the max/min ratio is ≥10 and SD(log index) is ≥50% of its unadjusted value.

| Index | max/min | SD(log index) | Result |
|---|---|---|---|
| I0: heat effect estimated within state | 27.2 (AP 5.3 vs MP 0.20) | 1.08 | — |
| I1: + age ≥60 + outdoor share, fitted between states (deliberately generous to confounding) | 16.4 (Punjab 4.5 vs MP 0.28) | 0.97 (90%) | PASS |
| I2: relative heat (IMD heat-wave days + departure) + covariates (acclimatisation sensitivity) | 13.9 (Telangana 4.2 vs MP 0.30) | 0.93 (86%) | PASS |

**GATE 3: PASS.**
- The age and outdoor-work coefficients are unidentifiable between states (95% CIs span about 10⁻⁴ to 10⁴). Demographic structure explains almost none of the gap.
- Madhya Pradesh has the second-highest outdoor share and the lowest index of any large state.

**Strongest contrast for the paper: neighbours with the same dry heat.**

| State | Recording index (I1) | Mean degree-days >40 °C |
|---|---|---|
| Punjab | 4.53 | 40 |
| Haryana | 2.17 | 71 |
| Rajasthan | 0.41 | 94 |
| Madhya Pradesh | 0.28 | 94 |
| Delhi | 0.07 | 79 |

That is a roughly 60-fold spread across contiguous north-west India in a single hot, dry climate zone.

**Dose-response check (2024).** Natural splines in degree-days and hot nights, plus a degree-days × hot-nights interaction, improve fit (ΔAIC up to −202). They leave 2024 at 2.2–2.4× its prediction, so non-linearity does not explain the 2024 surge.

**Remaining main threat: humidity.** IMD gridded data has no humidity. Coastal or humid high-index states (Andhra Pradesh, Odisha) could carry humid-heat mortality that dry-bulb Tmax misses. Two things argue against humidity as the main explanation:
- dry inland Punjab and Telangana are among the highest;
- humid West Bengal (0.44) and coastal Gujarat (0.44) are low.

Even so, test it before writing. Options:
- daily T2M/RH2M or wet-bulb from NASA POWER (free API, no login), sampled at district population centroids and fed into the same model;
- ERA5 (needs a CDS account, user action).

**Next.**
1. Humidity / wet-bulb test (gate 4).
2. Main model: Bayesian hierarchical Poisson–lognormal with partial pooling of α_s (35 units, including zero-count units), exchangeable γ_t, and state × period terms for rotating recording leaders.
3. Benchmark against the MDS-based expected heat mortality.

## Update (2026-11-12): gate 4 — humid heat (`src/05_fetch_power.py`, `src/06_humidity_gate.py`)

**Data.** NASA POWER daily point data (MERRA-2, 0.5° × 0.625°): 674 district representative points mapped to 546 grid cells, 2014–24, no fetch failures.

**Exposure.** Afternoon wet bulb, Stull (2011), at Tmax with RH derived from specific humidity and surface pressure. Season metrics:
- days with Tw ≥26 and ≥28 °C;
- degree-days above Tw 26 °C;
- mean Tw.

All are population-weighted to states.

**Sanity check.** POWER vs IMD season-mean Tmax: r = 0.87 (within-state r = 0.91), bias −0.6 °C.

**Results**
- **No within-state wet-bulb signal.**
  - Alone: RR per within-SD 0.82–1.06.
  - Added to dry heat: 0.88–1.09, all CIs spanning 1.
  - Dry heat fits far better than wet bulb alone: wet-bulb-only models have ΔAIC +68 to +333.
- **Rule (pre-specified): PASS** for all three index variants.

  | Variant | SD(log index) kept | AP/MP | Punjab/MP |
  |---|---|---|---|
  | W0 (within) | 106% | 48× | 19× |
  | W1 (between + covariates) | 92% | 14× | 17× |
  | W2 (wet only) | 89% | 12× | 18× |

  - Humid West Bengal stays low (0.35–0.44 between states).
  - Odisha and AP rise when the within-state model is used, because their wet-bulb slope is ≤1.
- **2024.** It had record wet-bulb exposure (mean Tw ≥28 days 7.5 vs 3.7). Yet adding wet bulb leaves 2024 at 2.3–2.8× its prediction.

**GATE 4: PASS.** Humid heat explains neither the state gap nor 2024. The main model uses dry heat (degree-days >40 °C + hot nights ≥28 °C).

**Caveat.** MERRA-2 humidity is coarse. A within-state null may partly reflect measurement error, so the paper should state it as "no evidence that", not "humidity is irrelevant".

**Policy and compensation evidence.** Collected in `docs/policy_sources.md`; all items secondary, primary G.O.s still to obtain.
- National notification of heatwave and lightning for 2026–31.
- AP Apathbandhu sunstroke ex-gratia since 2011.
- Odisha SDRF ₹50,000.
- Telangana and Tamil Nadu notifications in 2024–25.
- Punjab, the top recorder, has no scheme found, so compensation is at most a partial explanation.

## Main model (2026-11-12): Bayesian hierarchical Poisson–lognormal (`src/07_bayes_model.py`, NumPyro NUTS)

**Model.** 34 units × 11 years (A&N dropped: no grid, 0 deaths). Exposures: degree-days >40 °C and hot nights ≥28 °C.

**Structure**
- Mundlak state-mean exposures in α_s;
- age ≥60 and outdoor share in α_s;
- state × period δ for 2014–17, 2018–21, 2022–24;
- exchangeable sum-to-zero γ_t;
- observation-level overdispersion.

**Sampling.** 4 chains × 1,500 draws after 1,500 warmup. Max r̂ 1.002, min n_eff 1,004, 0 divergences.

**Predictive checks (mixed replication).**
- Every observed year total lies inside its 95% predictive interval.
- Zero unit-years: observed 0.481 vs replicated 0.452 (0.420–0.484), at the upper edge.
- Largest unit-year: observed 654 vs replicated 572 (350–1,200).

**Parameters (log scale)**

| Parameter | Mean | 90% CrI | Reading |
|---|---|---|---|
| β degree-days, per SD (33.5) | 0.24 | 0.08–0.40 | RR 1.27 |
| β hot nights, per SD (5.9) | 0.15 | 0.01–0.29 | RR 1.16 |
| θ outdoor share, per SD | +0.73 | 0.07–1.39 | — |
| θ age ≥60, per SD | 0.16 | −0.46 to 0.80 | — |
| σ_α (between-state recording) | 2.12 | 1.55–2.67 | dominant |
| σ_δ (state × period rotation) | 0.33 | 0.20–0.47 | — |
| σ_γ (year shocks) | 0.40 | 0.19–0.56 | — |
| σ_ε | 0.46 | — | — |

Between-state recording dominates. Rotation and year shocks are real but about one-sixth as large on the log scale.

**State recording index** (relative to the mean of 14 states with ≥50 deaths; posterior median and 95% CrI)

| State | Index | 95% CrI |
|---|---|---|
| Punjab | 4.88 | 3.00–7.84 |
| Telangana | 3.42 | 2.15–5.50 |
| Andhra Pradesh | 3.11 | 1.87–5.14 |
| Jharkhand | 2.53 | — |
| Odisha | 2.22 | — |
| Bihar | 1.54 | — |
| Haryana | 1.48 | — |
| Maharashtra | 0.93 | — |
| Uttar Pradesh | 0.63 | — |
| West Bengal | 0.43 | — |
| Gujarat | 0.37 | — |
| Chhattisgarh | 0.32 | — |
| Rajasthan | 0.24 | 0.14–0.41 |
| Madhya Pradesh | 0.21 | 0.12–0.37 |

- Delhi 0.031 (0.013–0.070); Tamil Nadu 0.012.
- P(Punjab in top 3) = 0.985.

**Residual index (net of the age and outdoor terms).** The gap widens, e.g. Punjab 9.1 (3.4–26), Haryana 3.5, Madhya Pradesh 0.11 (0.04–0.32). Outdoor share predicts more recorded deaths, and the top recorders have low outdoor shares, so work structure cannot explain the gap.

**Rotation (2022–24 vs 2014–17)**

| State | Change | P(decline) |
|---|---|---|
| Andhra Pradesh | ×0.38 (5.46 → 2.10) | 0.998 |
| Gujarat | ×0.56 | 0.97 |
| West Bengal | ×0.64 | 0.93 |
| Rajasthan | ×0.64 | 0.93 |
| Chhattisgarh | ×2.15 | 0.014 |
| Bihar | ×1.50 | 0.067 |
| Punjab | ×1.40 | 0.11 |

**Year recording shocks (RR, 95% CrI)**

| Year | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RR | 1.47 (1.15–1.90) | 1.27 | 1.35 | 1.07 | 0.99 | 1.21 | 0.67 | 0.54 (0.39–0.76) | 0.74 (0.56–0.95) | 0.88 | 1.32 (1.01–1.75) |

At fixed heat, recording fell by about half from 2014–16 to 2020–22, then recovered in 2024.

**Headline for the paper.** At the same heat and population, the top state records about 24× more heat-stroke deaths than the bottom (Punjab vs Madhya Pradesh). Whole regions record almost none:
- the north-east, Kerala and Tamil Nadu;
- Delhi, at 0.03.

Recording also swings about 2.7-fold over time nationally and shifts within states (Andhra Pradesh −62%). National notification of heatwave as a disaster for 2026–31 ties ex-gratia to certification. These indices are the pre-notification baseline against which any post-2026 rise must be read.

**Remaining before drafting**
1. Absolute anchor. Literature-based expected heat mortality, e.g. the Million Death Study case-crossover or GBD high-temperature deaths for India, to state what fraction recorded deaths represent. Label it coarse.
2. Primary G.O.s or answers for the policy items (`docs/policy_sources.md`).
3. Sensitivity runs:
   - Poisson-gamma instead of lognormal;
   - excluding 2020–21;
   - IMD heat-wave-day exposure instead of degree-days.
4. Figures:
   - forest plot of the index;
   - map;
   - year shocks;
   - AP/Chhattisgarh rotation.

## Absolute anchor (coarse): Million Death Study

**Source.** Fu SH, Gasparrini A, Rodriguez PS, Jha P. *PLoS Med* 2018;15(7):e1002619, doi:10.1371/journal.pmed.1002619 (PMID 30040816). Table 2, read from PMC6057641.

**Method of the source.** A case-crossover design on 411,613 Million Death Study deaths, 2001–13, applied to UN 2015 death estimates.

**Its estimates (2015, deaths attributable to heat)**
- Extremely hot days (34.2–39.7 °C): 25,100 (95% CI 15,400–33,200), statistically significant.
- Moderately hot days: 63,600 (−13,600 to 129,000), not significant.
- Hot temperatures overall: 0.5% (0.1–0.9) of medical deaths.

**Comparison**
- NCRB 2015 (1,908) is about 7.6% (5.7–12.4%) of the extreme-heat figure.
- The NCRB 2014–24 mean (1,096 a year) is about 4.4% (3.3–7.1%).
- Against all hot-temperature deaths (88,700), NCRB 2015 is 2.2%.

**Framing (must hold in the paper).** These are different constructs:
- the Million Death Study counts excess deaths from all medical causes, mostly cardiovascular and cerebrovascular;
- ADSI counts deaths that police classify as heat or sunstroke.

So the ratio is the share of heat's mortality burden visible in the official injury statistics, not the completeness of heatstroke recording. It is national, not state-level, and pre-dates 2024. Use it only as context for the relative indices, never to "correct" state counts.

## Correction (2026-11-13): district geography defect found while drawing the map; full pipeline rerun

`districts_v2.geojson` is versioned, and the 2011 subset used by the exposure builders had three defects:
1. **Holes** where post-2011 districts were carved out: 22 holes, 2.3% of India's area; Chhattisgarh 22.7%, Assam 11.5%.
2. **Outline polygons:** 18 unnamed whole-state outlines, each weighted as a district with the median population.
3. **Telangana weights:** the 10 Telangana districts matched by name carried pre-split populations on post-split boundaries.

**Fix** (`src/geography.py`, now shared by 01, 05 and 08):
- holes returned to the 2011 district with the longest shared border;
- outlines dropped;
- Telangana weighted by area share of its 2011 population, with Hyderabad on its Census count;
- Muzaffarabad and Mirpur given weight 0;
- an assertion that the union has no interior rings.

**Effect on exposures.** Old vs new state-year values:

| Exposure | r | Mean \|Δ\| | Largest \|Δ\| |
|---|---|---|---|
| Degree-days | ≥0.9998 | 0.13 | 4.4 (Telangana 2019) |
| Hot nights | 0.9998 | 0.04 | — |

The full pipeline was rerun via `run_all.sh`. Pre-fix files are kept in `data_local/pre_geofix/` for comparison.

**Correction to the correction (2026-11-13).** The first fix filled only interior holes (2.3% of India). A grid check against an independent India outline (ADM2 file) found further gaps where the carved districts touch a coast or border, which are not interior rings.

`geography.py` now returns the uncovered part of every named post-2011 district to its 2011 parent: 91 pieces, 223,343 km², about 7% of India. By state:

| State | Restored area | Share of state |
|---|---|---|
| Chhattisgarh | 33,109 km² | about 25% |
| Tamil Nadu | 25,092 km² | about 19% |
| Gujarat | 23,307 km² | — |
| Arunachal Pradesh | 15,801 km² | — |

Remaining uncovered points (0.5% of the outline grid) are the Rann of Kutch, Sundarbans waters, Gilgit-Baltistan and island slivers. The pipeline was rerun again on this geography.
