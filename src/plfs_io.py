"""PLFS unit-level loaders (weights per the PLFS READMEs) and the 35-unit state map, copied unchanged from the
occupation-suicide project (meta_occupation_suicide_india/src/02_plfs_denominators.py and 04_build_panel.py), where
they were checked against published PLFS worker shares. Unit-level files are licensed and not redistributed.
"""
import pathlib, zipfile
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
WORK = {11, 12, 21, 31, 41, 51}
ROOT = HERE.parents[1]
RAW = ROOT / "data_raw/microdata/plfs"   # PLFS zips (licensed; obtain from microdata.gov.in)
ROUNDS = {"2017-18": "CSV_PLFS_July2017_June2018.zip", "2018-19": "PLFS_2018_19_CSV.zip",
          "2019-20": "CSV_PLFS_19_20.zip", "2020-21": "CSV_Unit_level_data_PLFS_July2020_June2021.zip",
          "2021-22": "PLFS_Data_2021-22_CSV.zip", "2022-23": "PLFS_2022_23_CSV.zip",
          "2023-24": "CSV_data_PLFS_2023_2024.zip", "CY2024": "PLFS_CY2024_CSV.zip", "CY2025": "PLFS_CY2025_CSV.zip"}
WORK = {11, 12, 21, 31, 41, 51}


