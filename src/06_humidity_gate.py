"""Gate 4: is the state recording gap (and the 2024 surge) humid heat that dry-bulb IMD Tmax misses?

Humid-heat exposure from NASA POWER daily point data (05_fetch_power.py), one point per district:
  e      = q p / (0.622 + 0.378 q)          vapour pressure (kPa) from specific humidity q (kg/kg) and surface pressure p
  RH_tx  = 100 e / es(Tmax), es(T) = 0.6108 exp(17.27 T / (T + 237.3))
  Tw_max = Stull (2011) wet bulb at (Tmax, RH_tx)  -- afternoon wet bulb; POWER's T2MWET is a daily mean
Specific humidity varies little within a day, so RH at Tmax is the afternoon RH. Mar-Jun season metrics per district:
  tw26, tw28   days with Tw_max >= 26 / 28 C
  twdd26       sum of max(Tw_max - 26, 0)
  twmean       mean Tw_max
then Census-2011 population-weighted state means.
Sanity check: POWER Tmax vs IMD Tmax, state-season means (should correlate strongly).

Pre-specified rule (written before results): humidity explains the recording gap -> FAIL if, among units with >= 50
deaths, adding wet-bulb exposure (a) cuts SD(log index) below 50% of the gate-3 dry-heat index, or (b) brings BOTH
Andhra Pradesh / Madhya Pradesh and Punjab / Madhya Pradesh below 3-fold. Index variants as in 04_state_index.py:
W0 heat effects within state (state FE, dropped for prediction); W1 between states with age60 + outdoor (generous).
Also reported: within-state wet-bulb signal; 2024 obs/pred with wet bulb added.
Outputs: data/state_year_wetbulb.csv, outputs/humidity_gate.csv, outputs/humidity_2024.csv
"""
import json, pathlib, re, sys, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm

warnings.filterwarnings("ignore")
P = pathlib.Path(__file__).resolve().parents[1]
RAW = P / "data_local/power"


def stull(T, RH):
    RH = np.clip(RH, 5, 99)
    return (T * np.arctan(0.151977 * np.sqrt(RH + 8.313659)) + np.arctan(T + RH) - np.arctan(RH - 1.676331)
            + 0.00391838 * RH ** 1.5 * np.arctan(0.023101 * RH) - 4.686035)


# ---------------- exposures (rebuilt from the NASA POWER cache when present; otherwise the shipped table is used)
if RAW.exists() and any(RAW.glob("*.json")):
    pts = pd.read_csv(P / "data/district_points.csv")
    cell = {}
    for cid in pts.cell.unique():
        j = json.loads((RAW / f"{cid}.json").read_text())
        df = pd.DataFrame(j).replace(-999.0, np.nan)
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df = df[df.index.month.isin([3, 4, 5, 6])]
        q = df.QV2M / 1000
        e = q * df.PS / (0.622 + 0.378 * q)
        es = 0.6108 * np.exp(17.27 * df.T2M_MAX / (df.T2M_MAX + 237.3))
        tw = stull(df.T2M_MAX, 100 * e / es)
        yr = df.index.year
        cell[cid] = pd.DataFrame({
            "tw26": (tw >= 26).where(tw.notna()).groupby(yr).sum(min_count=1),
            "tw28": (tw >= 28).where(tw.notna()).groupby(yr).sum(min_count=1),
            "twdd26": (tw - 26).clip(lower=0).groupby(yr).sum(min_count=1),
            "twmean": tw.groupby(yr).mean(),
            "power_tmax": df.T2M_MAX.groupby(yr).mean()})
    rows = []
    for r in pts.itertuples():
        rows.append(cell[r.cell].assign(unit=r.unit, w=r.population).rename_axis("year").reset_index())
    X = pd.concat(rows)
    mets = ["tw26", "tw28", "twdd26", "twmean", "power_tmax"]
    W = X.groupby(["unit", "year"]).apply(lambda g: pd.Series({m: np.average(g[m], weights=g.w) for m in mets})).reset_index()
    W = W.rename(columns={"unit": "state"})
    W.to_csv(P / "data/state_year_wetbulb.csv", index=False)
    print("national mean (unweighted over units) by year:")
    print(W.groupby("year")[["tw26", "tw28", "twdd26", "twmean"]].mean().round(2).T.to_string())
else:
    print("NASA POWER cache not present: using data/state_year_wetbulb.csv")

# ---------------- panel (shared builder)
sys.path.insert(0, str(P / "src"))
from panel import build  # noqa: E402
d = build(wetbulb=True)
r = d[["power_tmax", "tmax_mean"]].corr().iloc[0, 1]
wr = d.assign(a=d.power_tmax - d.groupby("unit").power_tmax.transform("mean"),
              b=d.tmax_mean - d.groupby("unit").tmax_mean.transform("mean"))[["a", "b"]].corr().iloc[0, 1]
print(f"sanity: POWER vs IMD season-mean Tmax r = {r:.3f} (within-unit r = {wr:.3f}); mean bias {(d.power_tmax - d.tmax_mean).mean():+.2f} C")
assert r > 0.8, "POWER and IMD Tmax disagree; check the fetch"

pois = sm.families.Poisson()

