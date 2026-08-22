"""MODEL 4 — Potensi minyak per muatan.

## Kenapa ini regresi, bukan klasifikasi

Sistem lain berhenti di "68% matang". Angka itu tidak bisa dimasukkan ke
neraca massa. Yang dibutuhkan: **berapa KILOGRAM minyak ada di truk ini**.
Itu yang mengubah label menjadi akuntansi.

## Formula wajib transparan

Keluaran modul ini dipakai memotong pembayaran petani. Karena itu formula
dasarnya aljabar sederhana yang bisa dihitung ulang dengan kalkulator oleh
siapa pun yang mempersoalkannya — bukan kotak hitam:

    OER_teoretis  = basis_matang                        (andai seluruh matang)
    rugi_komposisi = SUM( proporsi_kelas x penalti_kelas )
    OER_realistis = OER_teoretis + rugi_komposisi        (penalti bertanda negatif)
    potensi_kg    = berat_bruto x OER_realistis / 100

Seluruh koefisien datang dari `ai/config/coefficients.yaml`, tidak ada yang
ditulis di dalam kode.

## Disiplin koefisien yang menggigit di sini

Dari empat penalti kematangan, **hanya `penalti_buah_mentah` yang
terverifikasi** ke sumber terbit. Penalti kurang masak dan terlalu masak
masih berstatus `perlu_verifikasi`.

Konsekuensinya nyata, bukan formalitas: mode bawaan (`terverifikasi`)
menghitung HANYA memakai koefisien yang sah. Penalti yang belum sah
diperlakukan nol, sehingga **kehilangan sisi pemasok ditaksir lebih
rendah** — arah kesalahan yang benar untuk sistem yang memotong uang
orang: kalau ragu, jangan merugikan petani.

Efek sampingnya harus disebut terus terang: karena potensi realistis jadi
lebih tinggi, selisih menuju rendemen aktual menjadi lebih lebar, dan
kehilangan itu berpindah ke **sisi pabrik**. Pilihan ini disengaja —
pabrik punya kemampuan menyelidiki dan memperbaiki, petani tidak.

Mode `lengkap` memakai semua penalti tetapi menandai hasilnya sebagai belum
terverifikasi, dan tidak boleh dipakai sebagai dasar potongan.

## Perambatan ketidakpastian

Komposisi dari Model 2 berupa selang, bukan angka pasti. Selang itu
dirambatkan lewat Monte Carlo: proporsi diambil acak dari dalam selangnya,
dinormalkan agar berjumlah 1, lalu potensinya dihitung. Persentil hasilnya
menjadi selang potensi (e2 -> e3 pada rantai ketidakpastian).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ai.config import coefficients as C  # noqa: E402

NAMA_KELAS = ["mentah", "kurang_masak", "masak", "terlalu_masak"]

# Peta tingkat kematangan -> jalur koefisien penalti.
# `masak` tidak punya penalti: ia adalah titik acuan basis_matang.
PENALTI = {
    "mentah": "kematangan.penalti_buah_mentah",
    "kurang_masak": "kematangan.penalti_kurang_masak",
    "masak": None,
    "terlalu_masak": "kematangan.penalti_terlalu_masak",
}


@dataclass(frozen=True)
class PotensiMinyak:
    """Hasil taksiran potensi, lengkap dengan jejak perhitungannya."""

    oer_teoretis: float          # poin OER, andai seluruh muatan matang
    rugi_komposisi: float        # poin OER, bertanda negatif
    oer_realistis: float         # poin OER, muatan ini apa adanya
    potensi_kg: float            # kilogram minyak
    potensi_lo: float
    potensi_hi: float
    berat_bruto_kg: float
    mode: str                    # "terverifikasi" | "lengkap"
    penalti_dipakai: dict[str, float]
    penalti_dilewati: list[str]  # koefisien yang ditolak karena belum sah
    dasar_sah: bool              # True bila seluruh koefisien yang DIPAKAI sah

    @property
    def lebar_selang(self) -> float:
        return self.potensi_hi - self.potensi_lo

    def sebagai_dict(self) -> dict:
        return asdict(self)


def _ambil_penalti(mode: str) -> tuple[dict[str, float], list[str]]:
    """Kumpulkan penalti yang boleh dipakai pada mode tertentu."""
    dipakai, dilewati = {}, []
    izin = (mode == "lengkap")
    for kelas, jalur in PENALTI.items():
        if jalur is None:
            dipakai[kelas] = 0.0
            continue
        try:
            dipakai[kelas] = C.nilai(jalur, izinkan_belum_terverifikasi=izin)
        except C.KoefisienError:
            # Ditolak loader karena belum terverifikasi. Diperlakukan nol,
            # dan dicatat supaya keputusan ini terlihat -- bukan hilang.
            dipakai[kelas] = 0.0
            dilewati.append(jalur)
    return dipakai, dilewati


def hitung(komposisi: dict[str, float], berat_bruto_kg: float,
           *, mode: str = "terverifikasi") -> PotensiMinyak:
    """Hitung potensi minyak dari komposisi titik (tanpa selang)."""
    if mode not in ("terverifikasi", "lengkap"):
        raise ValueError("mode harus 'terverifikasi' atau 'lengkap'")

    basis = C.nilai("rendemen.basis_matang")
    penalti, dilewati = _ambil_penalti(mode)

    # proporsi dinormalkan; disebut persen karena koefisien dinyatakan
    # "per 1 persen proporsi"
    total = sum(max(0.0, komposisi.get(k, 0.0)) for k in NAMA_KELAS)
    if total <= 0:
        raise ValueError("komposisi kosong")
    prop = {k: max(0.0, komposisi.get(k, 0.0)) / total * 100.0
            for k in NAMA_KELAS}

    rugi = sum(prop[k] * penalti[k] for k in NAMA_KELAS)
    oer_realistis = basis + rugi
    potensi = berat_bruto_kg * oer_realistis / 100.0

    return PotensiMinyak(
        oer_teoretis=basis, rugi_komposisi=rugi, oer_realistis=oer_realistis,
        potensi_kg=potensi, potensi_lo=potensi, potensi_hi=potensi,
        berat_bruto_kg=berat_bruto_kg, mode=mode,
        penalti_dipakai=penalti, penalti_dilewati=dilewati,
        # Pada mode "terverifikasi", koefisien yang belum sah ditolak dan
        # diperlakukan nol -- sehingga seluruh koefisien yang benar-benar
        # DIPAKAI sudah sah. Pada mode "lengkap" sebaliknya.
        dasar_sah=(mode == "terverifikasi"),
    )


def hitung_dengan_selang(komposisi_selang: dict[str, tuple[float, float, float]],
                         berat_bruto_kg: float, *,
                         mode: str = "terverifikasi",
                         n_sampel: int = 4000, alpha: float = 0.10,
                         seed: int = 42) -> PotensiMinyak:
    """Rambatkan selang komposisi (Model 2) menjadi selang potensi.

    Parameters
    ----------
    komposisi_selang
        ``{kelas: (lo, nilai, hi)}`` — keluaran Model 2.
    alpha
        0.10 menghasilkan selang 90%, sejalan dengan Model 2.

    Catatan metodologis: pencuplikan dilakukan seragam di dalam selang
    marginal lalu dinormalkan. Ini pendekatan konservatif — selang marginal
    Model 2 tidak memuat informasi korelasi antar kelas, sehingga
    mengasumsikan bentuk sebaran tertentu justru akan mengaku tahu lebih
    banyak daripada yang sebenarnya diketahui.
    """
    rng = np.random.default_rng(seed)
    titik = hitung({k: v[1] for k, v in komposisi_selang.items()},
                   berat_bruto_kg, mode=mode)

    lo = np.array([komposisi_selang[k][0] for k in NAMA_KELAS])
    hi = np.array([komposisi_selang[k][2] for k in NAMA_KELAS])
    sampel = rng.uniform(lo, hi, size=(n_sampel, len(NAMA_KELAS)))
    s = sampel.sum(axis=1, keepdims=True)
    sampel = np.divide(sampel, np.where(s == 0, 1, s)) * 100.0

    penalti = np.array([titik.penalti_dipakai[k] for k in NAMA_KELAS])
    oer = titik.oer_teoretis + sampel @ penalti
    potensi = berat_bruto_kg * oer / 100.0

    q_lo, q_hi = np.quantile(potensi, [alpha / 2, 1 - alpha / 2])
    return PotensiMinyak(
        **{**titik.sebagai_dict(),
           "potensi_lo": float(q_lo), "potensi_hi": float(q_hi)})


# --------------------------------------------------------- uji akal sehat

def sanity_check(verbose: bool = True) -> dict:
    """Periksa apakah formula berperilaku masuk akal.

    Tiga hal yang wajib benar, dan kalau salah satu gagal berarti ada bug
    di formula atau di satuan:

    1. Muatan 100% matang harus mendekati `basis_matang` (~21 poin OER).
    2. Muatan 100% mentah harus jauh di bawah itu.
    3. Menambah proporsi buah mentah harus MENURUNKAN potensi, monoton.
    """
    basis = C.nilai("rendemen.basis_matang")
    berat = 6000.0
    hasil = {}

    semua_matang = hitung({"masak": 1.0}, berat)
    hasil["semua_matang_oer"] = semua_matang.oer_realistis
    hasil["lulus_1"] = abs(semua_matang.oer_realistis - basis) < 1e-9

    semua_mentah = hitung({"mentah": 1.0}, berat)
    hasil["semua_mentah_oer"] = semua_mentah.oer_realistis
    hasil["lulus_2"] = semua_mentah.oer_realistis < basis - 5.0

    urut = []
    for pct in [0, 10, 20, 30, 40, 50]:
        h = hitung({"mentah": pct / 100, "masak": 1 - pct / 100}, berat)
        urut.append(h.potensi_kg)
    hasil["potensi_per_persen_mentah"] = urut
    hasil["lulus_3"] = all(urut[i] > urut[i + 1] for i in range(len(urut) - 1))
    hasil["semua_lulus"] = all(hasil[k] for k in ("lulus_1", "lulus_2", "lulus_3"))

    if verbose:
        print("=" * 62)
        print("UJI AKAL SEHAT — MODEL 4")
        print("=" * 62)
        print(f"basis matang (dari yaml)   : {basis:.2f} poin OER")
        print(f"1. muatan 100% matang      : {hasil['semua_matang_oer']:.2f} "
              f"-> {'LULUS' if hasil['lulus_1'] else 'GAGAL'}")
        print(f"2. muatan 100% mentah      : {hasil['semua_mentah_oer']:.2f} "
              f"-> {'LULUS' if hasil['lulus_2'] else 'GAGAL'}")
        print(f"3. monoton turun            "
              f"-> {'LULUS' if hasil['lulus_3'] else 'GAGAL'}")
        print()
        print("   % mentah   potensi (kg, berat 6.000 kg)")
        for pct, kg in zip([0, 10, 20, 30, 40, 50], urut):
            print(f"   {pct:8d}   {kg:10.1f}")
        print("=" * 62)
    return hasil


if __name__ == "__main__":
    sanity_check()

    print()
    print("=" * 62)
    print("CONTOH DENGAN SELANG (keluaran Model 2)")
    print("=" * 62)
    komposisi = {
        "mentah":        (0.09, 0.12, 0.15),
        "kurang_masak":  (0.14, 0.18, 0.22),
        "masak":         (0.60, 0.65, 0.70),
        "terlalu_masak": (0.03, 0.05, 0.08),
    }
    for mode in ("terverifikasi", "lengkap"):
        h = hitung_dengan_selang(komposisi, 6000.0, mode=mode)
        print(f"\nmode = {mode}")
        print(f"  OER teoretis   : {h.oer_teoretis:.2f} poin")
        print(f"  rugi komposisi : {h.rugi_komposisi:+.3f} poin")
        print(f"  OER realistis  : {h.oer_realistis:.3f} poin")
        print(f"  POTENSI MINYAK : {h.potensi_kg:.0f} kg "
              f"(selang 90%: {h.potensi_lo:.0f} - {h.potensi_hi:.0f}, "
              f"lebar {h.lebar_selang:.0f} kg)")
        print(f"  dasar sah      : {h.dasar_sah}")
        if h.penalti_dilewati:
            print(f"  DILEWATI       : {', '.join(h.penalti_dilewati)}")


# --------------------------------------------------------------------
# Permukaan resmi (GATE AI-2). Backend memanggil nama ini.
# --------------------------------------------------------------------

def estimate(komposisi_selang: dict[str, tuple[float, float, float]],
             berat_bruto_kg: float, *, mode: str = "terverifikasi",
             koreksi=None, **kw) -> PotensiMinyak:
    """Potensi minyak berselang, dari keluaran `composition.infer`.

    `koreksi` adalah `KoreksiTerpelajar` yang sudah dilatih, atau None.
    Kalau diberikan, hasilnya adalah formula DITAMBAH koreksi terbatas —
    tidak pernah koreksi menggantikan formula. Bila koreksi menyalakan
    alarm, pesannya diteruskan apa adanya alih-alih ditelan, karena
    alarm itu justru gunanya.
    """
    titik = hitung_dengan_selang(komposisi_selang, berat_bruto_kg,
                                 mode=mode, **kw)
    if koreksi is None:
        return titik

    komposisi = {k: v[1] for k, v in komposisi_selang.items()}
    h = koreksi.terapkan(komposisi)
    geser = h.koreksi_poin
    d = titik.sebagai_dict()
    d["oer_realistis"] = titik.oer_realistis + geser
    for k in ("potensi_kg", "potensi_lo", "potensi_hi"):
        d[k] = d[k] + berat_bruto_kg * geser / 100.0
    return PotensiMinyak(**d)
