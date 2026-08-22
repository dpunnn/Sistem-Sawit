"""Endpoint neraca — kartu tiga baris untuk satu shift giling."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.core.db import get_conn
from app.schemas.models import BalanceCard
from app.services import reasoning

router = APIRouter(prefix="/api", tags=["neraca"])

CATATAN_MODE = (
    "`terverifikasi` (bawaan) menolak koefisien yang belum tertelusur ke "
    "sumber terbit. Akibatnya kehilangan sisi pemasok ditaksir LEBIH KECIL, "
    "dan selisihnya muncul di baris `unexplained` alih-alih dipindahkan "
    "diam-diam ke pihak lain. Arah itu disengaja: kalau ragu, jangan "
    "merugikan petani.\n\n"
    "`lengkap` memakai seluruh koefisien termasuk yang belum terverifikasi. "
    "Berguna untuk melihat berapa besar harga kehati-hatian itu, TIDAK boleh "
    "dipakai sebagai dasar pembayaran."
)


def _shift_terakhir(conn) -> date | None:
    r = conn.execute(
        "SELECT shift_date FROM shift_output ORDER BY shift_date DESC LIMIT 1"
    ).fetchone()
    return r["shift_date"] if r else None


def _susun(shift: date | None, mode: str) -> BalanceCard:
    if mode not in ("terverifikasi", "lengkap"):
        raise HTTPException(
            status_code=422,
            detail={"pesan": f"mode '{mode}' tidak dikenal.",
                    "saran": "Pakai 'terverifikasi' atau 'lengkap'."})

    with get_conn() as conn:
        target = shift or _shift_terakhir(conn)
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
                        "saran": "Butuh shift_output, batch, dan grading_result "
                                 "untuk tanggal itu."})

        # Neraca harian jadi catatan permanen yang bisa ditelusuri,
        # bukan hitungan sekali pakai.
        reasoning.simpan_kartu(kartu, conn, mode=mode)
        conn.commit()

    kartu.pop("_kartu", None)
    kartu.pop("_tbs_kg", None)
    return BalanceCard(**kartu)


@router.get(
    "/balance",
    response_model=BalanceCard,
    summary="Kartu neraca minyak satu shift",
    description=(
        "Kartu **TIGA BARIS**, tidak pernah dua:\n\n"
        "```\n"
        "Potensi TEORETIS      andai seluruh muatan matang\n"
        "  (-) rugi pemasok    mutu buah yang masuk\n"
        "Potensi REALISTIS     muatan ini apa adanya\n"
        "  (-) rugi pabrik     kehilangan proses\n"
        "  (-) tak terjelaskan sisa yang tidak dibebankan ke siapa pun\n"
        "Rendemen AKTUAL       dari timbangan\n"
        "```\n\n"
        "Baris tengah bukan hiasan. Tanpanya, buah mentah dihitung dua kali: "
        "sekali karena menurunkan kandungan minyak yang masuk, sekali lagi "
        "lewat kehilangan pabrik yang naik saat memproses buah mentah — dan "
        "petani dipotong dua kali untuk satu kesalahan yang sama.\n\n"
        "Baris `unexplained` WAJIB ada dan tidak pernah dipaksa nol. "
        "Besarnya adalah ukuran seberapa jauh sistem ini boleh dipercaya "
        "hari itu.\n\n" + CATATAN_MODE
    ),
    responses={404: {"description": "Shift tidak ditemukan atau datanya tidak lengkap"}},
)
def neraca(
    shift_date: date | None = Query(
        None, description="Tanggal shift. Kosongkan untuk shift terakhir."),
    mode: str = Query("terverifikasi", description="terverifikasi | lengkap"),
):
    return _susun(shift_date, mode)


@router.get(
    "/balance/{shift_date}",
    response_model=BalanceCard,
    summary="Kartu neraca pada tanggal tertentu",
    description="Bentuk path dari `/api/balance`. " + CATATAN_MODE,
    responses={404: {"description": "Shift tidak ditemukan"}},
)
def neraca_tanggal(shift_date: date, mode: str = Query("terverifikasi")):
    return _susun(shift_date, mode)


@router.get(
    "/shifts",
    summary="Daftar shift yang tercatat",
    description="Dipakai pemilih tanggal, dan untuk tahu tanggal apa yang bisa dicoba.",
    tags=["neraca"],
)
def daftar_shift():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.shift_date, s.cpo_actual_kg, s.tbs_processed_kg, "
            "       (SELECT count(*) FROM batch b WHERE b.shift_date = s.shift_date) AS n_muatan "
            "FROM shift_output s ORDER BY s.shift_date DESC").fetchall()
    return [{
        "shift_date": r["shift_date"],
        "cpo_actual_kg": float(r["cpo_actual_kg"]),
        "tbs_processed_kg": float(r["tbs_processed_kg"]),
        "oer_aktual": round(float(r["cpo_actual_kg"]) / float(r["tbs_processed_kg"]) * 100, 3),
        "n_muatan": r["n_muatan"],
    } for r in rows]
