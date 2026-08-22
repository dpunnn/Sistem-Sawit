"""AI-2.2.3 — koreksi terpelajar DI ATAS formula, bukan menggantikannya.

## Kenapa tidak menggantikan saja dengan model

Formula potensi minyak bisa dihitung ulang dengan kalkulator oleh
siapa pun yang mempersoalkan hasilnya. Sifat itu bukan kekurangan yang
belum sempat diperbaiki — itu satu-satunya alasan angkanya boleh dipakai
dalam sengketa harga. Mengganti formula dengan regresi berarti menukar
alat bukti dengan kotak hitam.

Tetapi formula juga tidak bisa belajar. Tiap pabrik punya varietas,
umur tanaman, dan jarak kebun yang berbeda, dan koefisien terbit tidak
menangkap itu.

Jalan tengahnya: formula tetap jadi tulang punggung, koefisien terpelajar
hanya menambahkan SELISIH di atasnya —

    OER = formula(komposisi)  +  koreksi(komposisi)
          \\_____ terlacak ____/    \\__ maksimum +/- batas __/

## Tiga pagar yang membuat ini tetap alat bukti

1. **Terbatas.** Koreksi dipotong pada `BATAS_POIN`. Model tidak akan
   pernah bisa menggeser hasil lebih dari itu, berapa pun yakinnya.

2. **Terpisah.** Nilai formula dan nilai koreksi dilaporkan terpisah,
   tidak pernah menyatu jadi satu angka. Yang membaca selalu bisa
   melihat berapa banyak yang datang dari koefisien terbit dan berapa
   dari data pabrik.

3. **Berbunyi.** Kalau koreksi terpelajar menyimpang jauh dari nol,
   itu bukan keberhasilan belajar melainkan SINYAL ADA YANG SALAH:
   entah komposisi salah ukur, entah koefisien terbit tidak berlaku di
   pabrik itu, entah ada kehilangan sisi pabrik yang bocor masuk ke
   sisi pemasok. Kelas ini menolak dipakai diam-diam dalam keadaan itu.

## Yang HARAM dipelajari

Fitur koreksi hanya boleh berisi hal tentang BUAH YANG MASUK. Kalau
jam restan atau setelan sterilisasi ikut masuk sebagai fitur, koreksi
akan menyerap kehilangan sisi pabrik ke dalam potensi sisi pemasok --
persis penghitungan ganda yang dilarang seluruh sistem ini. Daftar
fitur dikunci di `FITUR` dan dijaga oleh uji.

Jalankan:
    python ai/perception/correction.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.perception.potential import NAMA_KELAS, hitung

# Koreksi tidak boleh menggeser rendemen lebih dari sepertiga poin.
# Sebagai pembanding: 1% buah mentah saja bernilai 0,13 poin, jadi batas
# ini setara sekitar 2,5% kesalahan komposisi -- cukup untuk menyerap
# kekhasan satu pabrik, jauh dari cukup untuk membalik kesimpulan.
BATAS_POIN = 0.33

# Di atas ini, koreksi dianggap gejala kerusakan dan bukan pembelajaran.
AMBANG_ALARM = 0.25

# Hanya tentang buah yang masuk. Menambahkan apa pun tentang proses
# pabrik ke daftar ini akan melanggar pemisahan tanggung jawab.
FITUR = list(NAMA_KELAS)

# Fitur yang secara eksplisit DILARANG, dijaga oleh uji supaya penambahan
# tidak sengaja tertangkap sebelum sampai produksi.
FITUR_TERLARANG = {
    "jam_restan", "restan", "gangguan", "kadar", "aliran", "oer_aktual",
    "minyak_kg", "berat_bruto_kg", "suhu", "tekanan", "throughput",
}


class KoreksiError(RuntimeError):
    pass


@dataclass
class HasilKoreksi:
    """Keluaran koreksi, dengan asal-usul tiap bagian tetap terlihat."""

    oer_formula: float
    koreksi_poin: float          # sudah dipotong pada BATAS_POIN
    koreksi_mentah: float        # sebelum dipotong — untuk audit
    oer_total: float
    terpotong: bool
    alarm: bool
    pesan: list[str] = field(default_factory=list)

    @property
    def porsi_terpelajar(self) -> float:
        """Berapa bagian hasil akhir yang datang dari data, bukan formula."""
        return abs(self.koreksi_poin) / max(abs(self.oer_total), 1e-9)


class KoreksiTerpelajar:
    """Regresi ridge atas SISA formula, bukan atas rendemen itu sendiri.

    Belajar dari sisa punya sifat yang penting: kalau formula sudah benar,
    tidak ada yang bisa dipelajari dan koreksinya menuju nol dengan
    sendirinya. Model yang belajar langsung dari rendemen tidak punya
    perilaku itu — ia akan selalu menemukan sesuatu, termasuk dari derau.
    """

    def __init__(self, *, lambda_ridge: float = 1.0,
                 batas: float = BATAS_POIN, mode: str = "terverifikasi"):
        self.lambda_ridge = lambda_ridge
        self.batas = batas
        self.mode = mode
        self.bobot_: np.ndarray | None = None
        self.intersep_: float = 0.0
        self.sisa_latih_: dict = {}

    # -- utilitas ----------------------------------------------------

    @staticmethod
    def _periksa_fitur(kolom) -> None:
        for k in kolom:
            dasar = str(k).lower()
            if any(t in dasar for t in FITUR_TERLARANG):
                raise KoreksiError(
                    f"fitur '{k}' menyangkut proses pabrik. Memasukkannya "
                    "membuat koreksi menyerap kehilangan sisi pabrik ke "
                    "dalam potensi sisi pemasok — penghitungan ganda yang "
                    "dilarang seluruh sistem ini.")

    def _matriks(self, komposisi_batch) -> np.ndarray:
        X = np.array([[max(0.0, k.get(n, 0.0)) for n in FITUR]
                      for k in komposisi_batch], dtype=float)
        jml = X.sum(axis=1, keepdims=True)
        return np.divide(X, np.where(jml == 0, 1, jml)) * 100.0

    def _formula(self, komposisi_batch) -> np.ndarray:
        return np.array([hitung(k, 1000.0, mode=self.mode).oer_realistis
                         for k in komposisi_batch])

    # -- pembelajaran ------------------------------------------------

    def latih(self, komposisi_batch: list[dict], oer_teramati) -> "KoreksiTerpelajar":
        """Pelajari sisa antara formula dan rendemen yang benar-benar terjadi.

        `oer_teramati` harus sudah BERSIH dari kehilangan sisi pabrik.
        Kalau tidak, yang dipelajari bukan kekhasan buah melainkan
        kebocoran pabrik — dan itu akan ditagihkan ke petani.
        """
        self._periksa_fitur(FITUR)
        X = self._matriks(komposisi_batch)
        y = np.asarray(oer_teramati, dtype=float) - self._formula(komposisi_batch)

        # ridge dengan intersep tidak ikut dihukum
        Xc = X - X.mean(axis=0)
        yc = y - y.mean()
        A = Xc.T @ Xc + self.lambda_ridge * np.eye(X.shape[1])
        self.bobot_ = np.linalg.solve(A, Xc.T @ yc)
        self.intersep_ = float(y.mean() - X.mean(axis=0) @ self.bobot_)

        pred = X @ self.bobot_ + self.intersep_
        self.sisa_latih_ = {
            "n": len(y),
            "sisa_rerata": float(y.mean()),
            "sisa_absolut_rerata": float(np.abs(y).mean()),
            "koreksi_absolut_rerata": float(np.abs(pred).mean()),
            "koreksi_maks": float(np.abs(pred).max()),
            "sisa_terjelaskan": float(
                1 - np.var(y - pred) / max(np.var(y), 1e-12)),
        }
        return self

    # -- penerapan ---------------------------------------------------

    def terapkan(self, komposisi: dict[str, float]) -> HasilKoreksi:
        if self.bobot_ is None:
            raise KoreksiError("panggil latih() dulu")

        oer_formula = hitung(komposisi, 1000.0, mode=self.mode).oer_realistis
        x = self._matriks([komposisi])[0]
        mentah = float(x @ self.bobot_ + self.intersep_)
        koreksi = float(np.clip(mentah, -self.batas, self.batas))

        pesan: list[str] = []
        terpotong = abs(mentah) > self.batas
        if terpotong:
            pesan.append(
                f"koreksi mentah {mentah:+.3f} poin melebihi batas "
                f"+/-{self.batas:.2f} dan dipotong. Formula tetap memegang "
                "hasil akhir.")
        alarm = abs(mentah) > AMBANG_ALARM
        if alarm:
            pesan.append(
                f"ALARM: koreksi {mentah:+.3f} poin menyimpang jauh dari nol. "
                "Ini bukan tanda model belajar dengan baik, melainkan sinyal "
                "ada yang salah — periksa pengukuran komposisi, keberlakuan "
                "koefisien terbit di pabrik ini, atau kebocoran kehilangan "
                "sisi pabrik ke sisi pemasok.")

        return HasilKoreksi(
            oer_formula=oer_formula, koreksi_poin=koreksi,
            koreksi_mentah=mentah, oer_total=oer_formula + koreksi,
            terpotong=terpotong, alarm=alarm, pesan=pesan)


# --------------------------------------------------------------------

def _peragaan() -> None:
    rng = np.random.default_rng(42)

    def acak(n):
        out = []
        for _ in range(n):
            m = rng.uniform(0.0, 0.30)
            km = rng.uniform(0.0, 0.30)
            tm = rng.uniform(0.0, 0.12)
            out.append({"mentah": m, "kurang_masak": km, "terlalu_masak": tm,
                        "masak": max(0.0, 1 - m - km - tm)})
        return out

    L = 70
    komposisi = acak(600)
    formula = np.array([hitung(k, 1000.0).oer_realistis for k in komposisi])

    print("=" * L)
    print("PERCOBAAN 1 — pabrik yang koefisien terbitnya memang berlaku")
    print("=" * L)
    y1 = formula + rng.normal(0, 0.10, size=len(formula))   # derau ukur saja
    m1 = KoreksiTerpelajar().latih(komposisi, y1)
    print(f"  sisa |rata-rata| yang tersedia : "
          f"{m1.sisa_latih_['sisa_absolut_rerata']:.3f} poin")
    print(f"  koreksi |rata-rata| dipelajari : "
          f"{m1.sisa_latih_['koreksi_absolut_rerata']:.3f} poin")
    print(f"  ragam sisa yang terjelaskan    : "
          f"{m1.sisa_latih_['sisa_terjelaskan']:.3f}")
    h = m1.terapkan({"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                     "terlalu_masak": 0.05})
    print(f"  contoh: formula {h.oer_formula:.3f} + koreksi "
          f"{h.koreksi_poin:+.3f} = {h.oer_total:.3f} poin")
    print(f"  porsi hasil yang datang dari data: {h.porsi_terpelajar:.2%}")
    print("  -> koreksi mendekati nol. Formula tidak meninggalkan sinyal")
    print("     sistematis yang bisa dipanen; belajar tidak menambah apa-apa.")

    print()
    print("=" * L)
    print("PERCOBAAN 2 — pabrik dengan kekhasan nyata (varietas lebih baik)")
    print("=" * L)
    bias = 0.15
    y2 = formula + bias + rng.normal(0, 0.10, size=len(formula))
    m2 = KoreksiTerpelajar().latih(komposisi, y2)
    h2 = m2.terapkan({"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                      "terlalu_masak": 0.05})
    print(f"  kekhasan yang ditanam          : {bias:+.3f} poin")
    print(f"  koreksi yang dipulihkan        : {h2.koreksi_poin:+.3f} poin")
    print(f"  alarm berbunyi                 : {'YA' if h2.alarm else 'tidak'}")
    print("  -> kekhasan sebesar ini masih wajar, jadi dipelajari tanpa alarm.")

    print()
    print("=" * L)
    print("PERCOBAAN 3 — kehilangan pabrik bocor ke sisi pemasok")
    print("=" * L)
    print("  Ini yang harus TERTANGKAP, bukan dipelajari diam-diam:")
    print("  rendemen teramati dipotong 0,60 poin oleh sebab sisi pabrik.")
    y3 = formula - 0.60 + rng.normal(0, 0.10, size=len(formula))
    m3 = KoreksiTerpelajar().latih(komposisi, y3)
    h3 = m3.terapkan({"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                      "terlalu_masak": 0.05})
    print(f"  koreksi mentah                 : {h3.koreksi_mentah:+.3f} poin")
    print(f"  setelah dipotong batas         : {h3.koreksi_poin:+.3f} poin")
    print(f"  terpotong                      : {'YA' if h3.terpotong else 'tidak'}")
    print(f"  alarm berbunyi                 : {'YA' if h3.alarm else 'tidak'}")
    for p in h3.pesan:
        print(f"    ! {p}")

    print()
    print("=" * L)
    print("PERCOBAAN 4 — fitur proses pabrik ditolak mentah-mentah")
    print("=" * L)
    try:
        KoreksiTerpelajar._periksa_fitur(["mentah", "jam_restan"])
        print("  GAGAL — fitur terlarang lolos")
    except KoreksiError as e:
        print(f"  OK — ditolak: {str(e)[:64]}…")
    print("=" * L)


if __name__ == "__main__":
    _peragaan()
