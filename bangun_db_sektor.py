"""Langkah 3 - Satu file DuckDB per sektor.

Setiap subfolder di raw/ yang berisi *.parquet (Pangan, Ekonomi, Energi, Sosial,
Bencana, Inflasi, Dimensi, Agregasi) menjadi satu database: db/<sektor>.duckdb
dengan satu tabel per file parquet (nama tabel = nama file).
Ini setara dengan finance_local.duckdb / marketing_local.duckdb pada contoh dosen.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DB_DIR = ROOT / "db"
DB_DIR.mkdir(exist_ok=True)

jumlah_db = 0
for folder in sorted(p for p in RAW.iterdir() if p.is_dir()):
    parquets = sorted(folder.glob("*.parquet"))
    if not parquets:
        print(f"(lewati {folder.name}: tidak ada parquet)")
        continue

    db_file = DB_DIR / f"{folder.name.lower()}.duckdb"
    if db_file.exists():
        db_file.unlink()

    print(f"\n⚡ [{folder.name}] -> {db_file.name}")
    con = duckdb.connect(str(db_file))
    for p in parquets:
        con.execute(f"CREATE TABLE {p.stem} AS SELECT * FROM read_parquet('{p.as_posix()}')")
        n = con.execute(f"SELECT COUNT(*) FROM {p.stem}").fetchone()[0]
        print(f"   {p.stem:32s} {n:>8,} baris")
    con.close()
    jumlah_db += 1

print(f"\n✅ {jumlah_db} database sektor dibuat di {DB_DIR}")
