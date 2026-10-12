"""Jalankan seluruh pipeline lakehouse secara berurutan:  py run_all.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGKAH = [
    "bencana_bulanan.py",     # 2. bencana bulanan -> parquet
    "agregasi.py",            # agregasi provinsi x bulan tanpa NaN
    "bangun_db_sektor.py",    # 3. db per sektor
    "ingest.py",              # 4. DuckLake (motherdb)
    "verifikasi.py",          # cek hasil
]

for f in LANGKAH:
    print("\n" + "=" * 70 + f"\n>>> {f}\n" + "=" * 70, flush=True)
    r = subprocess.run([sys.executable, "-u", str(ROOT / f)], cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"\n❌ Berhenti: {f} gagal (kode {r.returncode})")

print("\n🎉 Semua langkah selesai.")
