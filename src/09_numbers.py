"""Collect every number the manuscript reports into outputs/numbers.json, computed from pipeline outputs (never typed).
The manuscript builder fills its text from this file; verify step re-derives and compares.
"""
import json, pathlib, sys
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
O = P / "outputs"
sys.path.insert(0, str(P / "src"))
from panel import build  # noqa: E402

N = {}
d = build(verbose=False)
h = pd.read_csv(P / "data/adsi_heat_deaths_state_year.csv").groupby("year").deaths.sum()
N["deaths_total"] = int(h.sum())
N["deaths_by_year"] = {int(k): int(v) for k, v in h.items()}
N["deaths_mean_per_year"] = round(float(h.mean()), 0)
N["units_modelled"] = int(d.unit.nunique())
N["unit_years"] = int(len(d))
N["units_zero_deaths"] = int((d.groupby("unit").n.sum() == 0).sum())
N["units_ge50"] = int((d.groupby("unit").n.sum() >= 50).sum())
N["share_deaths_14_states_pct"] = round(100 * d.groupby("unit").n.sum().pipe(lambda s: s[s >= 50].sum() / s.sum()), 1)

# gate 2: exposure test and leave-one-year-out
E = pd.read_csv(O / "exposure_test.csv").set_index("exposure")
for x in ("dd40", "hot40", "hn28", "hw"):
    N[f"g2_RRsd_{x}"] = [round(float(E.loc[x, c]), 2) for c in ("RR_per_sd", "lo", "hi")]
    N[f"g2_withinsd_{x}"] = round(float(E.loc[x, "within_sd"]), 1)
N["g2_obs_pred_2024_best"] = round(float(E.loc["dd40 + hn28", "obs/pred_noCOVID"]), 2)
N["g2_obs_pred_2024_range"] = [round(float(E[c].drop("none (FE + trend)").min()), 2) for c in ("obs/pred_noCOVID",)] + \
                              [round(float(E["obs/pred_noCOVID"].drop("none (FE + trend)").max()), 2)]
L = pd.read_csv(O / "loyo_calibration.csv")
l = L[L.exposure == "dd40 + hn28"].set_index("year")["obs/pred"]
N["loyo"] = {int(k): round(float(v), 2) for k, v in l.items()}

# gate 3: state index with covariates
S3 = pd.read_csv(O / "state_index.csv").set_index("unit")
b3 = S3[S3.deaths >= 50]
for k in ("I0_heat_within", "I1_plus_age_outdoor", "I2_relative_heat"):
    v = b3[f"{k}_idx"]
    N[f"g3_{k}_fold"] = round(float(v.max() / v.min()), 1)
    N[f"g3_{k}_sdlog"] = round(float(np.log(v).std()), 2)
N["g3_sd_kept_I1_pct"] = round(100 * N["g3_I1_plus_age_outdoor_sdlog"] / N["g3_I0_heat_within_sdlog"])
N["g3_sd_kept_I2_pct"] = round(100 * N["g3_I2_relative_heat_sdlog"] / N["g3_I0_heat_within_sdlog"])
Sp = pd.read_csv(O / "spline_2024.csv")
N["g3_spline_obs_pred_range"] = [round(float(Sp["obs/pred"].min()), 1), round(float(Sp["obs/pred"].max()), 1)]

# gate 4: humidity
H = pd.read_csv(O / "humidity_gate.csv").set_index("unit")
hb = H[H.deaths >= 50]
ref = np.log(hb["dry_within (gate-3 I0)"]).std()
N["g4_sd_kept_pct"] = [round(100 * float(np.log(hb[c]).std() / ref)) for c in ("W0 wet_within", "W1 wet_between + cov", "W2 wet-only_between + cov")]
N["g4_AP_MP"] = [round(float(hb.loc["ANDHRA PRADESH", c] / hb.loc["MADHYA PRADESH", c]), 1) for c in ("W0 wet_within", "W1 wet_between + cov", "W2 wet-only_between + cov")]
N["g4_PB_MP"] = [round(float(hb.loc["PUNJAB", c] / hb.loc["MADHYA PRADESH", c]), 1) for c in ("W0 wet_within", "W1 wet_between + cov", "W2 wet-only_between + cov")]
H24 = pd.read_csv(O / "humidity_2024.csv")
N["g4_obs_pred_2024_range"] = [round(float(H24["obs/pred"].min()), 1), round(float(H24["obs/pred"].max()), 1)]

# main Bayesian model
B = pd.read_csv(O / "bayes_summary.csv").set_index("param")
N["diag"] = {"max_rhat": round(float(B.max_rhat_all.iloc[0]), 3), "min_neff": int(B.min_neff_all.iloc[0]),
             "divergences": int(B.divergences.iloc[0])}
