"""Shared assembly of the analysis panel from project-local files (data/):
ADSI heat/sun-stroke deaths x IMD exposures x PLFS covariates x Technical Group population (x NASA POWER wet bulb when
available), 35 constant-geography units, 2014-2024.
Units without exposure (Andaman & Nicobar Islands: outside the IMD land grid; 0 heat deaths) are dropped with a note.
"""
import pathlib, re
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
D = P / "data"


def key(u):
    u = u.lower().replace("(incl. ladakh)", "").replace("(ut)", "").replace("(former j&k state)", "").replace("islands", "")
    k = re.sub(r"[^a-z]", "", u.replace(" and ", " "))
    return {"an": "andamannicobar", "jammukashmir": "jkladakh", "jammukashmirladakh": "jkladakh",
            "dadranagarhavelidamandiu": "dnhdd"}.get(k, k)


def deaths():
    """ADSI heat/sun-stroke deaths: year, unit, n (35 units)."""
    return pd.read_csv(D / "adsi_heat_deaths_state_year.csv").rename(columns={"deaths": "n"})


def build(wetbulb=True, verbose=True):
    d = deaths()
    E = pd.read_csv(D / "state_year_heat_2014_2024.csv")
    COV = pd.read_csv(D / "state_season_covariates.csv")
    POP = pd.read_csv(D / "state_population_units.csv")
    parts = [(d, "unit"), (E, "state"), (COV, "unit"), (POP, "unit")]
    wfile = D / "state_year_wetbulb.csv"
    W = pd.read_csv(wfile) if wetbulb and wfile.exists() else None
    if W is not None:
        parts.append((W, "state"))
    for df, col in parts:
        df["k"] = df[col].map(key)
    ks = [set(df.k) for df, _ in parts]
    assert all(s == ks[0] for s in ks) and len(ks[0]) == 35, [sorted(s ^ ks[0]) for s in ks]
    d = (d.merge(E.drop(columns="state"), on=["k", "year"]).merge(COV.drop(columns="unit"), on=["k", "year"])
          .merge(POP[["k", "year", "population"]], on=["k", "year"]))
    if W is not None:
        d = d.merge(W.drop(columns="state"), on=["k", "year"])
    assert len(d) == 385 and d.population.notna().all() and d.n.notna().all()
    d["lpop"] = np.log(d.population)
    bad = d.hw.isna() | (d.twmean.isna() if W is not None else False)
    nogrid = d[bad].unit.unique()
    if verbose:
        print("dropped (no exposure):", list(nogrid), "deaths", d[d.unit.isin(nogrid)].n.sum())
    return d[~d.unit.isin(nogrid)].copy()
