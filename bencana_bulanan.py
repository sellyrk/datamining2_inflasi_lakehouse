"""Langkah 2 - Bencana bulanan per provinsi.

Membaca raw/Bencana/data_bencana_dampak_spesifik_2025.xlsx
dan menulis raw/Bencana/fact_bencana_bulanan.parquet
(kode_provinsi x bulan_id, bulan tanpa bencana TIDAK ada barisnya -> nanti diisi 0 oleh agregasi.py).
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
TAHUN = 2025
KEYS = ["kode_provinsi", "bulan_id"]

BULAN_NAMA = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_MAP = {n.lower(): i for i, n in enumerate(BULAN_NAMA, 1)}
BULAN_MAP.update({n.lower()[:3]: i for i, n in enumerate(BULAN_NAMA, 1)})
BULAN_MAP["ags"] = 8

ALIAS = {
    "SEMUA PROVINSI": "INDONESIA",
    "DAERAH ISTIMEWA YOGYAKARTA": "DI YOGYAKARTA",
    "D I YOGYAKARTA": "DI YOGYAKARTA",
    "DAERAH KHUSUS IBUKOTA JAKARTA": "DKI JAKARTA",
    "BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
}


def norm_name(s):
    s = str(s).upper()
    s = re.sub(r"^\s*\d+\s+", "", s)
    s = re.sub(r"^\s*(PROVINSI|PROV)\b\.?\s*", "", s)
    s = re.sub(r"\bKEP\b\.?", "KEPULAUAN", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIAS.get(s, s)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def to_num(s):
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    x = s.astype(str).str.strip().str.replace(",", "", regex=False)
    x = x.replace({"-": np.nan, "–": np.nan, "—": np.nan, "": np.nan, "nan": np.nan})
    return pd.to_numeric(x, errors="coerce")


def cari(df, kata):
    for c in df.columns:
        if kata in str(c).lower():
            return c
    raise KeyError(f"kolom berisi '{kata}' tidak ditemukan. Kolom: {list(df.columns)}")


# ---------- dimensi provinsi ----------
dim_path = next(RAW.rglob("dim_provinsi.parquet"))
dim = pd.read_parquet(dim_path)
KEY2KODE = dict(zip(dim["nama_provinsi"].map(norm_name), dim["kode_provinsi"]))

# ---------- baca xlsx ----------
src_path = next(RAW.rglob("data_bencana_dampak_spesifik*.xlsx"))
src = pd.read_excel(src_path)
print("Sumber:", src_path.name, src.shape)

d = pd.DataFrame({
    "nama_wilayah": src[cari(src, "provinsi")],
    "bulan": src[cari(src, "bulan")].astype(str).str.strip().str.lower().map(BULAN_MAP),
    "tahun": pd.to_numeric(src[cari(src, "tahun")], errors="coerce").fillna(TAHUN).astype(int),
    "jenis": src[cari(src, "jenis")].astype(str).str.strip(),
    "jumlah_kejadian": to_num(src[cari(src, "kejadian")]),
    "korban_meninggal": to_num(src[cari(src, "meninggal")]),
    "korban_hilang": to_num(src[cari(src, "hilang")]),
    "korban_luka": to_num(src[cari(src, "luka")]),
    "korban_terdampak": to_num(src[cari(src, "terdampak")]),
    "korban_mengungsi": to_num(src[cari(src, "mengungsi")]),
    "rumah_rusak": to_num(src[cari(src, "rumah")]),
})

n_bln_salah = int(d["bulan"].isna().sum())
if n_bln_salah:
    print(f"[bencana] {n_bln_salah} baris bulan tidak terbaca, dibuang")
d = d.dropna(subset=["bulan"])
d["bulan_id"] = d["tahun"] * 100 + d["bulan"].astype(int)

# ---------- nama provinsi -> kode ----------
d["kode_provinsi"] = d["nama_wilayah"].map(norm_name).map(KEY2KODE)
tak = sorted(d.loc[d["kode_provinsi"].isna(), "nama_wilayah"].astype(str).unique())
if tak:
    print(f"[bencana] {len(tak)} nama tidak cocok, dibuang: {tak}")
d = d.dropna(subset=["kode_provinsi"])
d["kode_provinsi"] = d["kode_provinsi"].astype(int)
d = d[d["kode_provinsi"] != 0]          # baris nasional (kalau ada) dihitung ulang di bawah

# ---------- total per provinsi x bulan ----------
METRIK = ["jumlah_kejadian", "korban_meninggal", "korban_hilang", "korban_luka",
          "korban_terdampak", "korban_mengungsi", "rumah_rusak"]
bulanan = d.groupby(KEYS, as_index=False)[METRIK].sum()

# jumlah kejadian per jenis bencana (banjir, longsor, karhutla, dst.)
pj = d.pivot_table(index=KEYS, columns="jenis", values="jumlah_kejadian",
                   aggfunc="sum", fill_value=0)
pj.columns = ["kejadian_" + slug(c) for c in pj.columns]
bulanan = bulanan.merge(pj.reset_index(), on=KEYS, how="left")

# ---------- baris nasional (kode 0) = jumlah seluruh provinsi ----------
nas = bulanan.drop(columns="kode_provinsi").groupby("bulan_id", as_index=False).sum()
nas.insert(0, "kode_provinsi", 0)
fact = pd.concat([nas, bulanan], ignore_index=True).sort_values(KEYS).reset_index(drop=True)

out = RAW / "Bencana" / "fact_bencana_bulanan.parquet"
out.parent.mkdir(parents=True, exist_ok=True)
fact.to_parquet(out, index=False)

print("Bulan tercakup:", sorted(fact["bulan_id"].unique()))
print(f"Tersimpan: {out}  ({len(fact)} baris, {fact.shape[1]} kolom)")