for k in ("sigma_alpha", "sigma_delta", "sigma_gamma"):
    N[k] = [round(float(B.loc[k, c]), 2) for c in ("mean", "5.0%", "95.0%")]
post = np.load(O / "bayes_posterior.npz")          # written by 07; string arrays are fixed-width unicode, no pickle
beta = post["beta"]
sd = d[["dd40", "hn28"]].std()
N["beta_RR_per_sd"] = {x: [round(float(np.exp(np.median(beta[:, i]))), 2), round(float(np.exp(np.quantile(beta[:, i], .025))), 2),
                           round(float(np.exp(np.quantile(beta[:, i], .975))), 2)] for i, x in enumerate(["dd40", "hn28"])}
N["exposure_sd"] = {x: round(float(sd[x]), 1) for x in ("dd40", "hn28")}
th = post["theta"]
N["theta_outdoor"] = [round(float(np.median(th[:, 1])), 2), round(float(np.quantile(th[:, 1], .025)), 2), round(float(np.quantile(th[:, 1], .975)), 2)]
N["theta_age60"] = [round(float(np.median(th[:, 0])), 2), round(float(np.quantile(th[:, 0], .025)), 2), round(float(np.quantile(th[:, 0], .975)), 2)]
SI = pd.read_csv(O / "bayes_state_index.csv").set_index("unit")
N["index"] = {u: {"ri": [round(float(r.RI_median), 2), round(float(r.RI_lo), 2), round(float(r.RI_hi), 2)],
                  "resid": [round(float(r.RIresid_median), 2), round(float(r.RIresid_lo), 2), round(float(r.RIresid_hi), 2)],
                  "periods": [round(float(r.RI_2014_17), 2), round(float(r.RI_2018_21), 2), round(float(r.RI_2022_24), 2)],
                  "change": round(float(r.change_2022_24_vs_2014_17), 2), "p_decline": round(float(r.P_decline), 3),
                  "p_top3": None if pd.isna(r.P_top3) else round(float(r.P_top3), 3), "deaths": int(r.deaths)}
              for u, r in SI.iterrows()}
big = SI[SI.deaths >= 50]
N["fold_top_bottom"] = round(float(big.RI_median.max() / big.RI_median.min()), 1)
N["top_state"], N["bottom_state"] = big.RI_median.idxmax(), big.RI_median.idxmin()
r = SI.RIresid_median[big.index]
N["resid_fold"] = round(float(r.max() / r.min()), 1)
Y = pd.read_csv(O / "bayes_year_effects.csv").set_index("year")
N["year_RR"] = {int(y): [round(float(v.RR_median), 2), round(float(v.RR_lo), 2), round(float(v.RR_hi), 2)] for y, v in Y.iterrows()}
N["year_swing"] = round(float(Y.RR_median.max() / Y.RR_median.min()), 1)
pp = pd.read_csv(O / "bayes_ppc.csv")
N["ppc_years_covered"] = int(((pp.obs >= pp.pp_lo) & (pp.obs <= pp.pp_hi)).sum())
N["ppc_zero_obs"] = round(float(pp.zero_unit_years_obs.iloc[0]), 3)
N["ppc_zero_rep"] = round(float(pp.zero_unit_years_rep_median.iloc[0]), 3)

# sensitivity
sens = {}
for v in ("negbin", "nocovid", "hwdays", "nomundlak"):
    t = pd.read_csv(O / f"bayes_state_index_{v}.csv").set_index("unit").loc[big.index]
    sm = pd.read_csv(O / f"bayes_summary_{v}.csv")
    sens[v] = {"fold": round(float(t.RI_median.max() / t.RI_median.min()), 1),
               "rank_corr": round(float(t.RI_median.rank().corr(big.RI_median.rank())), 3),
               "AP_change": round(float(t.loc["ANDHRA PRADESH", "change_2022_24_vs_2014_17"]), 2),
               "AP_p_decline": round(float(t.loc["ANDHRA PRADESH", "P_decline"]), 3),
               "max_rhat": round(float(sm.max_rhat_all.iloc[0]), 3), "divergences": int(sm.divergences.iloc[0])}
N["sensitivity"] = sens

# anchors (sources cited in docs/killcheck_report.md)
MDS = {"extreme_hot_2015": 25100, "lo": 15400, "hi": 33200, "all_hot_2015": 25100 + 63600}
N["mds"] = MDS
N["ncrb_share_of_mds_2015_pct"] = [round(100 * N["deaths_by_year"][2015] / MDS[k], 1) for k in ("extreme_hot_2015", "hi", "lo")]
N["ncrb_share_of_mds_mean_pct"] = [round(100 * float(h.mean()) / MDS[k], 1) for k in ("extreme_hot_2015", "hi", "lo")]
nc = pd.read_csv(P / "data/ncdc_hri_national_2021_2024.csv")
N["ncdc"] = nc.to_dict(orient="records")

