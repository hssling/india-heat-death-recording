"""State x heat-season covariates from PLFS unit-level data (aggregates only; no unit records are written).

Uses the tested loaders and 35-unit map in src/plfs_io.py (copied from the occupation-suicide project).
Per round x unit, weighted shares of the whole population (all ages):
  age60    aged >= 60
  outdoor  usual-status worker (principal status if a worker, else subsidiary) in NIC-2008 divisions 01-03
           (agriculture, forestry, fishing), 05-09 (mining, quarrying) or 41-43 (construction)
  casual   usual-status casual labourer (status 41, 51)
Heat season Mar-Jun of year Y lies in PLFS round (Y-1)-(Y); 2024 = mean of 2023-24 and CY2024.
2014-2017 have no PLFS round and take the 2017-18 values (covariates move slowly; flagged by `carried`).
Output: data/state_season_covariates.csv
"""
import pathlib, sys
import pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
import plfs_io as plfs  # noqa: E402  (loaders + unit map, see plfs_io.py)
CODE2UNIT = {c: u for u, (_, cl, _) in plfs.UNITS.items() for c in cl}
OUTDOOR = set(range(1, 4)) | set(range(5, 10)) | set(range(41, 44))
WORK = plfs.WORK

rows = []
for rnd, f in plfs.ROUNDS.items():
    if rnd == "CY2025":
        continue
    d = plfs.load(f)
    worker_ps = d.ups.isin(WORK)
    status = d.ups.where(worker_ps, d.uss.where(d.uss.isin(WORK)))
    nic = d.nic2.where(worker_ps, d.nic2_ss)
    d["age60"] = (d.age >= 60).astype(float)
    d["outdoor"] = (status.notna() & nic.isin(OUTDOOR)).astype(float)
    d["casual"] = status.isin([41, 51]).astype(float)
    d["unit"] = d.state.map(CODE2UNIT)
    assert d.unit.notna().all(), sorted(d.state[d.unit.isna()].unique())
    for c in ("age60", "outdoor", "casual"):
        d[c] = d[c] * d.w
    g = d.groupby("unit")[["w", "age60", "outdoor", "casual"]].sum()
    g[["age60", "outdoor", "casual"]] = g[["age60", "outdoor", "casual"]].div(g.w, axis=0)
    g = g.drop(columns="w").reset_index().assign(round=rnd, n=d.groupby("unit").size().values)
    rows.append(g)
    nat = d[["age60", "outdoor", "casual"]].sum() / d.w.sum()
    print(rnd, f"n={len(d):,}", nat.round(3).to_dict(), flush=True)
R = pd.concat(rows)
assert R.unit.nunique() == 35

season = {y: [f"{y - 1}-{str(y)[2:]}"] for y in range(2018, 2024)}
season[2024] = ["2023-24", "CY2024"]
out = []
for y in range(2014, 2025):
    rr = season.get(y, ["2017-18"])
    s = R[R["round"].isin(rr)].groupby("unit")[["age60", "outdoor", "casual"]].mean().reset_index()
    out.append(s.assign(year=y, carried=y < 2018))
C = pd.concat(out)
assert len(C) == 35 * 11
C.to_csv(P / "data/state_season_covariates.csv", index=False)
print(C[C.year == 2024].sort_values("outdoor").round(3).to_string(index=False))
