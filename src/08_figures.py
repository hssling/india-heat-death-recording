"""Figures for the manuscript (300-dpi PNG + PDF in figures/).

Fig 1  Map: exposure-adjusted recording index by state (log scale, diverging at 1 = average large state).
Fig 2  Forest plot: index with 95% CrI for the 14 states with >= 50 deaths, main model + four sensitivity variants.
Fig 3  (a) recorded heat/sun-stroke deaths by year; (b) year recording effect (RR, 95% CrI) at fixed heat.
Fig 4  Rotation: index by period (2014-17, 2018-21, 2022-24) for the 14 states; Andhra Pradesh and Chhattisgarh highlighted.
Palette: reference dataviz palette. Categorical slots 1-5 validated (validate_palette.js, light surface: all checks pass;
contrast WARN for slots 3-5 -> markers differ in shape and every series is in the legend). Diverging blue<->red with a
gray midpoint (#f0efec).
"""
import pathlib, sys
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm

P = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
from panel import key  # noqa: E402

F = P / "figures"; F.mkdir(exist_ok=True)
O = P / "outputs"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
DIV = LinearSegmentedColormap.from_list("div", ["#9e1f1f", "#e34948", "#f2a3a2", "#f0efec", "#86b6ef", "#2a78d6", "#104281"])
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 300})
NAME = {"ANDHRA PRADESH": "Andhra Pradesh", "TELANGANA": "Telangana", "PUNJAB": "Punjab", "JHARKHAND": "Jharkhand",
        "ODISHA": "Odisha", "BIHAR": "Bihar", "HARYANA": "Haryana", "MAHARASHTRA": "Maharashtra",
        "UTTAR PRADESH": "Uttar Pradesh", "WEST BENGAL": "West Bengal", "GUJARAT": "Gujarat",
        "CHHATTISGARH": "Chhattisgarh", "RAJASTHAN": "Rajasthan", "MADHYA PRADESH": "Madhya Pradesh"}


def save(fig, name):
    fig.savefig(F / f"{name}.png", bbox_inches="tight")
    fig.savefig(F / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


main = pd.read_csv(O / "bayes_state_index.csv")
big = main[main.deaths >= 50].sort_values("RI_median").reset_index(drop=True)

# ---------------- Fig 1 map (needs the state geometry, derived from district boundaries whose licence does not allow
# redistribution; the public repository ships the rendered figure instead)
if (P / "data/states_2011_complete.geojson").exists():
    st = gpd.read_file(P / "data/states_2011_complete.geojson")   # written by 00_prepare_inputs.py
    st["k"] = st.unit.map(key)
    main["k"] = main.unit.map(key)
    st = st.merge(main[["k", "RI_median", "deaths"]], on="k", how="left")
    assert st.RI_median.isna().sum() == 1, st[st.RI_median.isna()].unit.tolist()          # only A&N (no exposure)
    fig, ax = plt.subplots(figsize=(6.2, 6.6))
    norm = LogNorm(vmin=0.02, vmax=50)
    lo = st[st.deaths < 20]
    hi = st[st.deaths >= 20]
    hi.plot(column="RI_median", cmap=DIV, norm=norm, ax=ax, edgecolor="white", linewidth=0.4)
    lo.plot(column="RI_median", cmap=DIV, norm=norm, ax=ax, edgecolor="white", linewidth=0.4, hatch="////", alpha=0.85)
    st[st.RI_median.isna()].plot(ax=ax, color="#d9d8d2", edgecolor="white", linewidth=0.4)
    for r in st[st.deaths >= 50].itertuples():
        pt = r.geometry.representative_point()
        ax.annotate(f"{r.RI_median:.2f}", (pt.x, pt.y), ha="center", va="center", fontsize=6.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    ax.set_axis_off()
    sm = plt.cm.ScalarMappable(cmap=DIV, norm=norm)
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.01, ticks=[0.02, 0.1, 0.3, 1, 3, 10, 50])
    cb.ax.set_xticklabels(["0.02", "0.1", "0.3", "1", "3", "10", "50"])
    cb.set_label(f"Recording index (log scale; 1 = geometric mean of the {len(big)} states with ≥50 deaths)", color=INK2)
    cb.outline.set_visible(False)
    ax.text(0.0, 0.0, "Hatched: <20 recorded deaths. Grey: no gridded exposure.\nValues shown for states with ≥50 deaths.",
            transform=ax.transAxes, fontsize=6.5, color=INK2, va="bottom")
    save(fig, "fig1_map_recording_index")


else:
    print("state geometry not present: map (figure file) not regenerated")

# ---------------- Fig 2 forest with sensitivity variants
VAR = [("main", "Main model", "o"), ("negbin", "Poisson–gamma", "s"), ("nocovid", "Excluding 2020–21", "^"),
       ("hwdays", "IMD heat-wave days", "D"), ("nomundlak", "No state-mean exposure term", "v")]
fig, ax = plt.subplots(figsize=(6.2, 4.6))
y = np.arange(len(big))
ax.axvline(1, color=MUTED, lw=0.8, zorder=0)
for i, (v, lab, mk) in enumerate(VAR):
    f = O / ("bayes_state_index.csv" if v == "main" else f"bayes_state_index_{v}.csv")
    if not f.exists():
        print("missing variant", v); continue
    dv = pd.read_csv(f).set_index("unit").loc[big.unit]
    off = (i - 2) * 0.13
    if v == "main":
        ax.hlines(y + off, dv.RI_lo, dv.RI_hi, color=CAT[0], lw=2)
    ax.plot(dv.RI_median, y + off, mk, ms=5 if v == "main" else 4, color=CAT[i], mec="white", mew=0.6, label=lab, ls="none")
ax.set_xscale("log")
ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10]); ax.set_xticklabels(["0.1", "0.2", "0.5", "1", "2", "5", "10"])
ax.set_yticks(y); ax.set_yticklabels([NAME[u] for u in big.unit])
ax.xaxis.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.set_xlabel("Recording index (log scale; bar = 95% credible interval, main model)")
ax.legend(frameon=False, fontsize=7, loc="upper left")
for r in big.itertuples():
    ax.text(14, r.Index, f"{int(r.deaths):,}", va="center", fontsize=6.5, color=INK2)
