"""Endpoint pemasok dan koreksi grader.

Dua kartu di halaman neraca sebelumnya memakai angka karangan yang
ditulis langsung di berkas frontend. Padahal datanya SUDAH ADA di basis
data — tinggal ditanyakan.

Angka karangan di layar yang dilihat juri bukan sekadar tidak rapi; ia
klaim yang tidak dimiliki sistem. Dan yang paling berbahaya justru
kurva koreksi grader, karena ia mengaku sebagai bukti sistem belajar.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.core.db import get_conn

router = APIRouter(prefix="/api", tags=["pemasok"])


@router.get(
    "/suppliers",
    summary="Peringkat pemasok menurut proporsi buah mentah",
    description=(
        "Dihitung dari hasil grading yang benar-benar tersimpan, bukan dari "
        "daftar yang ditulis tangan.\n\n"
        "**Peringkat ini bahan diskusi, bukan dasar potongan.** Komponen "
        "kematangan berakurasi 0,6346 pada muatan campuran — cukup untuk "
        "menunjukkan pemasok mana yang perlu dibina, belum cukup untuk "
        "menentukan siapa dibayar berapa.\n\n"
        "`n_muatan` sengaja ikut: peringkat dari 2 muatan dan dari 200 muatan "
        "tidak boleh dibaca dengan bobot yang sama."
    ),
)
def daftar_pemasok(shift_date: date | None = Query(
        None, description="Batasi ke satu shift. Kosongkan untuk seluruh riwayat.")):
    syarat = "WHERE b.shift_date = %s" if shift_date else ""
    argumen = (shift_date,) if shift_date else ()

    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT s.name, s.kind,
                   count(g.id)                                        AS n_muatan,
                   avg((g.composition->'unripe'->>'v')::numeric)       AS mentah,
                   avg((g.composition->'ripe'->>'v')::numeric)         AS masak,
                   sum(b.gross_weight_kg)                              AS berat_kg,
                   avg(b.queue_hours)                                  AS restan_jam
            FROM supplier s
            JOIN batch b ON b.supplier_id = s.id
            JOIN grading_result g ON g.batch_id = b.id
            {syarat}
            GROUP BY s.id, s.name, s.kind
            ORDER BY mentah DESC NULLS LAST
        """, argumen).fetchall()

    return [{
        "name": r["name"],
        "kind": r["kind"],
        "n_muatan": r["n_muatan"],
        "unripe_pct": round(float(r["mentah"]), 2) if r["mentah"] is not None else None,
        "ripe_pct": round(float(r["masak"]), 2) if r["masak"] is not None else None,
        "gross_weight_kg": round(float(r["berat_kg"]), 2),
        "queue_hours_avg": round(float(r["restan_jam"]), 2),
    } for r in rows]


@router.get(
    "/corrections",
    summary="Koreksi grader — seberapa sering manusia membantah model",
    description=(
        "Dihitung dari tabel `grader_decision`, bukan dari kurva yang digambar "
        "supaya terlihat menurun.\n\n"
        "Kalau datanya masih sedikit, jawabannya `cukup_data: false` dan "
        "frontend WAJIB menampilkan keadaan kosong alih-alih grafik. Sistem "
        "ini belum pernah berjalan berminggu-minggu di pabrik mana pun, dan "
        "mengaku sudah belajar berdasarkan data yang tidak ada adalah klaim "
        "yang paling mudah dibantah juri.\n\n"
        "Ambang `cukup_data` sengaja rendah (20 keputusan) — cukup untuk "
        "angkanya berarti, jauh dari cukup untuk menyimpulkan tren."
    ),
)
def koreksi_grader():
    AMBANG = 20
    with get_conn() as conn:
        total = conn.execute(
            "SELECT count(*) AS n, "
            "       count(*) FILTER (WHERE decision = 'correct') AS n_koreksi "
            "FROM grader_decision").fetchone()
        mingguan = conn.execute("""
            SELECT date_trunc('week', d.decided_at)::date AS minggu,
                   count(*)                                        AS n_keputusan,
                   count(*) FILTER (WHERE d.decision = 'correct')   AS n_koreksi
            FROM grader_decision d
            GROUP BY 1 ORDER BY 1
        """).fetchall()

    n = total["n"] or 0
    return {
        "n_keputusan": n,
        "n_koreksi": total["n_koreksi"] or 0,
        "rasio_koreksi": round((total["n_koreksi"] or 0) / n, 4) if n else None,
        "cukup_data": n >= AMBANG,
        "ambang_cukup_data": AMBANG,
        "per_minggu": [{
            "week": str(r["minggu"]),
            "n_keputusan": r["n_keputusan"],
            "n_koreksi": r["n_koreksi"],
            "per_100_muatan": round(r["n_koreksi"] / r["n_keputusan"] * 100, 1)
            if r["n_keputusan"] else 0,
        } for r in mingguan],
        "catatan": (
            "Cukup data untuk dibaca sebagai tren."
            if n >= AMBANG else
            f"Baru {n} keputusan tercatat, di bawah ambang {AMBANG}. "
            "Belum boleh disajikan sebagai bukti sistem membaik."
        ),
    }
