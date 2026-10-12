# Langkah 1: cek hasil agregasi
import duckdb
con = duckdb.connect(r"D:\KULIAH\MKR TUGAS\SMT 7\DATA MINING II\ducklake\database.duckdb")
print(con.sql("SELECT bulan_id, COUNT(*) n FROM agg_provinsi_bulan GROUP BY 1 ORDER BY 1"))  # 39 per bulan
print(con.sql("SELECT * FROM agg_provinsi_bulan WHERE kode_provinsi = 64 LIMIT 3"))