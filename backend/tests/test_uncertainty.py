"""BE-3.5 — pastikan tidak ada tahap yang diam-diam menghapus selang.

Janji utama sistem ini adalah setiap angka hasil model membawa selang.
Janji itu paling mudah dilanggar bukan lewat keputusan sadar, melainkan
lewat satu baris yang mengambil `.value` saja karena lebih praktis.

Berkas ini menjaganya secara otomatis, di dua tempat sekaligus:
sistem tipe (Pydantic) dan bentuk keluaran yang benar-benar dikirim.

Jalankan:
    cd backend && python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from ai.reasoning import balance as M5  # noqa: E402
from ai.simulator.mill import Pabrik  # noqa: E402

from app.schemas.models import (BalanceCard, CompositionItem, Estimate,  # noqa: E402
                                GradingResult, LossAttribution)
from app.services import reasoning  # noqa: E402

BERAT = 240_000.0
KOMPOSISI = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
             "terlalu_masak": 0.05}


def _kartu():
    h = Pabrik(seed=42, ragam_proses=0.0).olah(KOMPOSISI, BERAT, jam_restan=9.0)
    return M5.dari_simulator(h, BERAT, KOMPOSISI, jam_restan=9.0,
                             lebar_komposisi=0.03)


# --------------------------------------------------------------------
# 1. SISTEM TIPE MENOLAK ANGKA TELANJANG
# --------------------------------------------------------------------

def test_estimate_wajib_bertiga():
    """Tidak ada varian tanpa selang. Begitu boleh dimatikan, ia akan
    dimatikan."""
    with pytest.raises(Exception):
        Estimate(value=100.0)          # type: ignore[call-arg]
    with pytest.raises(Exception):
        Estimate(value=100.0, lo=90.0)  # type: ignore[call-arg]


def test_komposisi_tidak_menerima_angka_polos():
    with pytest.raises(Exception):
        CompositionItem(ripeness="ripe", percent=68.0)  # type: ignore[arg-type]


def test_potensi_minyak_tidak_menerima_angka_polos():
    with pytest.raises(Exception):
        GradingResult(
            detections=[], composition=[], potential_oil_kg=4280.0,  # type: ignore[arg-type]
            model_version="uji", processed_at="2026-08-03T12:00:00Z")


def test_atribusi_tidak_menerima_angka_polos():
    with pytest.raises(Exception):
        LossAttribution(cause="buah mentah", side="supplier",
                        points=0.7, confidence="medium")  # type: ignore[arg-type]


def test_lebar_terhitung_otomatis():
    e = Estimate(value=1166.0, lo=1148.0, hi=1186.0)
    assert e.width == pytest.approx(38.0)


# --------------------------------------------------------------------
# 2. SELANG SELAMAT SAMPAI BENTUK KONTRAK
# --------------------------------------------------------------------

def test_tiap_baris_neraca_membawa_selang():
    k = _kartu()
    for b in k.semua_baris:
        d = reasoning.selang_baris(b)
        assert {"value", "lo", "hi"} <= set(d["points"])
        assert d["points"]["lo"] <= d["points"]["value"] <= d["points"]["hi"] + 1e-9


def test_tidak_ada_selang_yang_menciut_jadi_titik():
    """Selang selebar nol berarti sistem mengaku tahu persis, dan itu
    tidak pernah benar untuk angka hasil model."""
    k = _kartu()
    for b in (*k.rugi_pemasok, *k.rugi_pabrik, k.tak_terjelaskan):
        assert b.lebar > 0, f"baris '{b.nama}' kehilangan selangnya"


def test_selisih_neraca_melebar_bukan_menyempit():
    """e4. Selisih dihitung dari beberapa angka tidak pasti sekaligus,
    jadi ragamnya menjumlah."""
    k = _kartu()
    assert k.melebar()
    terlebar = max(b.lebar for b in (*k.rugi_pemasok, *k.rugi_pabrik))
    assert k.tak_terjelaskan.lebar > terlebar


def test_kartu_lengkap_lolos_validasi_pydantic():
    """Bentuk yang benar-benar dikirim ke frontend, divalidasi utuh."""
    k = _kartu()
    kartu = BalanceCard(
        shift_date="2026-08-03",
        potential_theoretical=k.oer_teoretis,
        supplier_losses=[reasoning.selang_baris(b) for b in k.rugi_pemasok],
        potential_realistic=k.oer_realistis,
        mill_losses=[reasoning.selang_baris(b) for b in k.rugi_pabrik],
        unexplained=reasoning.selang_baris(k.tak_terjelaskan),
        actual_oer=k.oer_aktual,
        loss_value_idr=0.0,
        station_losses=[],
    )
    assert kartu.total_loss_points == pytest.approx(
        k.oer_teoretis - k.oer_aktual, abs=1e-3)
    for baris in (*kartu.supplier_losses, *kartu.mill_losses, kartu.unexplained):
        assert baris.points.width > 0


def test_json_keluaran_tetap_membawa_lo_dan_hi():
    """Serialisasi adalah tempat terakhir selang bisa hilang diam-diam."""
    k = _kartu()
    d = LossAttribution(**reasoning.selang_baris(k.tak_terjelaskan)).model_dump()
    assert set(d["points"]) >= {"value", "lo", "hi"}


# --------------------------------------------------------------------
# 3. NILAI RUPIAH BOLEH TUNGGAL — DAN ALASANNYA HARUS JELAS
# --------------------------------------------------------------------

def test_nilai_rupiah_memakai_koefisien_bersumber():
    """Rupiah sengaja TIDAK berselang: ia untuk komunikasi ke manajemen,
    bukan dasar pembayaran. Yang berlaku untuk pembayaran tetap poin
    rendemen beserta selangnya.

    Tetapi kursnya tetap harus datang dari berkas koefisien, bukan
    diketik di dalam kode.
    """
    v = reasoning.nilai_rupiah(2.0, 100_000.0)
    assert v > 0
    from ai.config import coefficients as C
    kurs = C.nilai("harga.kurs_idr_per_usd", izinkan_belum_terverifikasi=True)
    usd = C.nilai("harga.cpo_referensi_usd_per_ton")
    assert v == pytest.approx(100_000.0 * 2.0 / 100 / 1000 * usd * kurs)