def load_cy2025(zip_name):
    """Calendar-year 2025 (redesigned monthly PLFS). README2025: final weight = MULT/100. Summed over all
    12 months this gives the population (1.19 bn), so MULT is already an annual-pooled weight; dividing by
    12 (tried first) gave 0.099 bn and was wrong."""
    z = zipfile.ZipFile(RAW / zip_name)
    d = pd.read_csv(z.open("Data_in_CSV/cperv12025.csv"), dtype=str, low_memory=False)
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    months = num("month").nunique()
    assert months == 12, months
    out = pd.DataFrame({"state": d["st"].str.zfill(2), "sector": num("sec"), "sex": num("sex"), "age": num("age"),
                        "ups": num("pas"), "nic2": num("ind_pas") // 1000, "uss": num("sas"), "nic2_ss": num("ind_sas") // 1000})
    out["w"] = num("mult") / 100
    return out


def load_cy2024(zip_name):
    """Calendar-year 2024 (panel 4, quarters Q3-Q6). README_Calendar_2024:
    final weight = MULT/(NO_QTR*100) if NSS == NSC else MULT/(NO_QTR*200). Columns have long names."""
    z = zipfile.ZipFile(RAW / zip_name)
    d = pd.read_csv(z.open("cperv1.csv"), dtype=str, low_memory=False)
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    nq = num(d.columns[-1])                                                    # State_Sector_Stratum_Substra(tum count of quarters)
    out = pd.DataFrame({"state": d["State_UT_Code"].str.zfill(2), "sector": num("Sector"), "sex": num("Sex"),
                        "age": num("Age"), "ups": num("Principal_Status_Code"), "nic2": num("Principal_Industry_Code") // 1000,
                        "uss": num("Subsidiary_Status_Code"), "nic2_ss": num("Subsidiary_Industry_Code") // 1000})
    nss, nsc = num("Ns_Count_Sector_Stratum_Substratum_Subsample"), num("Ns_Count_Sector_Stratum_Substratum")
    out["w"] = np.where(nss == nsc, num("Subsample_Multiplier") / 100, num("Subsample_Multiplier") / 200) / nq
    return out


def load(zip_name):
    if "CY2025" in zip_name:
        return load_cy2025(zip_name)
    if "CY2024" in zip_name:
        return load_cy2024(zip_name)
    z = zipfile.ZipFile(RAW / zip_name)
    name = next(n for n in z.namelist() if "per" in n.lower() and ("fv" in n.lower() or "v1" in n.lower()))
    d = pd.read_csv(z.open(name), dtype=str, low_memory=False)
    d.columns = [c.rsplit("_per", 1)[0].lower() for c in d.columns]               # strip _per_fv / _perv1
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    out = pd.DataFrame({
        "state": d["state"].str.zfill(2), "sector": num("b1q3"), "sex": num("b4q5"), "age": num("b4q6"),
        "ups": num("b5pt1q3"), "nic2": (num("b5pt1q5") // 1000), "uss": num("b5pt2q3"), "nic2_ss": num("b5pt2q5") // 1000})
    mult, nss, nsc, nq = num("mult"), num("nss"), num("nsc"), num("no_qtr")
    out["w"] = np.where(nss == nsc, mult / 100, mult / 200) / nq
    return out



UNITS = {  # unit: (ADSI names, PLFS codes, population-file name)
    "Andhra Pradesh": (["ANDHRA PRADESH"], ["28"], "Andhra Pradesh"),
    "Arunachal Pradesh": (["ARUNACHAL PRADESH"], ["12"], "Arunachal Pradesh"),
    "Assam": (["ASSAM"], ["18"], "Assam"), "Bihar": (["BIHAR"], ["10"], "Bihar"),
    "Chhattisgarh": (["CHHATTISGARH"], ["22"], "Chhattisgarh"), "Goa": (["GOA"], ["30"], "Goa"),
    "Gujarat": (["GUJARAT"], ["24"], "Gujarat"), "Haryana": (["HARYANA"], ["06"], "Haryana"),
    "Himachal Pradesh": (["HIMACHAL PRADESH"], ["02"], "Himachal Pradesh"),
    "Jharkhand": (["JHARKHAND"], ["20"], "Jharkhand"), "Karnataka": (["KARNATAKA"], ["29"], "Karnataka"),
    "Kerala": (["KERALA"], ["32"], "Kerala"), "Madhya Pradesh": (["MADHYA PRADESH"], ["23"], "Madhya Pradesh"),
    "Maharashtra": (["MAHARASHTRA"], ["27"], "Maharashtra"), "Manipur": (["MANIPUR"], ["14"], "Manipur"),
    "Meghalaya": (["MEGHALAYA"], ["17"], "Meghalaya"), "Mizoram": (["MIZORAM"], ["15"], "Mizoram"),
    "Nagaland": (["NAGALAND"], ["13"], "Nagaland"), "Odisha": (["ODISHA"], ["21"], "Odisha"),
    "Punjab": (["PUNJAB"], ["03"], "Punjab"), "Rajasthan": (["RAJASTHAN"], ["08"], "Rajasthan"),
    "Sikkim": (["SIKKIM"], ["11"], "Sikkim"), "Tamil Nadu": (["TAMIL NADU"], ["33"], "Tamil Nadu"),
    "Telangana": (["TELANGANA"], ["36"], "Telangana"), "Tripura": (["TRIPURA"], ["16"], "Tripura"),
    "Uttar Pradesh": (["UTTAR PRADESH"], ["09"], "Uttar Pradesh"),
    "Uttarakhand": (["UTTARAKHAND"], ["05"], "Uttarakhand"), "West Bengal": (["WEST BENGAL"], ["19"], "West Bengal"),
    "Andaman & Nicobar Islands": (["A & N ISLANDS"], ["35"], "Andaman & Nicobar Islands"),
    "Chandigarh": (["CHANDIGARH"], ["04"], "Chandigarh"), "Delhi": (["DELHI (UT)"], ["07"], "Delhi"),
    "Lakshadweep": (["LAKSHADWEEP"], ["31"], "Lakshadweep"), "Puducherry": (["PUDUCHERRY"], ["34"], "Puducherry"),
    "Jammu & Kashmir + Ladakh": (["JAMMU & KASHMIR", "LADAKH"], ["01", "37"], "Jammu & Kashmir + Ladakh (former J&K state)"),
    "DNH & DD": (["D & N HAVELI", "DAMAN & DIU", "D & N HAVELI AND DAMAN & DIU"], ["25", "26"],
                 "Dadra & Nagar Haveli and Daman & Diu"),
}