ax.text(14, len(big) - 0.3, "Deaths\n2014–24", fontsize=6.5, color=INK2, va="bottom")
ax.set_xlim(0.07, 22)
save(fig, "fig2_forest_sensitivity")

# ---------------- Fig 3 years
yr = pd.read_csv(O / "bayes_year_effects.csv")
ppc = pd.read_csv(O / "bayes_ppc.csv")
fig, (a, b) = plt.subplots(2, 1, figsize=(6.2, 4.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.1], "hspace": 0.12})
a.bar(ppc.year, ppc.obs, width=0.7, color=CAT[0])
for x, v in zip(ppc.year, ppc.obs):
    a.text(x, v + 30, f"{v:,}", ha="center", fontsize=6.5, color=INK2)
a.set_ylabel("Recorded heatstroke\ndeaths")
a.yaxis.grid(True, color=GRID, lw=0.5); a.set_axisbelow(True)
a.text(0.0, 1.02, "a", transform=a.transAxes, fontweight="bold", fontsize=9)
b.axhline(1, color=MUTED, lw=0.8)
b.vlines(yr.year, yr.RR_lo, yr.RR_hi, color=CAT[1], lw=2)
b.plot(yr.year, yr.RR_median, "o", color=CAT[1], ms=5, mec="white", mew=0.6)
b.set_yscale("log"); b.set_yticks([0.4, 0.6, 1, 1.5, 2]); b.set_yticklabels(["0.4", "0.6", "1", "1.5", "2"])
b.set_ylabel("Year recording effect\n(rate ratio, log scale)")
b.yaxis.grid(True, color=GRID, lw=0.5); b.set_axisbelow(True)
b.set_xticks(yr.year)
b.text(0.0, 1.02, "b", transform=b.transAxes, fontweight="bold", fontsize=9)
save(fig, "fig3_year_effects")

# ---------------- Fig 4 rotation
fig, ax = plt.subplots(figsize=(4.6, 4.6))
xs = [0, 1, 2]
hl = {"ANDHRA PRADESH": CAT[1], "CHHATTISGARH": CAT[0]}
for r in big.itertuples():
    v = [r.RI_2014_17, r.RI_2018_21, r.RI_2022_24]
    c, lw, z = (hl[r.unit], 2, 3) if r.unit in hl else ("#c9c8c1", 1, 1)
    ax.plot(xs, v, "-o", color=c, lw=lw, ms=3.5, zorder=z, mec="white", mew=0.5)
    ax.text(2.06, v[2], NAME[r.unit] + (f"  ×{r.change_2022_24_vs_2014_17:.2f}" if r.unit in hl else ""), va="center",
            fontsize=6.5, color=INK if r.unit in hl else INK2)
ax.set_yscale("log"); ax.set_yticks([0.1, 0.2, 0.5, 1, 2, 5]); ax.set_yticklabels(["0.1", "0.2", "0.5", "1", "2", "5"])
ax.set_xticks(xs); ax.set_xticklabels(["2014–17", "2018–21", "2022–24"]); ax.set_xlim(-0.1, 2.9)
ax.yaxis.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.set_ylabel("Recording index (log scale)")
save(fig, "fig4_rotation")
