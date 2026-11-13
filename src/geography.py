"""Constant 2011-Census district geography with complete territory, shared by the exposure builders and the map.

districts_v2.geojson (atlas project) is versioned: when a district was split after 2011, the new district is a separate
row (year 'update2014', '2016_c', ...) and its territory was cut out of the 2011 parent. Selecting the 2011 rows
therefore leaves gaps, both interior holes and gaps on coasts and borders (e.g. Chhattisgarh, Assam, Tamil Nadu,
Saurashtra, Palghar). Census-2011 population belongs to the original district, so the part of each later district not
covered by 2011 districts is given back to the 2011 district sharing the longest border with it.
Telangana: the file has only post-2014 Telangana rows (no 2011 Telangana rows). Their names match only 10 Census
districts, and those carry pre-split populations on post-split boundaries, so all Telangana districts except Hyderabad
(boundary unchanged) get the state's 2011 population (Census, Telangana districts of undivided AP) by area share.
The file also holds unnamed whole-state outline polygons in the 2011 set (e.g. Rajasthan, Bihar, Ladakh); these are
not districts and are dropped (they were previously included with a median population weight).
Muzaffarabad and Mirpur are outside Census 2011: kept for the map, population weight 0.
"""
import pathlib
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import Polygon

A = pathlib.Path(__file__).resolve().parents[2] / "meta_district_injury_atlas_india/data_local"
UNIT = {"Jammu and Kashmir": "J&K & Ladakh", "Ladakh": "J&K & Ladakh",
        "Dadra and Nagar Haveli and Daman and Diu": "DNH & DD", "Andaman and Nicobar Islands": "Andaman & Nicobar"}


def districts(verbose=True):
    g = gpd.read_file(A / "districts_v2.geojson")
    g = g[(g.year == "2011_c") | (g.st_nm == "Telangana")].copy()
    outline = g.district.isna()
    if verbose:
        print(f"geography: dropping {int(outline.sum())} unnamed whole-state outline polygons")
    g = g[~outline].copy()
    g["geometry"] = g.geometry.buffer(0)
    c = pd.read_csv(A / "census2011.csv")
    g["code"] = pd.to_numeric(g.dt_code, errors="coerce")
    g = g.merge(c[["District code", "District name", "Population"]], left_on="code", right_on="District code", how="left")
    miss = g.Population.isna()
    byname = c.assign(k=c["District name"].str.lower().str.strip()).drop_duplicates("k").set_index("k").Population
    g.loc[miss, "Population"] = g.loc[miss, "district"].str.lower().str.strip().map(byname)
    g["pop_imputed"] = g.Population.isna()
    g["Population"] = g.Population.fillna(g.Population.median())
    g = g.reset_index(drop=True)
    g["unit"] = g.st_nm.map(lambda s: UNIT.get(s, s))
    pok = g.district.isin(["Muzaffarabad", "Mirpur"])
    g.loc[pok, "Population"] = 0.0
    TEL11 = {"adilabad", "nizamabad", "karimnagar", "medak", "hyderabad", "rangareddy", "mahbubnagar", "nalgonda",
             "warangal", "khammam"}
    cn = c.assign(k=c["District name"].str.lower().str.replace(" ", ""))
    tel = cn[(cn["State name"].str.upper().str.contains("ANDHRA")) & cn.k.isin(TEL11)]
    assert len(tel) == 10, tel["District name"].tolist()
    t = g.st_nm == "Telangana"
    hyd = t & (g.district.str.lower() == "hyderabad")
    assert hyd.sum() == 1
    hyd_pop = float(tel[tel.k == "hyderabad"].Population.iloc[0])
    area = g[t].to_crs(7755).area
    rest = t & ~hyd
    g.loc[hyd, "Population"] = hyd_pop
    g.loc[rest, "Population"] = (tel.Population.sum() - hyd_pop) * area[rest] / area[rest].sum()
    g.loc[t, "pop_imputed"] = True

    # Territory carved out of 2011 districts after 2011: the part of every later named row (new districts) that no
    # 2011 district covers. This catches gaps on coasts and borders too, which are not interior rings of the union.
    allg = gpd.read_file(A / "districts_v2.geojson")
    later = allg[(allg.year != "2011_c") & (allg.st_nm != "Telangana") & allg.district.notna()].copy()
    later["geometry"] = later.geometry.buffer(0)
    cover = g.union_all()
    pieces = []
    for geo in later.geometry:
        r = geo.difference(cover).buffer(0)
        if not r.is_empty and r.area > 1e-4:
            pieces.extend([q for q in getattr(r, "geoms", [r]) if q.area > 1e-4])
            cover = cover.union(r)
    u = g.union_all()
    pieces += [Polygon(r) for p in getattr(u, "geoms", [u]) for r in p.interiors]       # any remaining interior holes
    if pieces:
        gp = g.to_crs(7755)
        P_ = gpd.GeoDataFrame(geometry=pieces, crs=g.crs).to_crs(7755)
        geoms = list(g.geometry)
        added = 0.0
        for piece, pm in zip(pieces, P_.geometry):
            shared = gp.geometry.boundary.intersection(pm.boundary).length
            parent = int(shared.values.argmax()) if shared.max() > 0 else int(gp.distance(pm).values.argmin())
            geoms[parent] = geoms[parent].union(piece).buffer(0)
            added += pm.area / 1e6
        g["geometry"] = geoms
        if verbose:
            print(f"geography: {len(pieces)} post-2011 pieces ({added:,.0f} km2) returned to their 2011 parent districts")
    u2 = g.union_all()
    left = sum(len(p.interiors) for p in getattr(u2, "geoms", [u2]))
    assert left == 0, f"{left} holes remain"
    return g
