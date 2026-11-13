"""Fetch NASA POWER daily point data (MERRA-2 based, 0.5 x 0.625 deg) for every district representative point,
2014-01-01 to 2024-12-31: T2M_MAX, QV2M (g/kg), PS (kPa), RH2M (%), T2MWET (daily-mean wet bulb, C).

Districts and Census-2011 populations from src/geography.py (as in 01_build_heat_exposures.py). Points are snapped to the
POWER grid and de-duplicated; each grid cell is fetched once and cached as JSON in data_local/power/ (raw downloads,
kept apart from code; only parsed with json.load). Re-running skips cached cells.
Only coordinates are sent; generic User-Agent. Sequential requests with a pause (POWER asks for moderate use).
Output: data/district_points.csv (district index, unit, population, lat, lon, cell id)
"""
import json, pathlib, time
import numpy as np, pandas as pd, geopandas as gpd, requests

P = pathlib.Path(__file__).resolve().parents[1]
RAW = P / "data_local/power"
RAW.mkdir(parents=True, exist_ok=True)

import sys  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geography import districts  # noqa: E402  (complete 2011 geography; see geography.py)
g = districts()

rp = g.geometry.representative_point()
pts = pd.DataFrame({"d": g.index, "unit": g.unit, "district": g.district, "population": g.Population,
                    "lat": rp.y.values, "lon": rp.x.values})
pts["glat"] = (np.round(pts.lat / 0.5) * 0.5).round(3)
pts["glon"] = (np.round(pts.lon / 0.625) * 0.625).round(4)
pts["cell"] = pts.glat.astype(str) + "_" + pts.glon.astype(str)
pts.to_csv(P / "data/district_points.csv", index=False)
cells = pts.drop_duplicates("cell")[["cell", "glat", "glon"]]
print(len(pts), "districts ->", len(cells), "POWER cells", flush=True)

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
todo = [r for r in cells.itertuples() if not (RAW / f"{r.cell}.json").exists()]
print(len(todo), "to fetch", flush=True)
for i, r in enumerate(todo):
    for attempt in range(4):
        try:
            resp = requests.get(URL, params=dict(parameters="T2M_MAX,QV2M,PS,RH2M,T2MWET", community="AG",
                                                 latitude=r.glat, longitude=r.glon, start="20140101", end="20241231",
                                                 format="JSON"), headers={"User-Agent": "research-client/1.0"}, timeout=180)
            resp.raise_for_status()
            j = resp.json()
            assert len(j["properties"]["parameter"]["T2M_MAX"]) == 4018
            (RAW / f"{r.cell}.json").write_text(json.dumps(j["properties"]["parameter"]))
            break
        except Exception as e:  # noqa: BLE001
            print("retry", r.cell, attempt, repr(e)[:120], flush=True)
            time.sleep(10 * (attempt + 1))
    else:
        raise SystemExit(f"failed {r.cell}")
    if i % 25 == 0:
        print(i, "/", len(todo), flush=True)
    time.sleep(1)
print("done", len(list(RAW.glob("*.json"))), "cells cached")
