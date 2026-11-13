#!/usr/bin/env bash
# Full pipeline, in order. Stops at the first failure.
# Raw-data steps run only where their inputs exist (the research monorepo): 00 (shared ADSI panel, population,
# geography), 01 (IMD .GRD files), 03 (licensed PLFS unit data), 05 (district geometry; NASA POWER API).
# Everywhere else (the public repository) the derived tables they write are shipped in data/ and steps 02-10 run.
set -euo pipefail
cd "$(dirname "$0")"
run() { echo "== $*"; python -X utf8 "$@"; }
if [ -d ../shared_adsi_panel ]; then run src/00_prepare_inputs.py > outputs_prepare_inputs.log 2>&1; fi   # monorepo only
if [ -d ../meta_heat_road_deaths_india/data/imd ]; then run src/01_build_heat_exposures.py > outputs_build_exposures.log 2>&1; fi   # needs IMD .GRD files
run src/02_exposure_test.py          > outputs_exposure_test.log 2>&1
if [ ! -f data/state_season_covariates.csv ]; then run src/03_plfs_covariates.py > outputs_plfs_covariates.log 2>&1; fi   # needs licensed PLFS unit data
run src/04_state_index.py            > outputs_state_index.log 2>&1
if [ -d ../meta_district_injury_atlas_india ]; then run src/05_fetch_power.py > outputs_fetch_power.log 2>&1; fi   # needs district geometry
run src/06_humidity_gate.py          > outputs_humidity_gate.log 2>&1
for v in main negbin nocovid hwdays nomundlak; do
  echo "== 07 VARIANT=$v"; VARIANT=$v python -X utf8 src/07_bayes_model.py > outputs_bayes_$v.log 2>&1
done
run src/08_figures.py                > outputs_figures.log 2>&1
run src/09_numbers.py                > outputs_numbers.log 2>&1
run verify.py
echo "pipeline complete"
