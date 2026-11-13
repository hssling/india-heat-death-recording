"""State-year heat exposures (Mar-Jun), 2014-2024, from IMD gridded daily Tmax/Tmin (1 deg), population-weighted.

District geometry and Census-2011 weights from src/geography.py (post-2011 holes returned to parents, state
outline polygons dropped, Telangana area-share weights; J&K + Ladakh and DNH + DD merged).

Daily district flags (IMD heat-wave criteria for plains, applied to the district-mean of grid cells; the 1-deg grid
smooths peaks, so the departure criterion carries most weight):
  hw      heat-wave day: Tmax >= 40 and Tmax - normal >= 4.5, or Tmax >= 45
  shw     severe heat-wave day: Tmax >= 40 and departure >= 6.5, or Tmax >= 47
  hwspell heat-wave day that is part of a run of >= 2 consecutive hw days (IMD declares on 2 consecutive days)
  wn      warm night: Tmax >= 40 and Tmin - normal >= 4.5 (IMD warm-night definition)
  hn28    hot night: Tmin >= 28
  dd40    degree-days above 40 C: sum of max(Tmax - 40, 0)
  hot40   days with Tmax >= 40 C
Normals: district x day-of-year mean 1991-2020, smoothed with a 15-day circular moving average.
Output: data/state_year_heat_2014_2024.csv (Mar-Jun sums, population-weighted mean over districts).
"""
import pathlib
import numpy as np, pandas as pd, geopandas as gpd
import imdlib as imd

P = pathlib.Path(__file__).resolve().parents[1]
ROOT = P.parent
IMD = ROOT / "meta_heat_road_deaths_india/data/imd"
YEARS = range(1991, 2025)

import sys  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geography import districts  # noqa: E402  (complete 2011 geography; see geography.py)
g = districts()


def cell_index(lat, lon):
    LON, LAT = np.meshgrid(lon, lat)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs="EPSG:4326")
    pts["ij"] = list(zip(*np.unravel_index(np.arange(LAT.size), LAT.shape)))
    j = gpd.sjoin(pts, g[["geometry"]].reset_index(names="d"), predicate="within")
    idx = j.groupby("d").ij.apply(list).to_dict()
    for d, row in g.iterrows():
        if d not in idx:
            cen = row.geometry.representative_point()
            idx[d] = [(int(np.abs(lat - cen.y).argmin()), int(np.abs(lon - cen.x).argmin()))]
    return idx


cache = {}


def district_daily(var, yr):
    ds = imd.open_data(var, yr, yr, "yearwise", str(IMD)).get_xarray()
    arr = ds[var].values.astype("float64")
    arr[arr <= -999] = np.nan
    arr[arr >= 99] = np.nan
    key = (len(ds.lat), len(ds.lon))
    if key not in cache:
        cache[key] = cell_index(ds.lat.values, ds.lon.values)
    out = np.full((arr.shape[0], len(g)), np.nan)
    for d, cells in cache[key].items():
        ii, jj = zip(*cells)
        with np.errstate(all="ignore"):
            out[:, d] = np.nanmean(arr[:, ii, jj], axis=1)
    return pd.DataFrame(out, index=pd.to_datetime(ds.time.values))


TX, TN = [], []
for yr in YEARS:
    TX.append(district_daily("tmax", yr)); TN.append(district_daily("tmin", yr))
    print(yr, flush=True)
TX, TN = pd.concat(TX), pd.concat(TN)
doy = np.minimum(TX.index.dayofyear, 365)


def normal(D):
    base = D[(D.index.year >= 1991) & (D.index.year <= 2020)]
    clim = base.groupby(np.minimum(base.index.dayofyear, 365)).mean()          # 365 x districts
    ext = pd.concat([clim.iloc[-7:], clim, clim.iloc[:7]])
    sm = ext.rolling(15, center=True).mean().iloc[7:-7]
    sm.index = clim.index
    return sm.loc[doy].set_index(D.index)


NX, NN = normal(TX), normal(TN)
dep, depn = TX - NX, TN - NN
hw = ((TX >= 40) & (dep >= 4.5)) | (TX >= 45)
shw = ((TX >= 40) & (dep >= 6.5)) | (TX >= 47)
prev, nxt = hw.shift(1, fill_value=False), hw.shift(-1, fill_value=False)
hwspell = hw & (prev | nxt)
wn = (TX >= 40) & (depn >= 4.5)
hn28 = TN >= 28
dd40 = (TX - 40).clip(lower=0)
season = (TX.index.month >= 3) & (TX.index.month <= 6) & (TX.index.year >= 2014)
yr = TX.index.year[season]
metrics = {"hot40": TX >= 40, "hw": hw, "shw": shw, "hwspell": hwspell, "wn": wn, "hn28": hn28, "dd40": dd40,
           "tmax_mean": TX, "tmin_mean": TN, "tmax_dep": dep, "tmin_dep": depn}
agg = {}
for k, D in metrics.items():
    # a flag on a missing temperature is False, which would count as 0 days: mask it so districts outside the IMD land
    # grid (Andaman & Nicobar) come out missing, not "no heat"
    S = D[season].astype(float).where(TX[season].notna() & TN[season].notna())
    means = ("tmax_mean", "tmin_mean", "tmax_dep", "tmin_dep")          # season means; all other metrics are day counts
    agg[k] = S.groupby(yr).mean() if k in means else S.groupby(yr).sum(min_count=1)
w = g.Population.values
rows = []
for unit, idxs in g.groupby("unit").groups.items():
    idxs = list(idxs)
    for k, M in agg.items():
        X = M[idxs].values
        ww = np.where(np.isnan(X), 0, w[idxs])
        rows.append(pd.DataFrame({"state": unit, "year": M.index, "metric": k, "value": np.nansum(X * ww, 1) / ww.sum(1)}))
out = pd.concat(rows).pivot_table(index=["state", "year"], columns="metric", values="value", dropna=False).reset_index()
assert len(out) == 35 * 11, len(out)                                 # keep units with no grid cover as explicit NaN
(P / "data").mkdir(exist_ok=True)
out.to_csv(P / "data/state_year_heat_2014_2024.csv", index=False)
print(out.groupby("year")[["hw", "hwspell", "shw", "wn", "hn28", "dd40", "tmax_dep"]].mean().round(2).to_string())