# ---------------- (a) within-state wet-bulb signal, 15 units
tot = d.groupby("unit").n.sum()
s15 = d[d.unit.isin(tot[tot >= 20].index)].copy()
g15 = pd.factorize(s15.unit)[0]
print("\n--- within-state signal (15 units, state + year FE, pop offset, clustered SE)")
base = smf.glm("n ~ dd40 + hn28 + C(unit) + C(year)", s15, family=pois, offset=s15.lpop).fit()
sig = []
for x in ("tw26", "tw28", "twdd26", "twmean"):
    for f in (f"n ~ {x} + C(unit) + C(year)", f"n ~ dd40 + hn28 + {x} + C(unit) + C(year)"):
        m = smf.glm(f, s15, family=pois, offset=s15.lpop).fit(cov_type="cluster", cov_kwds={"groups": g15})
        wsd = s15.groupby("unit")[x].transform(lambda v: v - v.mean()).std()
        b, se = m.params[x], m.bse[x]
        print(f"{f:48s} RR/within-SD({wsd:5.2f}) {np.exp(b * wsd):.2f} ({np.exp((b - 1.96 * se) * wsd):.2f}-{np.exp((b + 1.96 * se) * wsd):.2f})  dAIC vs dry {m.aic - base.aic:+.1f}")
        sig.append({"model": f, "exposure": x, "with_dry_heat": "dd40" in f, "within_sd": wsd, "RR_per_sd": np.exp(b * wsd),
                    "lo": np.exp((b - 1.96 * se) * wsd), "hi": np.exp((b + 1.96 * se) * wsd), "dAIC_vs_dry": m.aic - base.aic})
pd.DataFrame(sig).to_csv(P / "outputs/humidity_signal.csv", index=False)


# ---------------- (b) recording index with wet bulb
def index_from(model, data, drop_fe):
    Xd = data.copy()
    if drop_fe:
        Xd["unit"] = model.model.data.frame.unit.iloc[0]
    mu = np.exp(model.predict(Xd, which="linear", offset=Xd.lpop))
    mu *= data.n.sum() / mu.sum()
    g = data.assign(E=mu.values).groupby("unit").agg(O=("n", "sum"), E=("E", "sum"))
    return g.O / g.E


anyd = d[d.unit.isin(tot[tot > 0].index)]
ga, gall = pd.factorize(anyd.unit)[0], pd.factorize(d.unit)[0]
specs = {
    "dry_within (gate-3 I0)": ("n ~ dd40 + hn28 + C(year) + C(unit)", True),
    "dry_between + cov (gate-3 I1)": ("n ~ dd40 + hn28 + age60 + outdoor + C(year)", False),
    "W0 wet_within": ("n ~ dd40 + hn28 + twdd26 + tw28 + C(year) + C(unit)", True),
    "W1 wet_between + cov": ("n ~ dd40 + hn28 + twdd26 + tw28 + age60 + outdoor + C(year)", False),
    "W2 wet-only_between + cov": ("n ~ twdd26 + tw28 + twmean + age60 + outdoor + C(year)", False),
}
idx = {}
for nm, (f, fe) in specs.items():
    data, grp = (anyd, ga) if fe else (d, gall)
    m = smf.glm(f, data, family=pois, offset=data.lpop).fit(cov_type="cluster", cov_kwds={"groups": grp})
    idx[nm] = index_from(m, d, fe)
    terms = [t for t in m.params.index if t in ("twdd26", "tw28", "twmean")]
    print(f"{nm:30s}", {t: round(float(np.exp(m.params[t])), 3) for t in terms})
I = pd.DataFrame(idx).join(tot.rename("deaths")).join(d.groupby("unit")[["dd40", "twdd26", "tw28", "twmean"]].mean())
(P / "outputs").mkdir(exist_ok=True)
I.to_csv(P / "outputs/humidity_gate.csv")
big = I[I.deaths >= 50]
pd.set_option("display.width", 220)
print("\n", big.sort_values("W1 wet_between + cov").round(2).to_string())
sd0 = np.log(big["dry_within (gate-3 I0)"]).std()
ok = True
print(f"\n--- gate 4 rule ({len(big)} units >= 50 deaths); reference SD(log) dry_within = {sd0:.2f}")
for nm in ("W0 wet_within", "W1 wet_between + cov", "W2 wet-only_between + cov"):
    v = big[nm]
    sd = np.log(v).std()
    ap = v["ANDHRA PRADESH"] / v["MADHYA PRADESH"]
    pb = v["PUNJAB"] / v["MADHYA PRADESH"]
    fail = sd < 0.5 * sd0 or (ap < 3 and pb < 3)
    ok &= not fail
    print(f"{nm:28s} SD log {sd:.2f} ({sd / sd0:.0%})  AP/MP {ap:5.1f}  Punjab/MP {pb:5.1f}  max/min {v.max() / v.min():5.1f}  {'FAIL' if fail else 'PASS'}")
print("GATE 4:", "PASS" if ok else "FAIL")

# ---------------- (c) 2024 with wet bulb
fs = s15[(s15.year < 2024) & ~s15.year.isin([2020, 2021])]
d24 = s15[s15.year == 2024]
rows = []
for f in ("dd40 + hn28", "dd40 + hn28 + twdd26", "dd40 + hn28 + tw28", "dd40 + hn28 + twdd26 + tw28", "twdd26 + tw28 + twmean"):
    m = smf.glm(f"n ~ {f} + C(unit) + year", fs, family=pois, offset=fs.lpop).fit()
    pr = m.predict(d24, offset=d24.lpop).sum()
    rows.append({"heat_terms": f, "AIC_fit": m.aic, "pred24": pr, "obs24": d24.n.sum(), "obs/pred": d24.n.sum() / pr})
S = pd.DataFrame(rows)
S.to_csv(P / "outputs/humidity_2024.csv", index=False)
print("\n--- 2024 out-of-sample with wet bulb (fit 2014-23 excl. 2020-21)")
print(S.round(2).to_string(index=False))
print("\n2024 vs 2014-23 mean, wet-bulb exposure (15 units):")
print(s15.assign(p=s15.year == 2024).groupby("p")[["twdd26", "tw28", "dd40", "hn28"]].mean().round(2).to_string())
