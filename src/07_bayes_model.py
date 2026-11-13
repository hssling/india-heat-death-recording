"""Main model: Bayesian hierarchical Poisson-lognormal for exposure-adjusted recording of heat-stroke deaths.

  deaths[s,t] ~ Poisson(mu[s,t])
  log mu[s,t] = log pop[s,t] + alpha[s] + delta[s,p(t)] + beta . x[s,t] + gamma[t] + eps[s,t]
  alpha[s]    ~ N(a0 + theta . z[s] + lambda . xbar[s], sigma_alpha)   z = age60, outdoor (state means, standardised)
                                                                       xbar = state-mean exposures (Mundlak: beta is
                                                                       identified within state, as in the FE gates)
  delta[s,p]  ~ N(0, sigma_delta), periods 2014-17, 2018-21, 2022-24  (does the recording leader rotate?)
  gamma[t]    ~ N(0, sigma_gamma), sum-to-zero                        (exchangeable year recording shocks)
  eps[s,t]    ~ N(0, sigma_eps)                                       (overdispersion)
Exposures x (standardised): EXPO below; wet-bulb terms are added only if gate 4 shows a within-state signal.

Recording index, as in gates 3-4: RI[s] = exp(alpha[s] - mean of alpha over states with >= 50 deaths), i.e. recorded
deaths relative to the average large state at the same heat, population and year. alpha deliberately includes the
z and xbar terms: the Mundlak term is between-state heat beyond the within-state slope, which this design reads as
recording (the identifying assumption, stated in the paper). The z terms are reported too, so readers can see how
much of each state's index age structure and outdoor work would account for.
Outputs: outputs/bayes_state_index.csv, outputs/bayes_year_effects.csv, outputs/bayes_summary.csv, outputs/bayes_ppc.csv
"""
import os, pathlib, sys
import numpy as np, pandas as pd
import jax, jax.numpy as jnp
import numpyro, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS, Predictive

numpyro.set_host_device_count(4)
jax.config.update("jax_enable_x64", True)
P = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
# Sensitivity variants (env VARIANT): main | negbin (Poisson-gamma instead of lognormal overdispersion) |
# nocovid (drop 2020-21) | hwdays (IMD heat-wave days + hot nights) | nomundlak (no state-mean exposure term)
VARIANT = os.environ.get("VARIANT", "main")
assert VARIANT in ("main", "negbin", "nocovid", "hwdays", "nomundlak"), VARIANT
SUF = "" if VARIANT == "main" else f"_{VARIANT}"
EXPO = ["hw", "hn28"] if VARIANT == "hwdays" else ["dd40", "hn28"]   # gate 4: wet bulb has no within-state signal
PERIOD = {**{y: 0 for y in range(2014, 2018)}, **{y: 1 for y in range(2018, 2022)}, **{y: 2 for y in range(2022, 2025)}}
SEED = 20261112


def load():
    from panel import build                    # shared assembly (src/panel.py)
    return build()


def model(S, T, NP, s, t, p, X, Xbar, Z, lpop, negbin=False, y=None):
    a0 = numpyro.sample("a0", dist.Normal(-15, 5))
    theta = numpyro.sample("theta", dist.Normal(0, 1).expand([Z.shape[1]]))
    lam = numpyro.sample("lam", dist.Normal(0, 1).expand([Xbar.shape[1]]))
    beta = numpyro.sample("beta", dist.Normal(0, 1).expand([X.shape[1]]))
    s_a = numpyro.sample("sigma_alpha", dist.HalfNormal(2))
    s_d = numpyro.sample("sigma_delta", dist.HalfNormal(1))
    s_g = numpyro.sample("sigma_gamma", dist.HalfNormal(1))
    za = numpyro.sample("za", dist.Normal(0, 1).expand([S]))
    alpha = numpyro.deterministic("alpha", a0 + Z @ theta + Xbar @ lam + s_a * za)
    zd = numpyro.sample("zd", dist.Normal(0, 1).expand([S, NP]))
    delta = numpyro.deterministic("delta", s_d * zd)
    zg = numpyro.sample("zg", dist.Normal(0, 1).expand([T]))
    g = s_g * zg
    gamma = numpyro.deterministic("gamma", g - g.mean())
    eta = lpop + alpha[s] + delta[s, p] + X @ beta + gamma[t]
    if negbin:
        phi = numpyro.sample("phi", dist.HalfNormal(20))
        numpyro.sample("y", dist.NegativeBinomial2(jnp.exp(eta), phi), obs=y)
    else:
        s_e = numpyro.sample("sigma_eps", dist.HalfNormal(1))
        ze = numpyro.sample("ze", dist.Normal(0, 1).expand([len(s)]))
        numpyro.sample("y", dist.Poisson(jnp.exp(eta + s_e * ze)), obs=y)


