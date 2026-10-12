# py -u ingest.py
"""Langkah 4 - Gabungkan semua db sektor ke satu DuckLake (motherdb / lake).

Pola sama dengan contoh dosen: katalog bersama `shared_catalog.ducklake`,
data tersimpan di `lakehouse_storage/`, satu schema per sektor.
Sumber: db/<sektor>.duckdb dari bangun_db_sektor.py
Hasil : lake.<sektor>.<tabel>, mis. lake.pangan.fact_harga, lake.agregasi.agg_provinsi_bulan
"""
import os
import shutil
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)                      # path relatif seperti contoh dosen (aman di Windows)

DB_DIR = Path("db")
SHARED_CATALOG = "shared_catalog.ducklake"
STORAGE_DIR = "lakehouse_storage"


def setup_workspace():
    """Hapus katalog & storage lama supaya selalu mulai dari kondisi bersih."""
    for f in [SHARED_CATALOG, SHARED_CATALOG + ".wal"]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(STORAGE_DIR):
        shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR, exist_ok=True)


def init_ducklake(conn: duckdb.DuckDBPyConnection):
    conn.execute("INSTALL ducklake;")
    conn.execute("LOAD ducklake;")
    conn.execute(
        f"""
        ATTACH 'ducklake:{SHARED_CATALOG}' AS lake
        (DATA_PATH '{STORAGE_DIR}/');
    """
    )


def run_sektor(db_file: Path):
    sektor = db_file.stem                       # pangan, ekonomi, energi, ...
    print(f"⚡ [{sektor}] Process Started...")

    conn = duckdb.connect()                     # koneksi sementara (in-memory)
    init_ducklake(conn)
    conn.execute(f"ATTACH '{db_file.as_posix()}' AS src (READ_ONLY);")
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS lake.{sektor};")

    tabel = conn.execute(
        "SELECT table_name FROM duckdb_tables() WHERE database_name = 'src' ORDER BY 1"
    ).fetchall()
    for (t,) in tabel:
        conn.execute(f"CREATE TABLE lake.{sektor}.{t} AS SELECT * FROM src.main.{t};")
        n = conn.execute(f"SELECT COUNT(*) FROM lake.{sektor}.{t}").fetchone()[0]
        print(f"   lake.{sektor}.{t:30s} {n:>8,} baris")

    conn.close()
    print(f"✅ [{sektor}] Complete.")


if __name__ == "__main__":
    db_files = sorted(DB_DIR.glob("*.duckdb"))
    if not db_files:
        raise SystemExit("Tidak ada db/*.duckdb. Jalankan bangun_db_sektor.py dulu.")

    setup_workspace()
    print("=== RUNNING LAKEHOUSE INGESTION ===")

    # berurutan (bukan paralel): katalog DuckLake berbasis file satu penulis
    for f in db_files:
        run_sektor(f)

    print("\n🎉 Ingestion finished successfully!")
