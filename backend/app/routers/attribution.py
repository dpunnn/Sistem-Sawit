"""Endpoint atribusi — memecah kehilangan jadi penyebab, dengan selang.

ATURAN EMAS yang dijaga endpoint ini:

  SALAH : "0,7 poin hilang karena buah mentah pemasok A"
  BENAR : "0,7 +/- 0,25 poin — keyakinan sedang. Cukup untuk bahan
           diskusi, BELUM cukup untuk memotong pembayaran."

Karena itu setiap penyebab keluar bersama `confidence` DAN
`may_deduct_payment`. Yang kedua bukan sekadar terjemahan yang pertama:
keyakinan tinggi dengan selang yang masih memuat nol tetap tidak boleh
jadi dasar potongan.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.core.db import get_conn
from app.schemas.models import AttributionResponse
from app.services import reasoning

router = APIRouter(prefix="/api", tags=["atribusi"])

AMBANG = {
    "high": "Boleh jadi dasar keputusan finansial",
    "medium": "Cukup untuk bahan diskusi, belum untuk memotong pembayaran",
    "low": "Ditampilkan saja, tidak memicu tindakan",
}


@router.get(
    "/attribution",
    response_model=AttributionResponse,
    summary="Atribusi kehilangan rendemen per penyebab",
    description=(
        "Memecah selisih antara potensi teoretis dan rendemen aktual menjadi "
        "penyebab-penyebab, masing-masing dengan selang keyakinan dan ambang "
        "tindakan.\n\n"
        "**Ambang tindakan** — angka yang sama tidak boleh memicu konsekuensi "
        "yang sama bila keyakinannya berbeda:\n\n"
        "| Keyakinan | Boleh dipakai untuk |\n"
        "|---|---|\n"
        "| `high` | Dasar keputusan finansial |\n"
        "| `medium` | Bahan diskusi, belum untuk memotong pembayaran |\n"
        "| `low` | Ditampilkan saja, tidak memicu tindakan |\n\n"
        "`may_deduct_payment` menggabungkan dua syarat sekaligus: keyakinan "
        "harus `high` **dan** selangnya tidak boleh memuat nol. Selama "
        "kemungkinan 'tidak ada kehilangan sama sekali' belum tersingkir, "
        "memotong pembayaran berarti memungut uang dari ketidaktahuan.\n\n"
        "Baris `unexplained` selalu ikut dan tidak pernah dipaksa nol."
    ),
    responses={404: {"description": "Shift tidak ditemukan"}},
)
def atribusi(
    shift_date: date | None = Query(
        None, description="Tanggal shift. Kosongkan untuk shift terakhir."),
    mode: str = Query("terverifikasi", description="terverifikasi | lengkap"),
):
    with get_conn() as conn:
        target = shift_date
        if target is None:
            r = conn.execute(
                "SELECT shift_date FROM shift_output ORDER BY shift_date DESC LIMIT 1"
            ).fetchone()
            target = r["shift_date"] if r else None
        if target is None:
            raise HTTPException(
                status_code=404,
                detail={"pesan": "Belum ada shift giling yang tercatat.",
                        "saran": "Jalankan: python scripts/seed_shift.py"})

        kartu = reasoning.kartu_dari_basis_data(target, conn, mode=mode)
        if kartu is None:
            raise HTTPException(
                status_code=404,
                detail={"pesan": f"Shift {target} tidak punya data lengkap.",
                        "saran": "Butuh shift_output, batch, dan grading_result."})

    obj = kartu["_kartu"]
    penyebab = []
    for b in obj.semua_baris:
        d = reasoning.selang_baris(b)
        d["may_deduct_payment"] = b.boleh_untuk_potongan
        d["action_threshold"] = AMBANG[d["confidence"]]
        penyebab.append(d)
    penyebab.sort(key=lambda x: -x["points"]["value"])

    pangsa = obj.bagi_tanggung_jawab()
    return AttributionResponse(
        shift_date=target,
        total_loss_points=round(obj.oer_teoretis - obj.oer_aktual, 3),
        causes=penyebab,
        share={"supplier": round(pangsa["pemasok"], 4),
               "mill": round(pangsa["pabrik"], 4),
               "unknown": round(pangsa["tidak_terjelaskan"], 4)},
        uncertainty_widens=obj.melebar(),
        closure_error=obj.galat_penutupan(),
        coefficient_mode=mode,
        notes=obj.catatan,
    )


@router.get("/attribution/{shift_date}", response_model=AttributionResponse,
            summary="Atribusi pada tanggal tertentu",
            description="Bentuk path dari `/api/attribution`.")
def atribusi_tanggal(shift_date: date, mode: str = Query("terverifikasi")):
    return atribusi(shift_date, mode)
