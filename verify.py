"""Independent check of the manuscript against the pipeline outputs.

Recomputes the reported numbers directly from the raw output tables (NOT from outputs/numbers.json, which the
manuscript builder used) and checks that each expected string appears in manuscript/01_manuscript.md, matched on
number boundaries so that "4.8" cannot match "14.89". Exit code 1 on any failure.
Usage: python verify.py            (against manuscript/01_manuscript.md, or results/expected_key_results.json if absent)
       python verify.py --freeze   (monorepo: write the published strings to results/expected_key_results.json)
Mutation self-test: python verify.py --selftest (alters one number in a copy and requires a failure).
"""
import pathlib, re, sys
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parent
O = P / "outputs"


def expected():
    E = []
    by = pd.read_csv(P / "data/adsi_heat_deaths_state_year.csv").groupby("year").deaths.sum()
    E += [("total recorded deaths", f"{by.sum():,}"), ("2015 deaths", f"{by[2015]:,}"), ("2024 deaths", f"{by[2024]:,}"),
          ("2023 deaths", f"{by[2023]:,}"), ("minimum annual deaths", f"{by.min():,}")]
    S = pd.read_csv(O / "bayes_state_index.csv").set_index("unit")
    big = S[S.deaths >= 50]
    E += [("number of large states", f"{len(big)} states with at least 50"),
          ("top/bottom fold", f"{big.RI_median.max() / big.RI_median.min():.0f}-fold"),
          ("Punjab index", f"{S.loc['PUNJAB', 'RI_median']:.2f} ({S.loc['PUNJAB', 'RI_lo']:.2f}–{S.loc['PUNJAB', 'RI_hi']:.2f})"),
          ("Madhya Pradesh index", f"{S.loc['MADHYA PRADESH', 'RI_median']:.2f} ({S.loc['MADHYA PRADESH', 'RI_lo']:.2f}–{S.loc['MADHYA PRADESH', 'RI_hi']:.2f})"),
          ("Delhi index", f"{S.loc['DELHI (UT)', 'RI_median']:.2f}"),
          ("AP change", f"{S.loc['ANDHRA PRADESH', 'change_2022_24_vs_2014_17']:.2f} times"),
          ("AP P(decline)", f"{S.loc['ANDHRA PRADESH', 'P_decline']:.3f}"),
          ("AP 2014-17", f"{S.loc['ANDHRA PRADESH', 'RI_2014_17']:.2f}"), ("AP 2022-24", f"{S.loc['ANDHRA PRADESH', 'RI_2022_24']:.2f}")]
    for u in big.index:                                                  # every Table 1 row
        r = S.loc[u]
        E.append((f"Table 1 {u}", f"{int(r.deaths):,} | ", f"{r.RI_median:.2f} ({r.RI_lo:.2f}–{r.RI_hi:.2f}) | "
                  f"{r.RIresid_median:.2f} ({r.RIresid_lo:.2f}–{r.RIresid_hi:.2f}) | {r.RI_2014_17:.2f} | {r.RI_2022_24:.2f} | {r.P_decline:.2f} |"))
    Y = pd.read_csv(O / "bayes_year_effects.csv").set_index("year").RR_median
    E += [("year swing", f"{Y.max() / Y.min():.1f}-fold"), ("2024 year effect", f"{Y[2024]:.2f}")]
    X = pd.read_csv(O / "exposure_test.csv").set_index("exposure")
    E += [("2024 obs/pred best exposure", f"{X.loc['dd40 + hn28', 'obs/pred_noCOVID']:.2f} times")]
    L = pd.read_csv(O / "loyo_calibration.csv")
    l = L[L.exposure == "dd40 + hn28"].set_index("year")["obs/pred"]
    E += [("LOYO 2015", f"{l[2015]:.2f} times the prediction in 2015"), ("LOYO 2022", f"{l[2022]:.2f} in 2022")]
    mds = 25100
    E += [("MDS share 2015", f"{100 * by[2015] / mds:.1f}%"), ("MDS share mean", f"{100 * by.mean() / mds:.1f}%"),
          ("MDS share mean (abstract)", f"about {100 * by.mean() / mds:.0f}%")]
    nc = pd.read_csv(P / "data/ncdc_hri_national_2021_2024.csv").set_index("year")
    E += [("NCDC 2023", f"2023 ({int(nc.loc[2023, 'ncdc_confirmed_heatstroke_deaths'])})"),
          ("NCDC 2024", f"to 28 July, {int(nc.loc[2024, 'ncdc_confirmed_heatstroke_deaths'])}")]
    for v in ("negbin", "nocovid", "hwdays", "nomundlak", "main"):
        sm = pd.read_csv(O / ("bayes_summary.csv" if v == "main" else f"bayes_summary_{v}.csv"))
        assert sm.divergences.iloc[0] == 0 and sm.max_rhat_all.iloc[0] < 1.01, f"convergence failure in {v}"
    return E


def check(text, E):
    bad = []
    for item in E:
        label, *needles = item
        for nd in needles:
            pat = (r"(?<![\d.])" if nd[:1].isdigit() else "") + re.escape(nd) + (r"(?![\d])" if nd[-1:].isdigit() else "")
            if not re.search(pat, text):
                bad.append((label, nd))
    return bad


if __name__ == "__main__":
    import json
    E = expected()
    ms = P / "manuscript/01_manuscript.md"
    frozen = P / "results/expected_key_results.json"
    if "--freeze" in sys.argv:              # monorepo: record the published strings (each must be in the manuscript)
        text = ms.read_text(encoding="utf-8")
        bad = check(text, E)
        assert not bad, bad
        frozen.parent.mkdir(exist_ok=True)
        frozen.write_text(json.dumps({"_note": "Strings as printed in the manuscript; verify.py recomputes each from outputs/ "
                                      "and data/ and requires it here.", "strings": [n for item in E for n in item[1:]]},
                                     indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"froze {sum(len(i) - 1 for i in E)} strings to {frozen.relative_to(P)}"); sys.exit(0)
    if ms.exists():
        text = ms.read_text(encoding="utf-8")
    else:                                   # public repository: no manuscript, check against the frozen published strings
        text = "\n".join(json.loads(frozen.read_text(encoding="utf-8"))["strings"])
    if "--selftest" in sys.argv:
        S = pd.read_csv(O / "bayes_state_index.csv").set_index("unit")
        target = f"{S.loc['PUNJAB', 'RI_median']:.2f}"
        mutated = text.replace(target, f"{S.loc['PUNJAB', 'RI_median'] + 0.01:.2f}")
        assert mutated != text
        base = set(check(text, E))
        assert not base, f"self-test needs a clean manuscript first; failing: {sorted(base)}"
        new = [b for b in check(mutated, E) if b not in base]
        print("self-test:", "PASS (mutation detected by: " + ", ".join(sorted({b[0] for b in new})) + ")" if new
              else "FAIL (mutation not detected)")
        sys.exit(0 if new else 1)
    bad = check(text, E)
    n = sum(len(i) - 1 for i in E)
    print(f"{n - len(bad)}/{n} checks passed")
    for b in bad:
        print("  MISSING:", b[0], "->", repr(b[1]))
    sys.exit(1 if bad else 0)
