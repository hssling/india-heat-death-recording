# How many heat deaths does India record? Code and data

Code and derived data for *How many heat deaths does India record? Exposure-adjusted recording of heat-stroke deaths
across states, 2014–2024* (Siddalingaiah H S; manuscript under review).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24184627.svg)](https://doi.org/10.5281/zenodo.24184627)

## What the study does

The study links every police-recorded heat/sun-stroke death in India for 2014–2024 (National Crime Records Bureau,
*Accidental Deaths and Suicides in India*) to population-weighted March–June heat exposure. Exposure is built from the
India Meteorological Department gridded daily temperatures (degree-days above 40 °C; nights with minimum ≥ 28 °C).

A Bayesian hierarchical Poisson–lognormal model (NumPyro) estimates each state's recording index: recorded deaths
relative to the average large state at the same heat, population and year. The heat effect is identified within states
through a Mundlak term.

Before the main model, four pre-specified tests examine alternative explanations:
- heat signal;
- age and outdoor work, from Periodic Labour Force Survey aggregates;
- the shape of the dose–response;
- humid heat (NASA POWER wet bulb).

The rules for the last three were written before each was run; see `docs/killcheck_report.md`.

## Repository layout

| Path | Contents |
|---|---|
| `data/` | Derived state-year inputs: ADSI heat deaths (35 units); IMD heat exposures; wet bulb; PLFS aggregate shares; Technical Group population; NCDC national surveillance |
| `src/` | Pipeline steps 00–09 and shared modules (`panel.py`, `geography.py`, `plfs_io.py`) |
| `outputs/` | All result tables, including posterior summaries and draws (`bayes_posterior.npz`), and `numbers.json` |
| `figures/` | Figures 1–4 (PNG, PDF) |
| `results/expected_key_results.json` | The numbers as printed in the article |
| `verify.py` | Recomputes the reported numbers from `outputs/` and `data/` and checks them against `results/expected_key_results.json` |
| `docs/` | Pre-specified test reports and the policy-source register, with evidence grades |

## Reproduce

```bash
pip install -r requirements.txt -r requirements-bayes.txt
bash run_all.sh      # runs steps 02-09 from the shipped tables, then verify.py
```

Steps 00, 01, 03 and 05 rebuild the derived tables from raw sources and run only where those sources exist.

| Step | Raw source | Availability |
|---|---|---|
| 01 | IMD .GRD files | `imdlib`, public |
| 03 | PLFS unit-level data | Licensed from https://microdata.gov.in; not redistributed here, as the access agreement forbids it. Only weighted aggregate shares are shipped. |
| 05 | NASA POWER daily point data | Public API |
| 00 | Shared ADSI cause panel and boundary files | Research monorepo; ADSI reports are public at https://www.ncrb.gov.in |

District boundaries, and the state geometry derived from them, are not redistributed because their licence is unclear. The map (Figure 2 of the article, `figures/fig1_map_recording_index.*`) is shipped rendered; `08_figures.py` regenerates the other figures.

The CI workflow reruns the tests, figures and numbers on Linux and runs `verify.py`. A second job refits the main
Bayesian model and requires every large-state index to match the shipped value within 5% on the log scale.

## Licence

Code: MIT. Derived data: CC BY 4.0.

PLFS-derived tables are weighted aggregates. No attempt was made to identify any person or household.

## Use of AI tools

A large language model (Anthropic Claude) assisted with code, analysis checks, literature verification and drafting.
The author directed the study and is responsible for all content.
