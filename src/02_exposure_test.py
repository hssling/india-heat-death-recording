"""Kill-level test 2: do better heat exposures (IMD heat-wave days, severe days, spells, warm/hot nights, degree-days)
explain (a) within-state variation in recorded heat-stroke deaths and (b) the 2024 jump?

Sample: the 15 units with >= 20 ADSI heat/sun-stroke deaths 2014-24 (as in 00_kill_check.py).
(a) Poisson, state FE + year FE, SE clustered by state; RR per within-state SD; AIC on identical rows.
(b) Fit state FE + linear trend + exposure on 2014-23 (and on 2014-23 minus COVID 2020-21), predict 2024.
Kill rule (pre-specified in docs/killcheck_report.md): if observed/predicted 2024 stays > 2 under the best exposure,
the 2024 rise is recording drift, not heat.
Output: outputs/exposure_test.csv, printed tables.
"""
import pathlib, re, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm

warnings.filterwarnings("ignore")
P = pathlib.Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(P / "src"))
from panel import build  # noqa: E402

# heat models here use state fixed effects, so population enters through the fixed effects and trend (no offset)
d = build(wetbulb=False)
assert d.hot40.notna().all()

tot = d.groupby("unit").n.sum()
d = d[d.unit.isin(tot[tot >= 20].index)].copy()
print(d.unit.nunique(), "units,", len(d), "unit-years,", d.n.sum(), "deaths")
grp = pd.factorize(d.unit)[0]
X = ["hot40", "hw", "hwspell", "shw", "wn", "hn28", "dd40", "tmax_dep", "tmin_dep"]


def fit(f, data, groups=None):
    m = smf.glm(f, data, family=sm.families.Poisson())
    return m.fit(cov_type="cluster", cov_kwds={"groups": groups}) if groups is not None else m.fit()


base = fit("n ~ C(unit) + C(year)", d)
rows = []
fitset = d[d.year < 2024]
noc = fitset[~fitset.year.isin([2020, 2021])]
d24 = d[d.year == 2024]
for x in X + ["hw + hn28", "dd40 + hn28"]:
    m = fit(f"n ~ {x} + C(unit) + C(year)", d, grp)
    r = {"exposure": x, "AIC": m.aic, "dAIC_vs_FE_only": m.aic - base.aic}
    if "+" not in x:
        b, se = m.params[x], m.bse[x]
        wsd = d.groupby("unit")[x].transform(lambda v: v - v.mean()).std()
        r.update(within_sd=wsd, RR_per_sd=np.exp(b * wsd), lo=np.exp((b - 1.96 * se) * wsd), hi=np.exp((b + 1.96 * se) * wsd))
    for lab, fs in (("pred24", fitset), ("pred24_noCOVID", noc)):
        r[lab] = fit(f"n ~ {x} + C(unit) + year", fs).predict(d24).sum()
    rows.append(r)
r0 = {"exposure": "none (FE + trend)", "AIC": fit("n ~ C(unit) + year", d).aic}
for lab, fs in (("pred24", fitset), ("pred24_noCOVID", noc)):
    r0[lab] = fit("n ~ C(unit) + year", fs).predict(d24).sum()
rows.append(r0)
R = pd.DataFrame(rows)
obs = d24.n.sum()
R["obs24"] = obs
R["obs/pred"] = obs / R.pred24
R["obs/pred_noCOVID"] = obs / R.pred24_noCOVID
(P / "outputs").mkdir(exist_ok=True)
R.to_csv(P / "outputs/exposure_test.csv", index=False)
pd.set_option("display.width", 200)
print(R.round(3).to_string(index=False))

print("\n--- national (15-unit) series: deaths and mean exposures")
print(d.groupby("year").agg(deaths=("n", "sum"), hot40=("hot40", "mean"), hw=("hw", "mean"), shw=("shw", "mean"),
                            wn=("wn", "mean"), hn28=("hn28", "mean"), dd40=("dd40", "mean")).round(2).T.to_string())

# which units carry the 2024 excess under the best single exposure (lowest AIC)?
best = R.dropna(subset=["RR_per_sd"]).sort_values("AIC").exposure.iloc[0]
m = fit(f"n ~ {best} + C(unit) + year", noc)
u = d24.assign(pred=m.predict(d24))[["unit", "n", "pred", best]]
u["obs/pred"] = u.n / u.pred
print(f"\n--- 2024 by unit, best exposure = {best} (fit 2014-23 excl. 2020-21)")
print(u.sort_values("n", ascending=False).round(2).to_string(index=False))
u.assign(excess=u.n - u.pred, exposure=best).to_csv(P / "outputs/obs_pred_2024_by_unit.csv", index=False)

# Calibration of the kill rule: is a >2x miss unusual? Leave-one-year-out, same model family, best combined exposure.
# Fit on all other non-COVID years (state FE + trend + exposure), predict the held-out year.
print("\n--- leave-one-year-out: obs/pred for each held-out year (fit excludes held-out year and 2020-21)")
lo = []
for x in ("dd40 + hn28", "hot40", "hw + hn28"):
    for t in range(2014, 2025):
        fs = d[(d.year != t) & ~d.year.isin([2020, 2021])]
        dt = d[d.year == t]
        pr = fit(f"n ~ {x} + C(unit) + year", fs).predict(dt).sum()
        lo.append({"exposure": x, "year": t, "obs": dt.n.sum(), "pred": pr, "obs/pred": dt.n.sum() / pr})
L = pd.DataFrame(lo)
L.to_csv(P / "outputs/loyo_calibration.csv", index=False)
print(L.pivot(index="exposure", columns="year", values="obs/pred").round(2).to_string())
