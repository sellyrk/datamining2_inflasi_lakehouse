# ============================================================
# AGREGASI BULANAN: provinsi x bulan (tanpa NaN)
# Aturan:
#   1) dataset yang bulannya tidak lengkap (<12 bulan) / tidak bulanan -> TIDAK diagregasi
#   2) data yang memang tidak ada -> 0 (tidak ada NaN di hasil akhir)
# Jalankan setelah sel konfigurasi (BASE_PATH, RAW_PATH, DB_PATH) dan
# setelah semua fact_*.parquet dibuat.
# ============================================================
import os
import re
import duckdb
import pandas as pd
from pathlib import Path

BASE_PATH = Path(r"D:\KULIAH\MKR TUGAS\SMT 7\DATA MINING II/ducklake")
RAW_PATH = BASE_PATH / "raw"
DB_PATH = BASE_PATH / "database.duckdb"  

KEYS = ["kode_provinsi", "bulan_id"]


def rd(domain, name):
    p = RAW_PATH / domain / f"{name}.parquet"
    return duckdb.read_parquet(str(p)).df()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


# ---------- 1. kerangka lengkap: semua provinsi x 12 bulan ----------
dim_prov = rd("Dimensi", "dim_provinsi")
dim_waktu = rd("Dimensi", "dim_waktu")
grid = (dim_prov[["kode_provinsi", "nama_provinsi"]]
        .merge(dim_waktu[["bulan_id", "tahun", "bulan"]], how="cross"))
BULAN_LENGKAP = set(dim_waktu["bulan_id"])          # 12 bulan 2025


# ---------- 2. cek kelayakan dataset ----------
def layak_bulanan(df, nama):
    """True hanya jika punya kolom kode_provinsi+bulan_id dan mencakup 12 bulan penuh."""
    if not set(KEYS).issubset(df.columns):
        print(f"[SKIP] {nama}: bukan data provinsi x bulan")
        return False
    bln = set(df["bulan_id"].dropna().astype(int))
    if bln != BULAN_LENGKAP:
        print(f"[SKIP] {nama}: bulan tidak lengkap ({len(bln)}/12)")
        return False
    print(f"[OK]   {nama}: 12 bulan lengkap")
    return True


def agg_numerik(df):
    """Satu baris per provinsi x bulan: jumlahkan kolom numerik non-kunci."""
    num = [c for c in df.select_dtypes("number").columns if c not in KEYS]
    return df.groupby(KEYS, as_index=False)[num].sum(min_count=1)


# ---------- 3. kumpulkan dataset ----------
CALON = {                       # nama tabel : (domain)
    "fact_inflasi_yoy": "Inflasi",
    "fact_inflasi_energi": "Energi",
    "fact_bencana_provinsi": "Bencana",
    "fact_bencana_bulanan": "Bencana",
    "fact_tpt": "Ekonomi",
    "fact_tpak": "Ekonomi",
    "fact_ump": "Ekonomi",
    "fact_penduduk": "Sosial",
    "fact_penduduk_miskin": "Sosial",
    "fact_pengeluaran_kapita": "Sosial",
}

agregat = grid.copy()
kolom_nilai = []

# harga pangan: pivot per komoditas
harga = rd("Pangan", "fact_harga")
dim_kom = rd("Pangan", "dim_komoditas")
if layak_bulanan(harga, "fact_harga"):
    h = harga.merge(dim_kom, on="komoditas_id")
    h["kol"] = "harga_" + h["nama_komoditas"].map(slug)
    hp = (h.pivot_table(index=KEYS, columns="kol", values="harga_rp", aggfunc="mean")
            .reset_index())
    hp.columns.name = None
    agregat = agregat.merge(hp, on=KEYS, how="left")
    kolom_harga = [c for c in hp.columns if c.startswith("harga_")]
    # catat dulu berapa komoditas yang memang kosong sebelum diisi 0
    agregat["n_harga_kosong"] = agregat[kolom_harga].isna().sum(axis=1)
    kolom_nilai += kolom_harga

for nama, domain in CALON.items():
    df = rd(domain, nama)
    if not layak_bulanan(df, nama):
        continue
    a = agg_numerik(df)
    a = a.rename(columns={c: f"{slug(nama.replace('fact_', ''))}_{c}"
                          for c in a.columns if c not in KEYS})
    agregat = agregat.merge(a, on=KEYS, how="left")
    kolom_nilai += [c for c in a.columns if c not in KEYS]

# ---------- 4. NaN -> 0 ----------
agregat[kolom_nilai] = agregat[kolom_nilai].fillna(0)
agregat = agregat.sort_values(KEYS).reset_index(drop=True)

assert agregat.isna().sum().sum() == 0, "Masih ada NaN!"
assert agregat.duplicated(KEYS).sum() == 0, "Ada duplikat provinsi x bulan!"
print("\nShape:", agregat.shape, "| NaN:", int(agregat.isna().sum().sum()))
print(agregat.head())

# ---------- 5. simpan ke lake (parquet) + DuckDB ----------
out_dir = RAW_PATH / "Agregasi"
out_dir.mkdir(parents=True, exist_ok=True)
duckdb.sql("SELECT * FROM agregat").write_parquet(str(out_dir / "agg_provinsi_bulan.parquet"))

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB_PATH))
con.register("_agg", agregat)
con.execute("CREATE OR REPLACE TABLE agg_provinsi_bulan AS SELECT * FROM _agg")
con.unregister("_agg")
con.close()
print("Tersimpan: agg_provinsi_bulan ->", DB_PATH)