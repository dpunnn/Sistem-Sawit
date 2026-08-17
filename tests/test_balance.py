"""Uji Model 5 — yang dijaga di sini adalah keadilan, bukan akurasi.

Klaim inti proyek ini adalah bahwa buah mentah TIDAK dihitung dua kali.
Klaim seperti itu tidak boleh berhenti sebagai paragraf di proposal; ia
harus bisa gagal. Berkas ini yang membuatnya bisa gagal.

Jalankan:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.reasoning import balance as M5
from ai.simulator.mill import Pabrik

BERAT = 240_000.0

BAIK = {"mentah": 0.02, "kurang_masak": 0.06, "masak": 0.90,
        "terlalu_masak": 0.02}
BURUK = {"mentah": 0.24, "kurang_masak": 0.20, "masak": 0.52,
         "terlalu_masak": 0.04}


def _kehilangan_tetap() -> dict[str, float]:
    """Hasil ukur aliran yang IDENTIK untuk dua muatan berbeda.

    Kuncinya di sini: pabrik yang sama, alat yang sama, hari yang sama.
    Kalau Model 5 membebankan kehilangan pabrik yang berbeda hanya karena
    buah masuknya berbeda mutu, itu penghitungan ganda.
    """
    p = Pabrik(seed=42, ragam_proses=0.0)
    return {k: abs(v) for k, v in
            p.olah(BAIK, BERAT).kehilangan_aliran.items()}


# --------------------------------------------------------------------
# 1. ARITMETIKA
# --------------------------------------------------------------------

@pytest.mark.parametrize("komposisi", [BAIK, BURUK])
@pytest.mark.parametrize("mode", ["terverifikasi", "lengkap"])
def test_neraca_menutup(komposisi, mode):
    """Baris-baris harus benar-benar berjumlah ke rendemen aktual."""
    k = M5.susun(komposisi, BERAT, 36_000.0,
                 kehilangan_pabrik_poin=_kehilangan_tetap(),
                 jam_restan=9.0, mode=mode)
    assert k.galat_penutupan() < 1e-9


def test_pangsa_berjumlah_satu():
    k = M5.susun(BURUK, BERAT, 36_000.0,
                 kehilangan_pabrik_poin=_kehilangan_tetap(), jam_restan=6.0)
    assert sum(k.bagi_tanggung_jawab().values()) == pytest.approx(1.0)


# --------------------------------------------------------------------
# 2. ANTI PENGHITUNGAN GANDA  <- klaim inti proyek
# --------------------------------------------------------------------

def test_mutu_buah_tidak_menyentuh_sisi_pabrik():
    """Memburukkan mutu buah HANYA boleh menggerakkan baris pemasok.

    Kalau uji ini gagal, seluruh tesis "menunjuk dua arah" runtuh:
    petani akan dipotong sekali karena buahnya mentah, lalu dipotong
    lagi lewat kehilangan pabrik yang naik karena buahnya mentah.
    """
    hilang = _kehilangan_tetap()
    minyak = 36_000.0

    a = M5.susun(BAIK, BERAT, minyak, kehilangan_pabrik_poin=hilang,
                 jam_restan=9.0, mode="lengkap")
    b = M5.susun(BURUK, BERAT, minyak, kehilangan_pabrik_poin=hilang,
                 jam_restan=9.0, mode="lengkap")

    # sisi pemasok HARUS bergerak, dan ke arah yang benar
    assert b.total_pemasok_poin < a.total_pemasok_poin

    # sisi pabrik TIDAK BOLEH bergerak sedikit pun
    assert b.total_pabrik_poin == pytest.approx(a.total_pabrik_poin, abs=1e-12)


def test_selisih_pemasok_pindah_ke_tak_terjelaskan_bukan_ke_pabrik():
    """Setiap poin yang ditambahkan ke pemasok harus dikurangi dari
    baris tak terjelaskan — bukan dari baris pabrik.

    Ini bentuk kekekalan: total selisih ditentukan oleh timbangan, jadi
    memindahkan tuduhan ke satu pihak wajib mengambilnya dari pihak lain
    secara eksplisit. Kalau tidak, sistem sedang mencetak kesalahan dari
    ketiadaan.
    """
    hilang = _kehilangan_tetap()
    a = M5.susun(BAIK, BERAT, 36_000.0, kehilangan_pabrik_poin=hilang,
                 mode="lengkap")
    b = M5.susun(BURUK, BERAT, 36_000.0, kehilangan_pabrik_poin=hilang,
                 mode="lengkap")

    d_pemasok = b.total_pemasok_poin - a.total_pemasok_poin
    d_sisa = b.tak_terjelaskan.poin - a.tak_terjelaskan.poin
    assert d_pemasok + d_sisa == pytest.approx(0.0, abs=1e-9)


def test_kehilangan_pabrik_naik_tidak_menyentuh_sisi_pemasok():
    """Arah sebaliknya juga harus dijaga: pabrik yang bocor tidak boleh
    membuat tagihan pemasok membesar."""
    hilang = _kehilangan_tetap()
    parah = {k: v * 1.6 for k, v in hilang.items()}

    a = M5.susun(BURUK, BERAT, 36_000.0, kehilangan_pabrik_poin=hilang,
                 mode="lengkap")
    b = M5.susun(BURUK, BERAT, 36_000.0, kehilangan_pabrik_poin=parah,
                 mode="lengkap")

    assert b.total_pabrik_poin < a.total_pabrik_poin
    assert b.total_pemasok_poin == pytest.approx(a.total_pemasok_poin, abs=1e-12)


# --------------------------------------------------------------------
# 3. BARIS TAK TERJELASKAN TIDAK BOLEH DIHAPUS
# --------------------------------------------------------------------

def test_baris_tak_terjelaskan_selalu_ada():
    k = M5.susun(BAIK, BERAT, 36_000.0,
                 kehilangan_pabrik_poin=_kehilangan_tetap())
    assert k.tak_terjelaskan is not None
    assert k.tak_terjelaskan.pihak == M5.PIHAK_TIDAK_JELAS
    assert k.tak_terjelaskan in k.semua_baris


def test_sisa_nol_kalau_semua_koefisien_sama_dengan_simulator():
    """Kalau Model 5 memakai koefisien yang PERSIS sama dengan yang
    dipakai simulator, sisanya harus nol.

    Ini yang memisahkan "modelnya salah" dari "koefisiennya kurang":
    aritmetikanya terbukti tepat, sehingga sisa yang muncul di mode
    terverifikasi benar-benar berasal dari koefisien yang ditolak,
    bukan dari kesalahan hitung.
    """
    komposisi = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                 "terlalu_masak": 0.05}
    p = Pabrik(seed=42, ragam_proses=0.0)
    h = p.olah(komposisi, BERAT, jam_restan=9.0,
               gangguan="perebusan_kurang_matang")
    k = M5.dari_simulator(h, BERAT, komposisi, jam_restan=9.0, mode="lengkap")
    assert k.tak_terjelaskan.poin == pytest.approx(0.0, abs=1e-9)


def test_mode_terverifikasi_memindahkan_beban_ke_tak_terjelaskan():
    """Kehati-hatian harus punya harga yang terlihat, bukan gratis.

    Menolak koefisien yang belum tertelusur membuat rugi pemasok
    ditaksir lebih kecil. Selisihnya WAJIB muncul sebagai ketidaktahuan,
    bukan diam-diam ditimpakan ke pabrik.
    """
    komposisi = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                 "terlalu_masak": 0.05}
    p = Pabrik(seed=42, ragam_proses=0.0)
    h = p.olah(komposisi, BERAT, jam_restan=9.0)

    ketat = M5.dari_simulator(h, BERAT, komposisi, jam_restan=9.0,
                              mode="terverifikasi")
    longgar = M5.dari_simulator(h, BERAT, komposisi, jam_restan=9.0,
                                mode="lengkap")

    assert ketat.total_pemasok_poin > longgar.total_pemasok_poin   # kurang menuduh
    assert abs(ketat.tak_terjelaskan.poin) > abs(longgar.tak_terjelaskan.poin)
    assert ketat.catatan, "mode ketat wajib menjelaskan apa yang dilewatinya"


# --------------------------------------------------------------------
# 4. SIFAT MONOTON YANG HARUS DIPERTAHANKAN
# --------------------------------------------------------------------

@pytest.mark.parametrize("pct", [0.0, 0.1, 0.2, 0.3, 0.4])
def test_makin_mentah_makin_kecil_potensi_realistis(pct):
    sebelumnya = None
    for p in [0.0, 0.1, 0.2, 0.3, 0.4]:
        komposisi = {"mentah": p, "masak": 1 - p}
        k = M5.susun(komposisi, BERAT, 36_000.0,
                     kehilangan_pabrik_poin=_kehilangan_tetap())
        if sebelumnya is not None:
            assert k.potensi_realistis_kg < sebelumnya
        sebelumnya = k.potensi_realistis_kg


def test_potensi_teoretis_buta_terhadap_komposisi():
    """Baris pertama tidak boleh melihat mutu buah sama sekali.

    Kalau ia ikut bergerak, baris kedua kehilangan makna sebagai
    "kerugian akibat mutu" dan penghitungan ganda masuk lewat pintu
    belakang.
    """
    a = M5.susun(BAIK, BERAT, 36_000.0)
    b = M5.susun(BURUK, BERAT, 36_000.0)
    assert a.potensi_teoretis_kg == pytest.approx(b.potensi_teoretis_kg)


def test_sisa_positif_diberi_peringatan():
    """Rendemen aktual di atas yang bisa dijelaskan berarti ada yang
    keliru pada koefisien — dan sistem harus mengatakannya, bukan
    menjadikannya potongan."""
    # 50.200 kg dari 240 ton = 20,92 poin, di atas potensi realistis 20,74
    # yang bisa dijelaskan -> harus muncul sebagai sisa positif berperingatan
    k = M5.susun(BAIK, BERAT, 50_200.0)
    assert k.tak_terjelaskan.poin > 0
    assert any("POSITIF" in c for c in k.catatan)


# --------------------------------------------------------------------
# 5. KELUARAN UNTUK BACKEND
# --------------------------------------------------------------------

def test_dict_memuat_semua_baris():
    k = M5.susun(BURUK, BERAT, 36_000.0,
                 kehilangan_pabrik_poin=_kehilangan_tetap(), jam_restan=9.0)
    d = k.sebagai_dict()
    for kunci in ("teoretis", "rugi_pemasok", "realistis", "rugi_pabrik",
                  "tak_terjelaskan", "aktual", "pangsa", "galat_penutupan"):
        assert kunci in d
    assert len(d["rugi_pabrik"]) == len(k.rugi_pabrik)
    assert d["galat_penutupan"] < 1e-9
