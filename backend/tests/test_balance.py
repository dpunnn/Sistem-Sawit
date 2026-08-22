"""BE-3.4 — buktikan buah mentah TIDAK dihitung dua kali.

Cacat ini yang paling mungkin menyelinap masuk lagi saat refactor,
karena "sederhanakan jadi dua baris" terdengar seperti perbaikan.
Test-nya murah, kerusakannya mahal: petani dipotong dua kali untuk satu
kesalahan yang sama.

Berbeda dari `tests/test_balance.py` di akar repo yang menguji lapis AI,
berkas ini menguji **jalur backend** — bentuk kontrak, tanda, dan
penerjemahan istilah. Keduanya perlu: aritmetika yang benar bisa rusak
di perjalanan menuju HTTP.

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

from app.services import kontrak, reasoning  # noqa: E402

BERAT = 240_000.0
BAIK = {"mentah": 0.02, "kurang_masak": 0.06, "masak": 0.90, "terlalu_masak": 0.02}
BURUK = {"mentah": 0.24, "kurang_masak": 0.20, "masak": 0.52, "terlalu_masak": 0.04}


def _kehilangan_tetap() -> dict[str, float]:
    """Pabrik yang sama, alat yang sama, hari yang sama."""
    p = Pabrik(seed=42, ragam_proses=0.0)
    return {k: abs(v) for k, v in p.olah(BAIK, BERAT).kehilangan_aliran.items()}


def _kartu(komposisi, mode="lengkap"):
    return M5.reconcile(komposisi, BERAT, 36_000.0,
                        kehilangan_pabrik_poin=_kehilangan_tetap(),
                        jam_restan=9.0, mode=mode)


# --------------------------------------------------------------------
# 1. ANTI PENGHITUNGAN GANDA — lewat jalur backend
# --------------------------------------------------------------------

def test_mutu_buah_tidak_menggerakkan_sisi_pabrik():
    a, b = _kartu(BAIK), _kartu(BURUK)
    assert b.total_pemasok_poin < a.total_pemasok_poin       # pemasok bergerak
    assert b.total_pabrik_poin == pytest.approx(             # pabrik tidak
        a.total_pabrik_poin, abs=1e-12)


def test_bentuk_kontrak_ikut_menjaga_pemisahan():
    """Yang diuji: setelah diterjemahkan ke bentuk HTTP, pemisahannya
    masih utuh. Aritmetika yang benar bisa rusak di perjalanan."""
    a = [reasoning.selang_baris(x) for x in _kartu(BAIK).rugi_pabrik]
    b = [reasoning.selang_baris(x) for x in _kartu(BURUK).rugi_pabrik]
    assert [x["points"]["value"] for x in a] == [x["points"]["value"] for x in b]


def test_sisi_pemasok_dan_sisa_saling_menutup():
    a, b = _kartu(BAIK), _kartu(BURUK)
    d_pemasok = b.total_pemasok_poin - a.total_pemasok_poin
    d_sisa = b.tak_terjelaskan.poin - a.tak_terjelaskan.poin
    assert d_pemasok + d_sisa == pytest.approx(0.0, abs=1e-9)


def test_potensi_teoretis_buta_terhadap_komposisi():
    assert _kartu(BAIK).oer_teoretis == pytest.approx(_kartu(BURUK).oer_teoretis)


# --------------------------------------------------------------------
# 2. TIGA BARIS, TIDAK PERNAH DUA
# --------------------------------------------------------------------

def test_neraca_menutup():
    assert _kartu(BURUK).galat_penutupan() < 1e-9


def test_baris_tak_terjelaskan_selalu_ada():
    k = _kartu(BAIK)
    assert k.tak_terjelaskan is not None
    d = reasoning.selang_baris(k.tak_terjelaskan)
    assert d["side"] == "unknown"


def test_urutan_tiga_baris_tidak_terbalik():
    """Kendala yang sama juga ditegakkan basis data lewat CHECK.

    Potensi realistis yang melampaui potensi teoretis berarti mutu buah
    MENAMBAH kandungan minyak — mustahil.
    """
    for komposisi in (BAIK, BURUK):
        k = _kartu(komposisi)
        assert k.oer_realistis <= k.oer_teoretis


# --------------------------------------------------------------------
# 3. PENERJEMAHAN ISTILAH
# --------------------------------------------------------------------

def test_pihak_diterjemahkan_ke_kontrak():
    k = _kartu(BURUK)
    sisi = {reasoning.selang_baris(b)["side"] for b in k.semua_baris}
    assert sisi <= {"supplier", "mill", "unknown"}
    assert "supplier" in sisi and "mill" in sisi and "unknown" in sisi


def test_urutan_selang_benar_walau_sisa_positif():
    """Pembalikan tanda memakai NEGASI, bukan nilai mutlak.

    Bedanya baru terlihat pada kasus sisa positif — saat pabrik
    menghasilkan lebih banyak daripada yang bisa dijelaskan neraca.
    Dengan nilai mutlak, batas selangnya tertukar dan `lo` jadi lebih
    besar daripada `hi`. Bug itu ditemukan uji ini, bukan oleh mata.

    Komposisi BURUK dengan hasil 36 ton memang menghasilkan sisa
    positif: koefisien mode `lengkap` menjelaskan LEBIH banyak
    kehilangan daripada yang benar-benar terjadi.
    """
    k = _kartu(BURUK)
    for b in k.semua_baris:
        d = reasoning.selang_baris(b)
        assert d["points"]["lo"] <= d["points"]["value"] <= d["points"]["hi"] + 1e-9


def test_kehilangan_biasa_bertanda_positif():
    """Pada kasus normal, kehilangan keluar sebagai besaran positif."""
    k = _kartu(BAIK)
    for b in (*k.rugi_pemasok, *k.rugi_pabrik):
        assert reasoning.selang_baris(b)["points"]["value"] > 0


def test_sisa_positif_diberi_peringatan():
    """Nilai negatif TIDAK disamarkan jadi positif — ia sinyal bahwa
    koefisien terlalu berhati-hati, dan harus terbaca apa adanya."""
    k = _kartu(BURUK)
    d = reasoning.selang_baris(k.tak_terjelaskan)
    if d["points"]["value"] < 0:
        assert any("POSITIF" in c for c in k.catatan)


def test_keyakinan_tak_dikenal_jatuh_ke_low():
    """Kalau sistem tidak tahu seberapa yakin dirinya, jawabannya bukan
    'tinggi'."""
    assert kontrak.keyakinan("entah") == "low"
    assert kontrak.pihak("entah") == "unknown"


def test_peta_kelas_bolak_balik_konsisten():
    for k, v in kontrak.KELAS.items():
        assert kontrak.KELAS_BALIK[v] == k


def test_semua_stasiun_punya_label():
    for nama in kontrak.STASIUN.values():
        assert nama in kontrak.LABEL_STASIUN


# --------------------------------------------------------------------
# 4. TIDAK ADA RUMUS DOMAIN DI BACKEND  <- ATURAN 3
# --------------------------------------------------------------------

def test_backend_tidak_memuat_koefisien_domain():
    """Penjaga kebocoran lapisan.

    Angka-angka domain (21.0 basis matang, -0.13 penalti buah mentah,
    nisbah massa) hanya boleh hidup di ai/config/coefficients.yaml.
    Kalau salah satunya muncul sebagai literal di backend/, artinya ada
    rumus yang disalin — dan dua tempat yang menghitung hal sama dengan
    cara berbeda hanya soal waktu sebelum berbeda hasilnya.
    """
    import re

    terlarang = [r"\b21\.0\b", r"-0\.13\b", r"\b0\.055\b", r"\b938\.87\b"]
    pelanggar = []
    for f in (BACKEND / "app").rglob("*.py"):
        teks = f.read_text(encoding="utf-8")
        # buang komentar & docstring sederhana: yang dicari adalah kode
        kode = "\n".join(l.split("#")[0] for l in teks.splitlines())
        for pola in terlarang:
            if re.search(pola, kode):
                pelanggar.append(f"{f.relative_to(BACKEND)} :: {pola}")
    assert not pelanggar, (
        "koefisien domain muncul sebagai literal di backend: " + str(pelanggar))