if __name__ == "__main__":
    d = load()
    if VARIANT == "nocovid":
        d = d[~d.year.isin([2020, 2021])]
    print("VARIANT", VARIANT, "exposures", EXPO, "rows", len(d))
    d = d.sort_values(["unit", "year"]).reset_index(drop=True)
    units = sorted(d.unit.unique()); years = sorted(d.year.unique())
    s = d.unit.map({u: i for i, u in enumerate(units)}).values
    t = d.year.map({y: i for i, y in enumerate(years)}).values
    p = d.year.map(PERIOD).values
    mu_x, sd_x = d[EXPO].mean(), d[EXPO].std()
    X = ((d[EXPO] - mu_x) / sd_x).values
    Xbar = pd.DataFrame(X, columns=EXPO).groupby(s).mean().values
    if VARIANT == "nomundlak":
        Xbar = np.zeros_like(Xbar)
    Zs = d.groupby("unit")[["age60", "outdoor"]].mean().loc[units]
    Z = ((Zs - Zs.mean()) / Zs.std()).values
    args = dict(S=len(units), T=len(years), NP=3, s=s, t=t, p=p, X=X, Xbar=Xbar, Z=Z, lpop=d.lpop.values,
                negbin=VARIANT == "negbin")
    nw, ns = (200, 200) if os.environ.get("QUICK") else (1500, 1500)   # QUICK=1: smoke test only, never for results
    mcmc = MCMC(NUTS(model, target_accept_prob=0.95), num_warmup=nw, num_samples=ns, num_chains=4, progress_bar=False)
    mcmc.run(jax.random.PRNGKey(SEED), y=d.n.values, **args)
    from numpyro.diagnostics import summary
    smry = summary(mcmc.get_samples(group_by_chain=True))
    keys = [k for k in ["a0", "theta", "lam", "beta", "sigma_alpha", "sigma_delta", "sigma_gamma", "sigma_eps", "phi"] if k in smry]
    rows = []
    for k in keys:
        v = smry[k]
        for i in range(np.size(v["mean"])):
            rows.append({"param": k if np.size(v["mean"]) == 1 else f"{k}[{i}]", **{c: float(np.ravel(v[c])[i]) for c in ("mean", "std", "5.0%", "95.0%", "n_eff", "r_hat")}})
    R = pd.DataFrame(rows)
    allr = max(float(np.max(smry[k]["r_hat"])) for k in smry)
    mine = min(float(np.min(smry[k]["n_eff"])) for k in smry)
    ndiv = int(mcmc.get_extra_fields()["diverging"].sum())
    print(R.round(3).to_string(index=False))
    print(f"max r_hat {allr:.3f}; min n_eff {mine:.0f}; divergences {ndiv}")
    (P / "outputs").mkdir(exist_ok=True)
    R.assign(max_rhat_all=allr, min_neff_all=mine, divergences=ndiv).to_csv(P / f"outputs/bayes_summary{SUF}.csv", index=False)

    post = mcmc.get_samples()
    al = np.asarray(post["alpha"])                                   # draws x S
    deaths = d.groupby("unit").n.sum().loc[units]
    ref = np.array([u for u in units if deaths[u] >= 50])
    refi = [units.index(u) for u in ref]
    ri = np.exp(al - al[:, refi].mean(1, keepdims=True))
    dl = np.asarray(post["delta"])                                   # draws x S x 3
    rip = np.exp(al[:, :, None] + dl - (al[:, refi, None] + dl[:, refi, :]).mean(1, keepdims=True))
    rank = (-ri[:, refi]).argsort(1).argsort(1) + 1
    out = pd.DataFrame({"unit": units, "deaths": deaths.values,
                        "RI_median": np.median(ri, 0), "RI_lo": np.quantile(ri, .025, 0), "RI_hi": np.quantile(ri, .975, 0)})
    for k, lab in enumerate(["2014_17", "2018_21", "2022_24"]):
        out[f"RI_{lab}"] = np.median(rip[:, :, k], 0)
    out["P_top3"] = np.nan
    out.loc[out.unit.isin(ref), "P_top3"] = (rank <= 3).mean(0)
    # residual index: alpha net of the age/outdoor terms (recording not attributable to demographic/work structure)
    th = np.asarray(post["theta"])                                   # draws x 2
    ar = al - th @ Z.T
    rr = np.exp(ar - ar[:, refi].mean(1, keepdims=True))
    out["RIresid_median"] = np.median(rr, 0)
    out["RIresid_lo"] = np.quantile(rr, .025, 0); out["RIresid_hi"] = np.quantile(rr, .975, 0)
    # rotation: change in recording between first and last period, relative to the reference-state average
    ch = rip[:, :, 2] / rip[:, :, 0]
    out["change_2022_24_vs_2014_17"] = np.median(ch, 0)
    out["P_decline"] = (ch < 1).mean(0)
    np.savez_compressed(P / f"outputs/bayes_posterior{SUF}.npz", alpha=al, delta=dl, gamma=np.asarray(post["gamma"]),
                        beta=np.asarray(post["beta"]), theta=th, units=np.array(units), years=np.array(years))
    out.sort_values("RI_median").to_csv(P / f"outputs/bayes_state_index{SUF}.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.sort_values("RI_median").round(3).to_string(index=False))
    gm = np.asarray(post["gamma"])
    Y = pd.DataFrame({"year": years, "RR_median": np.median(np.exp(gm), 0), "RR_lo": np.quantile(np.exp(gm), .025, 0),
                      "RR_hi": np.quantile(np.exp(gm), .975, 0)})
    Y.to_csv(P / f"outputs/bayes_year_effects{SUF}.csv", index=False)
    print(Y.round(3).to_string(index=False))
    # mixed replication: redraw the observation-level overdispersion terms (ze) instead of reusing the fitted ones,
    # which would reproduce the data almost exactly and make the check uninformative
    post_mixed = {k: v for k, v in post.items() if k != "ze"}
    pp = np.asarray(Predictive(model, post_mixed)(jax.random.PRNGKey(1), **args)["y"])
    z_obs = (d.n.values == 0).mean(); z_rep = (pp == 0).mean(1)
    print(f"PPC zero unit-years: observed {z_obs:.3f}, replicated median {np.median(z_rep):.3f} "
          f"({np.quantile(z_rep, .025):.3f}-{np.quantile(z_rep, .975):.3f})")
    big_obs = d.n.max(); big_rep = pp.max(1)
    print(f"PPC largest unit-year: observed {big_obs}, replicated median {np.median(big_rep):.0f} "
          f"({np.quantile(big_rep, .025):.0f}-{np.quantile(big_rep, .975):.0f})")
    ppc = pd.DataFrame({"year": years, "obs": d.groupby("year").n.sum().values,
                        "pp_median": [np.median(pp[:, t == i].sum(1)) for i in range(len(years))],
                        "pp_lo": [np.quantile(pp[:, t == i].sum(1), .025) for i in range(len(years))],
                        "pp_hi": [np.quantile(pp[:, t == i].sum(1), .975) for i in range(len(years))]})
    ppc["zero_unit_years_obs"] = z_obs
    ppc["zero_unit_years_rep_median"] = float(np.median(z_rep))
    ppc.to_csv(P / f"outputs/bayes_ppc{SUF}.csv", index=False)
    print(ppc.to_string(index=False))
    print("exposure SDs used for standardisation:", sd_x.round(3).to_dict())
