"""Uji perambatan ketidakpastian (e1 -> e5) dan koreksi terpelajar.

Yang dijaga di sini adalah satu sifat yang mudah dilanggar tanpa
disadari: **ketidakpastian tidak boleh menyusut saat dirambatkan**.

Selisih neraca adalah pengurangan angka-angka yang semuanya tidak pasti.
Ragamnya menjumlah, jadi selangnya melebar. Sistem yang melaporkan
selisih lebih sempit daripada bahan-bahannya sedang mengaku tahu lebih
banyak daripada yang mungkin — dan karena angka itu dipakai memotong
uang orang, pengakuan palsu itu punya korban.

Jalankan:
    python -m pytest tests/test_uncertainty.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.perception import potential as M4
from ai.perception.correction import (AMBANG_ALARM, BATAS_POIN, FITUR,
                                      KoreksiError, KoreksiTerpelajar)
from ai.reasoning import balance as M5
from ai.simulator.mill import Pabrik

BERAT = 240_000.0
KOMPOSISI = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
             "terlalu_masak": 0.05}


def _selang(komposisi, lebar=0.03):
    return {k: (max(0.0, v - lebar), v, min(1.0, v + lebar))
            for k, v in komposisi.items()}


def _kartu(lebar_komposisi=0.03, **kw):
    h = Pabrik(seed=42, ragam_proses=0.0).olah(KOMPOSISI, BERAT, jam_restan=9.0)
    return M5.dari_simulator(h, BERAT, KOMPOSISI, jam_restan=9.0,
                             lebar_komposisi=lebar_komposisi, **kw)


# --------------------------------------------------------------------
# 1. e2 -> e3 : KOMPOSISI KE KILOGRAM
# --------------------------------------------------------------------

def test_komposisi_tidak_pasti_menghasilkan_potensi_tidak_pasti():
    """Angka pasti yang lahir dari masukan tidak pasti adalah kebohongan."""
    p = M4.hitung_dengan_selang(_selang(KOMPOSISI), BERAT)
    assert p.lebar_selang > 0
    assert p.potensi_lo < p.potensi_kg < p.potensi_hi


@pytest.mark.parametrize("lebar", [0.01, 0.03, 0.06, 0.10])
def test_selang_potensi_tumbuh_bersama_selang_komposisi(lebar):
    sebelumnya = None
    for w in [0.01, 0.03, 0.06, 0.10]:
        p = M4.hitung_dengan_selang(_selang(KOMPOSISI, w), BERAT)
        if sebelumnya is not None:
            assert p.lebar_selang > sebelumnya
        sebelumnya = p.lebar_selang


# --------------------------------------------------------------------
# 2. e4 : SELISIH NERACA  <- inti AI-3.2.2
# --------------------------------------------------------------------

def test_sisa_punya_selang():
    k = _kartu()
    assert k.tak_terjelaskan.lebar > 0
    assert k.sisa_lo < k.sisa_hi


def test_sisa_lebih_lebar_daripada_bahannya():
    """Sifat yang paling mudah dilanggar tanpa disadari.

    Selisih dihitung dari beberapa angka tidak pasti sekaligus, jadi
    selangnya WAJIB tidak lebih sempit daripada penyumbang terlebar.
    """
    k = _kartu()
    assert k.melebar()
    terlebar = max(b.lebar for b in (*k.rugi_pemasok, *k.rugi_pabrik))
    assert k.tak_terjelaskan.lebar > terlebar


def test_ragam_menjumlah_bukan_mengambil_yang_terbesar():
    """Kalau ragam benar-benar dijumlahkan, lebar sisa harus melampaui
    penyumbang terbesar secara nyata -- bukan sekadar menyamainya."""
    k = _kartu()
    lebar = [b.lebar for b in (*k.rugi_pemasok, *k.rugi_pabrik)]
    kuadrat = float(np.sqrt(sum(w ** 2 for w in lebar)))
    # Monte Carlo tidak akan persis sama dengan rumus akar-jumlah-kuadrat,
    # tetapi harus berada di sekitarnya, bukan di sekitar max().
    assert k.tak_terjelaskan.lebar == pytest.approx(kuadrat, rel=0.25)


def test_komposisi_makin_kabur_membuat_sisa_makin_kabur():
    sempit = _kartu(lebar_komposisi=0.01)
    lebar = _kartu(lebar_komposisi=0.10)
    assert lebar.tak_terjelaskan.lebar > sempit.tak_terjelaskan.lebar


def test_lab_makin_berderau_membuat_sisa_makin_kabur():
    tenang = _kartu(ragam_lab=0.02)
    ribut = _kartu(ragam_lab=0.20)
    assert ribut.tak_terjelaskan.lebar > tenang.tak_terjelaskan.lebar


def test_tanpa_selang_komposisi_sistem_mengaku():
    """Baris pemasok yang diperlakukan titik harus DIKATAKAN, bukan
    dibiarkan tampak sebagai kepastian."""
    h = Pabrik(seed=42, ragam_proses=0.0).olah(KOMPOSISI, BERAT)
    k = M5.susun(KOMPOSISI, BERAT, h.minyak_kg,
                 kehilangan_pabrik_poin={a: abs(v) for a, v
                                         in h.kehilangan_aliran.items()})
    assert any("diperlakukan sebagai titik" in c for c in k.catatan)


def test_titik_tengah_selalu_di_dalam_selang():
    k = _kartu()
    for b in k.semua_baris:
        assert b.poin_lo <= b.poin <= b.poin_hi + 1e-9


def test_neraca_tetap_menutup_setelah_perambatan():
    """Menambahkan selang tidak boleh merusak aritmetika titik tengahnya."""
    assert _kartu().galat_penutupan() < 1e-9


def test_deterministik_pada_seed_sama():
    a, b = _kartu(seed=7), _kartu(seed=7)
    assert a.tak_terjelaskan.poin_lo == pytest.approx(b.tak_terjelaskan.poin_lo)
    assert a.tak_terjelaskan.poin_hi == pytest.approx(b.tak_terjelaskan.poin_hi)


# --------------------------------------------------------------------
# 3. KEYAKINAN PER BARIS
# --------------------------------------------------------------------

def test_selang_memuat_nol_tidak_pernah_boleh_jadi_potongan():
    b = M5.Baris(nama="uji", poin=-0.05, kg=-100, pihak=M5.PIHAK_PABRIK,
                 poin_lo=-0.12, poin_hi=0.03)
    assert b.keyakinan == "rendah"
    assert not b.boleh_untuk_potongan


def test_koefisien_belum_sah_menurunkan_keyakinan():
    sempit = dict(poin=-1.0, poin_lo=-1.05, poin_hi=-0.95)
    sah = M5.Baris(nama="a", kg=0, pihak="x", dasar_sah=True, **sempit)
    belum = M5.Baris(nama="b", kg=0, pihak="x", dasar_sah=False, **sempit)
    assert sah.keyakinan == "tinggi"
    assert belum.keyakinan != "tinggi"
    assert not belum.boleh_untuk_potongan


def test_baris_tanpa_selang_diperlakukan_titik_bukan_tak_diketahui():
    b = M5.Baris(nama="uji", poin=-0.5, kg=-10, pihak="x")
    assert b.poin_lo == b.poin_hi == -0.5


# --------------------------------------------------------------------
# 4. KOREKSI TERPELAJAR  <- AI-2.2.3
# --------------------------------------------------------------------

def _komposisi_acak(n, seed=42):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        m, km, tm = rng.uniform(0, 0.3), rng.uniform(0, 0.3), rng.uniform(0, 0.12)
        out.append({"mentah": m, "kurang_masak": km, "terlalu_masak": tm,
                    "masak": max(0.0, 1 - m - km - tm)})
    return out


@pytest.fixture(scope="module")
def contoh():
    ks = _komposisi_acak(400)
    formula = np.array([M4.hitung(k, 1000.0).oer_realistis for k in ks])
    return ks, formula


def test_koreksi_mendekati_nol_bila_formula_sudah_benar(contoh):
    """Belajar dari SISA punya sifat penting: kalau tidak ada yang bisa
    dipelajari, koreksinya menuju nol dengan sendirinya."""
    ks, formula = contoh
    rng = np.random.default_rng(1)
    m = KoreksiTerpelajar().latih(ks, formula + rng.normal(0, 0.10, len(formula)))
    h = m.terapkan(KOMPOSISI)
    assert abs(h.koreksi_poin) < 0.05
    assert not h.alarm


def test_koreksi_memulihkan_kekhasan_pabrik(contoh):
    ks, formula = contoh
    rng = np.random.default_rng(2)
    bias = 0.15
    m = KoreksiTerpelajar().latih(ks, formula + bias + rng.normal(0, 0.08, len(formula)))
    h = m.terapkan(KOMPOSISI)
    assert h.koreksi_poin == pytest.approx(bias, abs=0.05)


def test_koreksi_tidak_pernah_melampaui_batas(contoh):
    """Pagar yang membuat formula tetap memegang hasil akhir."""
    ks, formula = contoh
    rng = np.random.default_rng(3)
    m = KoreksiTerpelajar().latih(ks, formula - 2.0 + rng.normal(0, 0.08, len(formula)))
    h = m.terapkan(KOMPOSISI)
    assert abs(h.koreksi_poin) <= BATAS_POIN + 1e-9
    assert h.terpotong
    assert abs(h.koreksi_mentah) > BATAS_POIN


def test_penyimpangan_besar_membunyikan_alarm(contoh):
    """Koreksi besar BUKAN tanda model belajar dengan baik."""
    ks, formula = contoh
    rng = np.random.default_rng(4)
    m = KoreksiTerpelajar().latih(ks, formula - 0.60 + rng.normal(0, 0.08, len(formula)))
    h = m.terapkan(KOMPOSISI)
    assert h.alarm
    assert any("ALARM" in p for p in h.pesan)
    assert abs(h.koreksi_mentah) > AMBANG_ALARM


def test_formula_dan_koreksi_tetap_terpisah(contoh):
    """Keterlacakan hilang begitu keduanya menyatu jadi satu angka."""
    ks, formula = contoh
    rng = np.random.default_rng(5)
    m = KoreksiTerpelajar().latih(ks, formula + 0.1 + rng.normal(0, 0.08, len(formula)))
    h = m.terapkan(KOMPOSISI)
    assert h.oer_total == pytest.approx(h.oer_formula + h.koreksi_poin)
    assert h.oer_formula == pytest.approx(
        M4.hitung(KOMPOSISI, 1000.0).oer_realistis)


def test_fitur_proses_pabrik_ditolak():
    """Penjaga penghitungan ganda.

    Kalau jam restan boleh jadi fitur, koreksi akan menyerap kehilangan
    sisi pabrik ke dalam potensi sisi pemasok -- dan petani ditagih untuk
    antrean bongkar yang bukan urusannya.
    """
    for terlarang in ["jam_restan", "oer_aktual", "suhu_sterilizer",
                      "kadar_ampas", "berat_bruto_kg"]:
        with pytest.raises(KoreksiError):
            KoreksiTerpelajar._periksa_fitur(["mentah", terlarang])


def test_daftar_fitur_hanya_tentang_buah():
    assert set(FITUR) == set(M4.NAMA_KELAS)


def test_belum_dilatih_menolak_menebak():
    with pytest.raises(KoreksiError):
        KoreksiTerpelajar().terapkan(KOMPOSISI)


def test_estimate_dengan_koreksi_menggeser_hasil(contoh):
    """Koreksi terpasang lewat permukaan resmi, bukan lewat jalan samping."""
    ks, formula = contoh
    rng = np.random.default_rng(6)
    m = KoreksiTerpelajar().latih(ks, formula + 0.12 + rng.normal(0, 0.08, len(formula)))
    tanpa = M4.estimate(_selang(KOMPOSISI), BERAT)
    dengan = M4.estimate(_selang(KOMPOSISI), BERAT, koreksi=m)
    assert dengan.potensi_kg > tanpa.potensi_kg
    # koreksi menggeser, tidak melebarkan -- lebar selang berasal dari e2
    assert dengan.lebar_selang == pytest.approx(tanpa.lebar_selang, rel=1e-6)
