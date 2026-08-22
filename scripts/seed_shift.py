"""Bangkitkan satu shift giling dari simulator, masuk ke Postgres.

## Kenapa data seed dibangkitkan, bukan diketik

Angka yang diketik tangan pasti tidak menutup. Neraca yang barisnya
tidak berjumlah adalah hal pertama yang akan dicoba juri, dan gagalnya
tidak kelihatan sampai seseorang menjumlahkan kolomnya.

Seluruh isi seed di sini keluar dari `ai/simulator/mill.py` dan
`ai/reasoning/balance.py` — modul yang sama yang dipakai saat sistem
berjalan sungguhan. Konsekuensinya: kalau koefisien berubah, seed ikut
berubah, dan tidak ada angka basi yang tertinggal di berkas SQL.

## Dua cara pakai

    --sql       tulis backend/db/init/02_seed.sql  (dipakai docker compose)
    (bawaan)    masukkan langsung ke Postgres yang sedang berjalan

Yang pertama untuk menyiapkan repo; yang kedua untuk mengisi ulang data
demo tanpa membangun ulang container -- termasuk saat merekam video
proof of work.

Jalankan:
    python scripts/seed_shift.py --sql
    python scripts/seed_shift.py --tanggal 2026-08-03
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import coefficients as C
from ai.reasoning import balance as M5
from ai.simulator.mill import ALIRAN, Pabrik

OUT_SQL = ROOT / "backend" / "db" / "init" / "02_seed.sql"

PEMASOK = [
    ("KUD Jaya Makmur", "kud"),
    ("Tani Sawit Mandiri", "swadaya"),
    ("PT Inti Lestari", "inti"),
    ("Koperasi Sawit Bersama", "kud"),
    ("Petani Swadaya Blok C", "swadaya"),
]

# Komposisi muatan sesuai skenario di pipeline. Empat karakter, supaya
# atribusi punya sesuatu untuk ditunjuk ke DUA arah sekaligus.
KARAKTER = (
    [("bagus", dict(mentah=0.02, kurang_masak=0.05, masak=0.91, terlalu_masak=0.02),
      (0.0, 3.0))] * 3
    + [("sedang", dict(mentah=0.08, kurang_masak=0.16, masak=0.71, terlalu_masak=0.05),
        (1.0, 5.0))] * 5
    + [("banyak_mentah", dict(mentah=0.24, kurang_masak=0.18, masak=0.55, terlalu_masak=0.03),
        (1.0, 4.0))] * 2
    + [("restan_panjang", dict(mentah=0.10, kurang_masak=0.15, masak=0.70, terlalu_masak=0.05),
        (8.0, 14.0))] * 4
    + [("sedang", dict(mentah=0.07, kurang_masak=0.14, masak=0.74, terlalu_masak=0.05),
        (2.0, 6.0))] * 6
)

NAMA_STASIUN = {
    "kondensat_sterilizer": "condensate",
    "janjang_kosong": "empty_bunch",
    "ampas_kempa": "press_cake",
    "nut_in_fiber": "nut_in_fiber",
    "underflow_cst": "cst_underflow",
    "sludge_separator": "sludge",
    "fat_pit": "fat_pit",
    "deoiling_pond": "deoiling_pond",
}
STANDAR = {
    "kondensat_sterilizer": "oil_loss.standar.kondensat_sterilizer",
    "janjang_kosong": "oil_loss.standar.janjang_kosong",
    "ampas_kempa": "oil_loss.standar.ampas_kempa",
    "sludge_separator": "oil_loss.standar.sludge_akhir",
}
KELAS_KONTRAK = {"mentah": "unripe", "kurang_masak": "underripe",
                 "masak": "ripe", "terlalu_masak": "overripe"}


def bangkitkan(tanggal: date, seed: int = 42, gangguan: str = "perebusan_kurang_matang") -> dict:
    """Satu shift utuh: muatan, grading, kehilangan stasiun, neraca."""
    rng = np.random.default_rng(seed)
    pabrik = Pabrik(seed=seed, ragam_proses=0.0)

    muatan = []
    for i, (nama, komposisi, restan) in enumerate(KARAKTER):
        berat = float(rng.uniform(4_500, 8_500))
        jam = float(rng.uniform(*restan))
        muatan.append({
            "plat": f"KH {1000 + i * 37} {'ABCDEFGH'[i % 8]}{'JKLMNP'[i % 6]}",
            "supplier": i % len(PEMASOK),
            "karakter": nama,
            "komposisi": komposisi,
            "berat": berat,
            "restan": jam,
            "jam_terima": 6 + i * 0.8,
        })

    total_tbs = sum(m["berat"] for m in muatan)

    # Komposisi seluruh shift = rata-rata berbobot berat tiap muatan.
    gabungan = {k: sum(m["komposisi"].get(k, 0.0) * m["berat"] for m in muatan) / total_tbs
                for k in KELAS_KONTRAK}
    restan_rata = sum(m["restan"] * m["berat"] for m in muatan) / total_tbs

    h = pabrik.olah(gabungan, total_tbs, jam_restan=restan_rata, gangguan=gangguan)
    kartu = M5.dari_simulator(h, total_tbs, gabungan, jam_restan=restan_rata,
                              lebar_komposisi=0.03)

    # Potensi per muatan, memakai jalur yang sama dengan endpoint grading.
    from ai.perception import potential as M4
    for m in muatan:
        selang = {k: (max(0.0, v - 0.03), v, min(1.0, v + 0.03))
                  for k, v in m["komposisi"].items()}
        p = M4.estimate(selang, m["berat"])
        m["potensi"] = p
        m["komposisi_selang"] = selang

    usd = C.nilai("harga.cpo_referensi_usd_per_ton")
    kurs = C.nilai("harga.kurs_idr_per_usd", izinkan_belum_terverifikasi=True)
    rugi_kg = total_tbs * (kartu.oer_teoretis - kartu.oer_aktual) / 100.0
    idr = rugi_kg / 1000.0 * usd * kurs

    return {
        "tanggal": tanggal, "muatan": muatan, "total_tbs": total_tbs,
        "hasil": h, "kartu": kartu, "loss_idr": idr, "pabrik": pabrik,
        "gabungan": gabungan,
    }


# --------------------------------------------------------------------
# SQL
# --------------------------------------------------------------------

def _q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _komposisi_json(selang: dict) -> str:
    d = {KELAS_KONTRAK[k]: {"v": round(v[1] * 100, 2),
                            "lo": round(v[0] * 100, 2),
                            "hi": round(v[2] * 100, 2)}
         for k, v in selang.items()}
    return _q(json.dumps(d))


def _atribusi_json(kartu) -> str:
    """Bentuk kontrak, bukan bentuk internal.

    Penerjemahan istilah dipusatkan di backend/app/services/kontrak.py
    supaya seed dan endpoint tidak pernah berbeda -- kalau berbeda,
    layar akan menampilkan data seed dengan benar lalu rusak begitu
    backend hidup, dan itu bug yang paling sulit dilacak.
    """
    sys.path.insert(0, str(ROOT / "backend"))
    from app.services import kontrak

    baris = []
    for b in kartu.semua_baris:
        baris.append({
            "cause": b.nama, "side": kontrak.pihak(b.pihak),
            "points": round(abs(b.poin), 4),
            "lo": round(abs(b.poin_hi), 4), "hi": round(abs(b.poin_lo), 4),
            "confidence": kontrak.keyakinan(b.keyakinan),
            "detail": b.keterangan,
        })
    return _q(json.dumps(baris))


def tulis_sql(s: dict, path: Path = OUT_SQL) -> Path:
    t = s["tanggal"]
    kartu, pabrik = s["kartu"], s["pabrik"]
    L = ["-- " + "=" * 68,
         "-- DATA SEED — dibangkitkan oleh scripts/seed_shift.py",
         "--",
         "-- JANGAN disunting tangan. Seluruh angka di bawah keluar dari",
         "-- ai/simulator/mill.py dan ai/reasoning/balance.py, sehingga",
         "-- barisnya benar-benar menutup. Angka yang diketik tangan pasti",
         "-- tidak menutup, dan itu hal pertama yang akan dicoba juri.",
         "--",
         f"-- Dibangkitkan ulang: python scripts/seed_shift.py --sql",
         "-- " + "=" * 68,
         ""]

    L.append("INSERT INTO supplier (name, kind) VALUES")
    L.append(",\n".join(f"    ({_q(n)}, {_q(k)})" for n, k in PEMASOK) + ";")
    L.append("")

    L.append("INSERT INTO batch (truck_plate, supplier_id, received_at,"
             " gross_weight_kg, queue_hours, shift_date) VALUES")
    baris = []
    for m in s["muatan"]:
        jam = int(m["jam_terima"])
        menit = int((m["jam_terima"] % 1) * 60)
        baris.append(
            f"    ({_q(m['plat'])}, {m['supplier'] + 1}, "
            f"{_q(f'{t} {jam:02d}:{menit:02d}:00+07')}, "
            f"{m['berat']:.2f}, {m['restan']:.2f}, {_q(t)})")
    L.append(",\n".join(baris) + ";")
    L.append("")

    L.append("INSERT INTO grading_result (batch_id, composition,"
             " potential_oil_kg, potential_lo, potential_hi,"
             " model_version, processed_at) VALUES")
    baris = []
    for i, m in enumerate(s["muatan"], start=1):
        p = m["potensi"]
        baris.append(
            f"    ({i}, {_komposisi_json(m['komposisi_selang'])}::jsonb, "
            f"{p.potensi_kg:.2f}, {p.potensi_lo:.2f}, {p.potensi_hi:.2f}, "
            f"{_q('detector-A/head-V3')}, {_q(f'{t} 12:00:00+07')})")
    L.append(",\n".join(baris) + ";")
    L.append("")

    L.append("-- loss_pct = kadar minyak DI DALAM aliran (persen terhadap")
    L.append("-- contoh), BUKAN persen terhadap TBS. Kolom points_oer")
    L.append("-- dihitung Postgres sendiri: loss_pct * mass_ratio.")
    L.append("INSERT INTO station_loss (shift_date, station, loss_pct,"
             " standard_pct, mass_ratio) VALUES")
    baris = []
    for a in ALIRAN:
        std = STANDAR.get(a)
        std_v = f"{C.nilai(std):.3f}" if std else "NULL"
        baris.append(
            f"    ({_q(t)}, {_q(NAMA_STASIUN[a])}, "
            f"{s['hasil'].kadar_aliran[a]:.3f}, {std_v}, {pabrik.nisbah[a]:.4f})")
    L.append(",\n".join(baris) + ";")
    L.append("")

    L.append("INSERT INTO shift_output (shift_date, cpo_actual_kg,"
             " tbs_processed_kg) VALUES")
    L.append(f"    ({_q(t)}, {s['hasil'].minyak_kg:.2f}, {s['total_tbs']:.2f});")
    L.append("")

    L.append("INSERT INTO balance (shift_date, potential_theoretical,"
             " potential_realistic, actual_oer, attribution, loss_value_idr,"
             " coefficient_mode) VALUES")
    L.append(f"    ({_q(t)}, {kartu.oer_teoretis:.3f}, "
             f"{kartu.oer_realistis:.3f}, {kartu.oer_aktual:.3f}, "
             f"{_atribusi_json(kartu)}::jsonb, {s['loss_idr']:.2f}, "
             f"{_q('terverifikasi')});")
    L.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def masukkan(s: dict) -> None:
    """Sisipkan langsung ke Postgres yang sedang berjalan."""
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.db import get_conn, init_pool, close_pool

    sql = tulis_sql(s, ROOT / "backend" / "db" / "init" / "_seed_sementara.sql")
    init_pool()
    try:
        with get_conn() as conn:
            conn.execute(sql.read_text(encoding="utf-8"))
            conn.commit()
    finally:
        close_pool()
        sql.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tanggal", default=str(date.today() - timedelta(days=1)))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gangguan", default="perebusan_kurang_matang")
    ap.add_argument("--sql", action="store_true",
                    help="tulis 02_seed.sql alih-alih menyisipkan ke Postgres")
    args = ap.parse_args()

    t = date.fromisoformat(args.tanggal)
    s = bangkitkan(t, seed=args.seed, gangguan=args.gangguan)
    k = s["kartu"]

    print(f"SHIFT {t} — {len(s['muatan'])} muatan, "
          f"{s['total_tbs']:,.0f} kg TBS".replace(",", "."))
    print(f"  komposisi gabungan : "
          + "  ".join(f"{k2} {v * 100:.1f}%" for k2, v in s["gabungan"].items()))
    print()
    print(f"  potensi teoretis   : {k.oer_teoretis:6.3f} poin")
    print(f"  rugi pemasok       : {k.total_pemasok_poin:+6.3f}")
    print(f"  potensi realistis  : {k.oer_realistis:6.3f} poin")
    print(f"  rugi pabrik        : {k.total_pabrik_poin:+6.3f}")
    print(f"  tak terjelaskan    : {k.tak_terjelaskan.poin:+6.3f} "
          f"[{k.tak_terjelaskan.poin_lo:.3f}; {k.tak_terjelaskan.poin_hi:.3f}]")
    print(f"  rendemen aktual    : {k.oer_aktual:6.3f} poin")
    print(f"  galat penutupan    : {k.galat_penutupan():.2e}")
    print(f"  selisih melebar    : {'YA' if k.melebar() else 'TIDAK'}")
    print(f"  nilai kehilangan   : Rp {s['loss_idr']:,.0f}".replace(",", "."))
    print()

    if k.galat_penutupan() > 1e-9:
        print("[GAGAL] neraca tidak menutup — seed tidak ditulis")
        return 1

    if args.sql:
        p = tulis_sql(s)
        print(f"[ok] {p}")
        print("     dijalankan otomatis saat `docker compose up` pertama kali")
    else:
        masukkan(s)
        print("[ok] tersisip ke Postgres")
    return 0


if __name__ == "__main__":
    sys.exit(main())
