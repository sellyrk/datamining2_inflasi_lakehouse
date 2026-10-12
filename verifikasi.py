"""Verifikasi lake: daftar tabel, jumlah baris, 39 wilayah per bulan, tanpa NaN."""
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

con = duckdb.connect()
con.execute("INSTALL ducklake;")
con.execute("LOAD ducklake;")
con.execute("ATTACH 'ducklake:shared_catalog.ducklake' AS lake (DATA_PATH 'lakehouse_storage/');")

print("=== ISI LAKE ===")
tabel = con.execute(
    "SELECT schema_name, table_name FROM duckdb_tables() "
    "WHERE database_name = 'lake' ORDER BY 1, 2"
).fetchall()
for s, t in tabel:
    n = con.execute(f"SELECT COUNT(*) FROM lake.{s}.{t}").fetchone()[0]
    print(f"lake.{s}.{t:32s} {n:>8,} baris")

print("\n=== CEK AGREGASI ===")
per_bulan = con.execute(
    "SELECT bulan_id, COUNT(*) FROM lake.agregasi.agg_provinsi_bulan GROUP BY 1 ORDER BY 1"
).fetchall()
assert len(per_bulan) == 12 and all(n == 39 for _, n in per_bulan), f"tidak 12 x 39: {per_bulan}"
print("OK: 12 bulan x 39 wilayah")

df = con.execute("SELECT * FROM lake.agregasi.agg_provinsi_bulan").df()
n_nan = int(df.isna().sum().sum())
assert n_nan == 0, f"masih ada {n_nan} NaN"
print(f"OK: tidak ada NaN ({df.shape[0]} baris x {df.shape[1]} kolom)")

print("\n=== CONTOH QUERY (Kalimantan Timur, kode 64) ===")
print(con.execute(
    "SELECT nama_provinsi, bulan_id, harga_beras "
    "FROM lake.agregasi.agg_provinsi_bulan WHERE kode_provinsi = 64 ORDER BY bulan_id LIMIT 5"
).df())