# derived facts that the text states in words (each backs a sentence; see 10_build_manuscript.py asserts)
tot = d.groupby("unit").n.sum()
N["units_ge20"] = int((tot >= 20).sum())
ex = pd.read_csv(O / "obs_pred_2024_by_unit.csv").sort_values("excess", ascending=False)
pos = ex[ex.excess > 0]
N["excess24_top5"] = ex.unit.head(5).tolist()
N["excess24_top5_share_pct"] = round(float(100 * pos.excess.head(5).sum() / pos.excess.sum()), 0)
N["excess24_shortfall"] = ex.sort_values("excess").unit.iloc[0]
N["excess24_shortfall_n"] = [int(ex.sort_values("excess").n.iloc[0]), round(float(ex.sort_values("excess").pred.iloc[0]))]
nat = d.groupby("year")[["dd40", "hn28"]].mean()
N["hn28_2024_is_max"] = bool(nat.hn28.idxmax() == 2024)
N["dd40_2024_rank"] = int(nat.dd40.rank(ascending=False)[2024])
dm = d.groupby("unit").dd40.mean().rank(ascending=False)
N["delhi_dd40_rank"] = int(dm["DELHI (UT)"])
N["delhi_dd40_mean"] = round(float(d[d.unit == "DELHI (UT)"].dd40.mean()))
Yr = pd.read_csv(O / "bayes_year_effects.csv").set_index("year").RR_median
N["year_max"], N["year_min"] = int(Yr.idxmax()), int(Yr.idxmin())
p1 = {u: v["periods"][0] for u, v in N["index"].items() if v["deaths"] >= 50}
N["top_state_2014_17"] = max(p1, key=p1.get)
low = {u: v["ri"][0] for u, v in N["index"].items() if v["deaths"] >= 10}
N["lowest_recorders_ge10_deaths"] = sorted(low, key=low.get)[:5]
N["nw_dd40"] = {u: round(float(d[d.unit == u].dd40.mean())) for u in ("PUNJAB", "HARYANA", "RAJASTHAN", "MADHYA PRADESH", "DELHI (UT)")}
N["g2_null_exposures"] = [x for x in ("hot40", "hw", "hwspell", "shw", "wn", "hn28", "dd40", "tmax_dep", "tmin_dep")
                          if pd.read_csv(O / "exposure_test.csv").set_index("exposure").loc[x, "lo"] <= 1]

# posterior credible intervals for the headline ratios (from the saved draws, not ratios of medians)
units_post = [str(u) for u in post["units"]]
years_post = [int(y) for y in post["years"]]
al, gm, dl = post["alpha"], post["gamma"], post["delta"]
def q3(x): return [round(float(np.median(x)), 2), round(float(np.quantile(x, .025)), 2), round(float(np.quantile(x, .975)), 2)]
iu = units_post.index
N["ratio_top_bottom_post"] = q3(np.exp(al[:, iu(N["top_state"])] - al[:, iu(N["bottom_state"])]))
yi = years_post.index
N["ratio_year_max_min_post"] = q3(np.exp(gm[:, yi(N["year_max"])] - gm[:, yi(N["year_min"])]))
N["ratio_2024_vs_min_post"] = q3(np.exp(gm[:, yi(2024)] - gm[:, yi(N["year_min"])]))
a = iu("ANDHRA PRADESH")
ref = [iu(u) for u, v in N["index"].items() if v["deaths"] >= 50]
r1 = al[:, a] + dl[:, a, 0] - (al[:, ref] + dl[:, ref, 0]).mean(1)
r3 = al[:, a] + dl[:, a, 2] - (al[:, ref] + dl[:, ref, 2]).mean(1)
N["ap_change_post"] = q3(np.exp(r3 - r1))
N["sigma_alpha_fold"] = round(float(np.exp(N["sigma_alpha"][0])), 1)

(O / "numbers.json").write_text(json.dumps(N, indent=1, default=str), encoding="utf-8")
print("wrote", len(N), "top-level entries")
for k in ("deaths_total", "fold_top_bottom", "top_state", "bottom_state", "year_swing", "diag", "sigma_alpha", "beta_RR_per_sd",
          "ncrb_share_of_mds_2015_pct", "g2_obs_pred_2024_best", "resid_fold"):
    print(k, N[k])
