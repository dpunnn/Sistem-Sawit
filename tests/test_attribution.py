"""Uji Model 6 — yang dijaga di sini adalah hak untuk tidak dituduh.

Model 6 mengeluarkan tuduhan. Karena itu yang diuji bukan hanya
"apakah tebakannya benar", melainkan apakah ia menahan diri saat
buktinya kurang, dan apakah ia benar-benar buta terhadap kunci jawaban.

Jalankan:
    python -m pytest tests/test_attribution.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.evaluation.rule_recovery import (AMBANG_PULIH, cocokkan,
                                         tanda_tangan_sebenarnya)
from ai.reasoning.attribution import AMBANG_ANOMALI, Dugaan, Model6
from ai.simulator.mill import ALIRAN, Pabrik


@pytest.fixture(scope="module")
def riwayat():
    return Pabrik(seed=42).riwayat(400)


@pytest.fixture(scope="module")
def model(riwayat):
    return Model6(seed=42).pelajari(riwayat)


# --------------------------------------------------------------------
# 1. TIDAK BOLEH MELIHAT KUNCI JAWABAN
# --------------------------------------------------------------------

def test_label_gangguan_tidak_pernah_dipakai(riwayat):
    """Kalau kolom label dihapus, hasilnya harus PERSIS sama.

    Ini bukan formalitas: kebocoran label lewat kolom yang lupa dibuang
    adalah cara paling umum sebuah hasil tak berlabel ternyata palsu.
    """
    tanpa = riwayat.drop(columns=["_gangguan"])
    a = Model6(seed=1).pelajari(riwayat)
    b = Model6(seed=1).pelajari(tanpa)
    assert set(a.pola_) == set(b.pola_)
    for k in a.pola_:
        assert np.allclose(a.pola_[k], b.pola_[k])


def test_kolom_bergaris_bawah_dibuang(riwayat):
    """Semua kolom kebenaran simulator diawali garis bawah."""
    m = Model6(seed=1).pelajari(riwayat)
    assert m.dasar_ is not None
    assert len(m.dasar_) == len(ALIRAN)


# --------------------------------------------------------------------
# 2. MENAHAN DIRI SAAT BUKTINYA KURANG
# --------------------------------------------------------------------

def test_hari_normal_tidak_dituduh(model, riwayat):
    """Sebagian besar hari normal harus lolos tanpa tuduhan.

    Ambangnya sengaja longgar (<=15%): yang diuji adalah bahwa sistem
    PUNYA rem, bukan bahwa remnya sempurna. Angka sebenarnya dilaporkan
    di ai/evaluation/rule_recovery.py, bukan disembunyikan di sini.
    """
    normal = riwayat[riwayat._gangguan == "normal"]
    dituduh = np.mean([model.diagnosa(r).anomali for _, r in normal.iterrows()])
    assert dituduh <= 0.15


def test_keyakinan_rendah_tidak_boleh_jadi_potongan():
    d = Dugaan(nama="uji", kemiripan=0.4, poin=-0.7, poin_lo=-0.9,
               poin_hi=-0.5, aliran_utama=["ampas_kempa"])
    assert d.keyakinan == "rendah"
    assert not d.boleh_untuk_potongan
    assert "BELUM cukup untuk memotong pembayaran" in d.kalimat()


def test_selang_melewati_nol_tidak_boleh_jadi_potongan():
    """Keyakinan tinggi saja tidak cukup.

    Kalau selangnya masih memuat nol, kemungkinan "tidak ada kehilangan
    sama sekali" belum tersingkir — dan memotong pembayaran atas dasar
    itu adalah memungut uang dari ketidaktahuan.
    """
    d = Dugaan(nama="uji", kemiripan=0.95, poin=-0.10, poin_lo=-0.30,
               poin_hi=0.12, aliran_utama=["ampas_kempa"])
    assert d.keyakinan == "tinggi"
    assert not d.boleh_untuk_potongan


def test_keyakinan_tinggi_dengan_selang_bersih_boleh():
    d = Dugaan(nama="uji", kemiripan=0.95, poin=-0.55, poin_lo=-0.70,
               poin_hi=-0.40, aliran_utama=["janjang_kosong"])
    assert d.boleh_untuk_potongan
    assert "BELUM cukup" not in d.kalimat()


def test_selang_selalu_memuat_titik_tengah(model, riwayat):
    rusak = riwayat[riwayat._gangguan != "normal"].head(40)
    for _, r in rusak.iterrows():
        for d in model.diagnosa(r).dugaan:
            assert d.poin_lo <= d.poin <= d.poin_hi + 1e-9


# --------------------------------------------------------------------
# 3. MENEMUKAN YANG MEMANG ADA
# --------------------------------------------------------------------

def test_hari_rusak_terdeteksi(model, riwayat):
    rusak = riwayat[riwayat._gangguan != "normal"]
    ketemu = np.mean([model.diagnosa(r).anomali for _, r in rusak.iterrows()])
    assert ketemu >= 0.85


def test_memulihkan_mayoritas_aturan(model):
    """Sebagian besar gangguan yang ditanam harus ditemukan kembali.

    Tiga dari lima adalah ambang minimum yang dijaga di sini; hasil
    sebenarnya empat dari lima. Yang kelima
    (sludge_separator_tersumbat) memang tidak terpisahkan dari
    cst_dingin karena tanda tangannya berimpit — keterbatasan yang
    dicatat, bukan yang ditutupi.
    """
    tabel = cocokkan(model.pola_)
    assert tabel["pulih"].sum() >= 3


def test_pola_yang_pulih_sangat_mirip(model):
    tabel = cocokkan(model.pola_)
    pulih = tabel[tabel["pulih"]]
    assert (pulih["kosinus"] >= AMBANG_PULIH).all()
    assert pulih["kosinus"].max() > 0.95


def test_dua_gangguan_berimpit_memang_berimpit():
    """Membuktikan kegagalan yang tersisa punya sebab, bukan misteri.

    cst_dingin dan sludge_separator_tersumbat sama-sama menaikkan
    sludge separator dan fat pit. Kalau kosinus antar tanda tangan
    aslinya saja sudah tinggi, tidak ada metode tak berlabel yang bisa
    memisahkannya — batasnya ada di datanya, bukan di modelnya.
    """
    ttd = tanda_tangan_sebenarnya()
    mirip = float(np.dot(ttd["cst_dingin"], ttd["sludge_separator_tersumbat"]))
    assert mirip > 0.5


# --------------------------------------------------------------------
# 4. BISA DIULANG ORANG LAIN
# --------------------------------------------------------------------

def test_deterministik(riwayat):
    a = Model6(seed=7).pelajari(riwayat)
    b = Model6(seed=7).pelajari(riwayat)
    assert set(a.pola_) == set(b.pola_)
    baris = riwayat.iloc[5]
    da, db = a.diagnosa(baris), b.diagnosa(baris)
    assert [x.nama for x in da.dugaan] == [x.nama for x in db.dugaan]
    assert np.allclose([x.poin_lo for x in da.dugaan],
                       [x.poin_lo for x in db.dugaan])


def test_belum_dipelajari_menolak_menebak():
    with pytest.raises(RuntimeError):
        Model6().diagnosa({f"poin_{a}": 0.1 for a in ALIRAN})


def test_kolom_kurang_ditolak_jelas(riwayat):
    with pytest.raises(KeyError):
        Model6().pelajari(riwayat.drop(columns=["poin_ampas_kempa"]))


# --------------------------------------------------------------------
# 5. SISA TAK TERJELASKAN TIDAK BOLEH HILANG
# --------------------------------------------------------------------

def test_sisa_tidak_pernah_positif(model, riwayat):
    """Sisa adalah kehilangan yang belum dijelaskan; tandanya harus
    negatif atau nol, tidak pernah menambah minyak."""
    for _, r in riwayat.head(60).iterrows():
        assert model.diagnosa(r).poin_tak_terjelaskan <= 1e-9


def test_dugaan_dibatasi_tiga(model, riwayat):
    """Daftar tuduhan yang panjang bukan ketelitian, melainkan cara
    menyamarkan ketidaktahuan."""
    for _, r in riwayat.head(60).iterrows():
        assert len(model.diagnosa(r).dugaan) <= 3
