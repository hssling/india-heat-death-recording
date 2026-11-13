"""Gate 3: does the state recording index survive population, age and outdoor-work adjustment? Plus a dose-response
(spline) check on the 2024 miss.

All 35 units, Mar-Jun heat seasons 2014-2024, ADSI heat/sun-stroke deaths (calendar year), Technical Group population.
Recording index = observed / expected deaths, expected = pop x exp(beta . heat + gamma_t + covariates), rescaled so that
expected = observed nationally (index 1 = national average recording at that unit's heat and population).
  I0  heat only: beta, gamma_t estimated WITHIN state (state FE model, units with any deaths), applied without the FE
  I1  + age60 + outdoor share, coefficients estimated BETWEEN states (no state FE). This is deliberately generous to
      the confounding explanation: covariates absorb as much between-state variation as they can.
  I2  as I1 but heat measured relative to local climate (IMD heat-wave days, departure-based), the acclimatisation
      sensitivity: hot states may tolerate the same absolute temperature better.
Pre-specified survival rule (written before running): among units with >= 50 deaths, the index survives if under I1
and I2 (i) max/min index >= 10 and (ii) SD(log index) is >= 50% of its I0 value.
Outputs: outputs/state_index.csv, outputs/spline_2024.csv
"""
import pathlib, re, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm
from scipy.stats import chi2

warnings.filterwarnings("ignore")
P = pathlib.Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(P / "src"))
from panel import build  # noqa: E402

d = build(wetbulb=False)
print(f"{len(d)} unit-years, {d.n.sum()} deaths, national pop 2024 {d[d.year == 2024].population.sum() / 1e9:.3f} bn")
print(f"{len(d)} unit-years, {d.n.sum()} deaths, national pop 2024 {d[d.year == 2024].population.sum() / 1e9:.3f} bn")

pois = sm.families.Poisson()


def index_from(model, data, drop_fe=True):
    """Expected deaths from the model's linear predictor without the state FE, rescaled to national observed."""
    X = data.copy()
    if drop_fe:
        X["unit"] = model.model.data.frame.unit.iloc[0]          # reference level: FE contributes 0
    mu = np.exp(model.predict(X, which="linear", offset=X.lpop))
    mu *= data.n.sum() / mu.sum()
    g = data.assign(E=mu.values).groupby("unit").agg(O=("n", "sum"), E=("E", "sum"))
    lo = chi2.ppf(0.025, 2 * g.O) / 2 / g.E
    hi = chi2.ppf(0.975, 2 * (g.O + 1)) / 2 / g.E
    return (g.O / g.E).rename("idx"), lo.fillna(0), hi


anyd = d[d.unit.isin(d.groupby("unit").n.sum().pipe(lambda s: s[s > 0]).index)]
grp = pd.factorize(anyd.unit)[0]
res = {}
m0 = smf.glm("n ~ dd40 + hn28 + C(year) + C(unit)", anyd, family=pois, offset=anyd.lpop).fit(cov_type="cluster", cov_kwds={"groups": grp})
res["I0_heat_within"] = index_from(m0, d)
g_all = pd.factorize(d.unit)[0]
m1 = smf.glm("n ~ dd40 + hn28 + age60 + outdoor + C(year)", d, family=pois, offset=d.lpop).fit(cov_type="cluster", cov_kwds={"groups": g_all})
res["I1_plus_age_outdoor"] = index_from(m1, d, drop_fe=False)
m2 = smf.glm("n ~ hw + tmax_dep + hn28 + age60 + outdoor + C(year)", d, family=pois, offset=d.lpop).fit(cov_type="cluster", cov_kwds={"groups": g_all})
res["I2_relative_heat"] = index_from(m2, d, drop_fe=False)
for nm, m in (("within-state heat (I0)", m0), ("between-state + covariates (I1)", m1), ("relative heat (I2)", m2)):
    terms = [t for t in m.params.index if not t.startswith("C(") and t != "Intercept"]
    print(f"\n{nm}:", {t: f"{np.exp(m.params[t]):.3g} ({np.exp(m.conf_int().loc[t, 0]):.3g}-{np.exp(m.conf_int().loc[t, 1]):.3g})" for t in terms})

tab = pd.concat({f"{k}_{s}": v[i] for k, v in res.items() for i, s in enumerate(["idx", "lo", "hi"])}, axis=1)
deaths = d.groupby("unit").n.sum().rename("deaths")
cov = d.groupby("unit")[["dd40", "hw", "age60", "outdoor"]].mean()
tab = tab.join(deaths).join(cov).sort_values("I1_plus_age_outdoor_idx")
(P / "outputs").mkdir(exist_ok=True)
tab.to_csv(P / "outputs/state_index.csv")
pd.set_option("display.width", 220)
show = tab[["deaths", "dd40", "outdoor", "age60"] + [c for c in tab.columns if c.endswith("_idx")]]
print("\n", show.round(2).to_string())

big = tab[tab.deaths >= 50]
print(f"\n--- survival rule, {len(big)} units with >= 50 deaths")
sd0 = np.log(big["I0_heat_within_idx"]).std()
ok = True
for k in res:
    v = big[f"{k}_idx"]
    fold, sd = v.max() / v.min(), np.log(v).std()
    rule = k == "I0_heat_within" or (fold >= 10 and sd >= 0.5 * sd0)
    ok &= rule
    print(f"{k:22s} max/min {fold:6.1f} (max {v.idxmax()}, min {v.idxmin()})  SD log {sd:.2f} ({sd / sd0:.0%} of I0)  {'PASS' if rule else 'FAIL'}")
print("GATE 3:", "PASS" if ok else "FAIL")

# Dose-response check: does a flexible (natural spline) heat term explain the 2024 miss? 15 units, as in 02.
tot = d.groupby("unit").n.sum()
s15 = d[d.unit.isin(tot[tot >= 20].index)]
fs = s15[(s15.year < 2024) & ~s15.year.isin([2020, 2021])]
d24 = s15[s15.year == 2024]
rows = []
for f in ("dd40 + hn28", "cr(dd40, df=3) + hn28", "cr(dd40, df=3) + cr(hn28, df=3)", "cr(dd40, df=4) + cr(hn28, df=4)",
          "dd40 + hn28 + I(dd40 * hn28)"):
    m = smf.glm(f"n ~ {f} + C(unit) + year", fs, family=pois, offset=fs.lpop).fit()
    pr = m.predict(d24, offset=d24.lpop).sum()
    rows.append({"heat_terms": f, "AIC_fit": m.aic, "pred24": pr, "obs24": d24.n.sum(), "obs/pred": d24.n.sum() / pr})
S = pd.DataFrame(rows)
S.to_csv(P / "outputs/spline_2024.csv", index=False)
print("\n--- 2024 out-of-sample with flexible dose-response (fit 2014-23 excl. 2020-21, pop offset)")
print(S.round(2).to_string(index=False))
