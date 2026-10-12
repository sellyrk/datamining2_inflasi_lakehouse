# DM2 – Lakehouse Inflasi & Faktor Pendukung per Provinsi (2025)

Pipeline data engineering berbasis **DuckDB / DuckLake** untuk data BPS 2025
(pangan, ekonomi, energi, sosial, bencana, inflasi), disusun per **provinsi × bulan**.

## Arsitektur

```
raw/<Sektor>/*.xlsx            -> data mentah (BPS)
        │  notebooks/DM2_AGREGASI.ipynb (ETL xlsx -> parquet, dim & fact)
        ▼
raw/<Sektor>/*.parquet         -> dimensi & fakta per sektor
        │  bencana_bulanan.py  (bencana bulanan dari xlsx)
        │  agregasi.py         (agregasi provinsi × bulan, tanpa NaN)
        ▼
db/<sektor>.duckdb             -> satu database per sektor (bangun_db_sektor.py)
        │  ingest.py
        ▼
shared_catalog.ducklake        -> DuckLake (motherdb): lake.<sektor>.<tabel>
lakehouse_storage/
```

## Aturan agregasi
- Dataset dengan bulan **tidak lengkap** (TPT/TPAK semesteran, penduduk miskin
  Maret/September, UMP & penduduk tahunan, upah triwulanan) **tidak** ikut agregasi bulanan.
- Hasil agregasi **tidak berisi NaN**: data yang memang tidak ada diisi `0`.
- Kolom `n_harga_kosong` menandai berapa komoditas yang tidak tercatat di suatu provinsi
  (harga 0 = tidak tercatat, bukan harga nol).

## Cara menjalankan
```powershell
py -m pip install -U duckdb pandas pyarrow openpyxl
py run_all.py          # semua langkah berurutan
```
Atau satu per satu:
```powershell
py bencana_bulanan.py
py agregasi.py
py bangun_db_sektor.py
py -u ingest.py
py verifikasi.py
```
> Butuh internet saat pertama kali (menginstal ekstensi `ducklake`).
> File parquet awal dibuat oleh notebook `notebooks/DM2_AGREGASI.ipynb`.

## Hasil
Tabel utama: `lake.agregasi.agg_provinsi_bulan` (39 wilayah × 12 bulan).
Contoh:
```sql
SELECT nama_provinsi, bulan_id, harga_beras
FROM lake.agregasi.agg_provinsi_bulan
WHERE kode_provinsi = 64 ORDER BY bulan_id;
```
