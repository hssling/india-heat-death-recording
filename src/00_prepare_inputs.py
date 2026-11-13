"""Export the inputs this project takes from sibling projects of the research monorepo into data/, so that every later
step reads only project-local files (and the public repository is self-contained).

Writes:
  data/adsi_heat_deaths_state_year.csv   year, unit, deaths  (ADSI heat/sun-stroke deaths, 35 constant-geography units,
                                          from shared_adsi_panel; checked against the printed all-India totals)
  data/state_population_units.csv        unit, year, population (Technical Group projections, 35 units, 2014-2024)
  data/states_2011_complete.geojson      35 units dissolved from the complete 2011 district geography (src/geography.py),
                                          simplified for mapping only
Run inside the monorepo only; the public repository ships these files.
"""
import pathlib, sys
from importlib import import_module
import pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
ROOT = P.parent
D = P / "data"

A = pd.read_csv(ROOT / "shared_adsi_panel/data/adsi_panel_35.csv")
h = A[(A.cause == "Heat/Sun Stroke") & (A.sex == "total") & (A.measure == "died")].groupby(["year", "unit"], as_index=False).n.sum()
T = pd.read_csv(ROOT / "shared_adsi_panel/data/adsi_cause_totals.csv")
pr = T[T.unit.str.contains("INDIA") & (T.cause.str.replace(r"[^A-Za-z]", "", regex=True).str.lower() == "heatsunstroke")
       & (T.measure == "died") & (T.sex == "total")].groupby("year").n.sum()
chk = pd.concat([h.groupby("year").n.sum().rename("panel"), pr.rename("printed")], axis=1)
assert len(chk) == 11 and (chk.panel == chk.printed).all(), chk
assert h.groupby("year").unit.nunique().eq(35).all()
h.rename(columns={"n": "deaths"}).to_csv(D / "adsi_heat_deaths_state_year.csv", index=False)
print("heat deaths:", int(h.n.sum()), "; matches printed all-India totals for all 11 years")

sys.path.insert(0, str(ROOT / "meta_occupation_suicide_india/src"))
UNITS = import_module("04_build_panel").UNITS
POP = pd.read_csv(ROOT / "meta_occupation_suicide_india/data/state_population.csv")
POP = POP[POP.state.isin([v[2] for v in UNITS.values()]) & POP.year.between(2014, 2024)]
POP = POP.assign(unit=POP.state.map({v[2]: u for u, v in UNITS.items()}))[["unit", "year", "population"]]
assert POP.unit.nunique() == 35 and len(POP) == 35 * 11, (POP.unit.nunique(), len(POP))
POP.to_csv(D / "state_population_units.csv", index=False)
print("population: 35 units x 11 years; India 2024", f"{POP[POP.year == 2024].population.sum():,.0f}")

sys.path.insert(0, str(P / "src"))
from geography import districts  # noqa: E402
g = districts(verbose=False)
st = g.dissolve("unit")[["geometry"]].reset_index()
st["geometry"] = st.geometry.simplify(0.01, preserve_topology=True)
st.to_file(D / "states_2011_complete.geojson", driver="GeoJSON")
print("state geometry: ", len(st), "units")
