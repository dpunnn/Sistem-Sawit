"""MODEL 6 — Atribusi kehilangan.  *** PALING NOVEL ***

Memecah selisih jadi penyebab, masing-masing DENGAN SELANG.

ATURAN EMAS:
  SALAH : "0,7 poin hilang karena buah mentah pemasok A"
  BENAR : "0,7 +/- 0,25 poin — keyakinan sedang. Cukup untuk bahan
           diskusi, BELUM cukup untuk memotong pembayaran."

Baris "tidak terjelaskan" WAJIB ada. Jangan dipaksa nol.

## Yang membuat bagian ini berbeda dari klasifikasi biasa

Model 6 TIDAK PERNAH melihat label gangguan. Ia hanya melihat yang
terlihat di pabrik nyata: delapan hasil ukur laboratorium per hari,
komposisi taksiran, dan angka timbangan. Dari situ ia harus:

1. menemukan sendiri berapa banyak pola kerusakan yang ada,
2. memulihkan bentuk tiap pola (aliran mana naik, seberapa),
3. menamai hari-hari berikutnya dengan pola itu, DAN
4. mengaku tidak tahu ketika polanya tidak cocok dengan apa pun.

Langkah 2 itu yang disebut *rule recovery*: sistem menemukan kembali
hubungan sebab-akibat mekanis yang tidak pernah diberitahukan padanya.
Bisa-tidaknya ia melakukan itu diukur di ai/evaluation/rule_recovery.py
dengan membandingkan pola temuan terhadap gangguan yang ditanam.

## Kenapa tidak memakai klasifikasi berlabel saja

Karena di pabrik nyata labelnya tidak ada. Tidak ada operator yang
mencatat "hari ini sterilizer kurang tekanan" dalam bentuk yang bisa
dilatih. Metode yang butuh label hanya bisa didemokan, tidak bisa
dipasang. Metode tanpa label bisa dipasang hari pertama.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.simulator.mill import ALIRAN

# Ambang keyakinan. Angka-angka ini adalah pilihan kebijakan, bukan
# temuan — dan diletakkan di satu tempat supaya bisa diperdebatkan.
AMBANG_TINGGI = 0.75
AMBANG_SEDANG = 0.50

# Batas di bawah ini, sebuah hari dianggap normal dan tidak dituduh
# apa-apa. Dinyatakan dalam simpangan baku robust.
AMBANG_ANOMALI = 2.5


@dataclass
class Dugaan:
    """Satu kemungkinan penyebab, lengkap dengan kejujurannya."""

    nama: str
    kemiripan: float             # 0-1, kecocokan dengan pola tersimpan
    poin: float                  # kehilangan yang dijelaskan pola ini
    poin_lo: float
    poin_hi: float
    aliran_utama: list[str]

    @property
    def keyakinan(self) -> str:
        if self.kemiripan >= AMBANG_TINGGI:
            return "tinggi"
        if self.kemiripan >= AMBANG_SEDANG:
            return "sedang"
        return "rendah"

    @property
    def boleh_untuk_potongan(self) -> bool:
        """Satu-satunya tempat aturan ini boleh ditulis.

        Keyakinan tinggi saja tidak cukup — selangnya juga tidak boleh
        melewati nol. Kalau selang memuat nol, kemungkinan "tidak ada
        kehilangan sama sekali" belum tersingkir.
        """
        return self.keyakinan == "tinggi" and self.poin_lo * self.poin_hi > 0

    def kalimat(self) -> str:
        lebar = (self.poin_hi - self.poin_lo) / 2
        s = (f"{self.nama.replace('_', ' ')}: {abs(self.poin):.3f} "
             f"+/- {lebar:.3f} poin — keyakinan {self.keyakinan}")
        if not self.boleh_untuk_potongan:
            s += ". Cukup untuk bahan diskusi, BELUM cukup untuk memotong pembayaran"
        return s


@dataclass
class Diagnosa:
    dugaan: list[Dugaan]
    poin_tak_terjelaskan: float
    anomali: bool
    skor_anomali: float

    def cetak(self) -> None:
        L = 70
        print("-" * L)
        if not self.anomali:
            print(f"  Hari ini dalam batas normal "
                  f"(skor anomali {self.skor_anomali:.2f} < {AMBANG_ANOMALI})")
            print(f"  Tidak ada penyebab yang ditunjuk.")
            print("-" * L)
            return
        print(f"  Skor anomali {self.skor_anomali:.2f} — pola menyimpang terdeteksi")
        for i, d in enumerate(self.dugaan, 1):
            print(f"  {i}. {d.kalimat()}")
            print(f"     aliran yang menandai: {', '.join(d.aliran_utama)}")
        print(f"  sisa tak terjelaskan: {self.poin_tak_terjelaskan:.3f} poin")
        print("-" * L)


class Model6:
    """Menemukan pola kerusakan tanpa pernah diberi label.

    Alur:
      pelajari()  -> dasar normal + pola-pola yang ditemukan sendiri
      diagnosa()  -> menamai satu hari memakai pola itu
    """

    def __init__(self, *, ambang_anomali: float = AMBANG_ANOMALI,
                 maks_pola: int = 8, seed: int = 42):
        self.ambang_anomali = ambang_anomali
        self.maks_pola = maks_pola
        self.seed = seed
        self.dasar_: np.ndarray | None = None
        self.sebar_: np.ndarray | None = None
        self.pola_: dict[str, np.ndarray] = {}
        self.n_anggota_: dict[str, int] = {}

    # -- utilitas ----------------------------------------------------

    @staticmethod
    def _matriks(df: pd.DataFrame) -> np.ndarray:
        """Ambil delapan hasil ukur aliran, dalam poin positif."""
        kol = [f"poin_{a}" for a in ALIRAN]
        hilang = [k for k in kol if k not in df.columns]
        if hilang:
            raise KeyError(f"kolom aliran tidak lengkap: {hilang}")
        return np.abs(df[kol].to_numpy(dtype=float))

    def _rasio(self, X: np.ndarray) -> np.ndarray:
        """Ubah ke rasio terhadap dasar normal.

        Rasio, bukan selisih. Aliran besar dan aliran kecil jadi setara
        sehingga sludge separator yang naik dua kali lipat tidak
        tenggelam di bawah janjang kosong yang naik 10%.
        """
        return X / np.maximum(self.dasar_, 1e-9)

    # -- pembelajaran ------------------------------------------------

    def pelajari(self, df: pd.DataFrame) -> "Model6":
        """Pelajari dasar normal dan pola-pola kerusakan dari riwayat.

        Kolom `_gangguan` DIBUANG kalau ada — supaya tidak mungkin
        bocor lewat kelalaian.
        """
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics import silhouette_score

        df = df.drop(columns=[c for c in df.columns if c.startswith("_")],
                     errors="ignore")
        X = self._matriks(df)

        # Dasar = median per aliran. Median tahan terhadap hari rusak
        # selama tiap jenis kerusakan tidak menguasai lebih dari
        # separuh hari — syarat yang terpenuhi karena kerusakan datang
        # bergiliran, bukan bersamaan.
        self.dasar_ = np.median(X, axis=0)
        R = self._rasio(X)
        # sebaran robust: MAD diskalakan supaya setara simpangan baku
        self.sebar_ = 1.4826 * np.median(np.abs(R - 1.0), axis=0)
        self.sebar_ = np.maximum(self.sebar_, 1e-6)

        skor = np.max(np.abs(R - 1.0) / self.sebar_, axis=1)
        aneh = skor >= self.ambang_anomali
        if aneh.sum() < 10:
            return self

        # Arah penyimpangan saja, besarnya dibuang. Dua hari dengan
        # kerusakan sama tetapi tingkat keparahan berbeda harus jatuh
        # ke pola yang sama.
        D = R[aneh] - 1.0
        arah = D / np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9)

        # Berapa banyak pola? Ditentukan siluet, bukan ditetapkan.
        # Sistem yang diberi tahu "ada lima kerusakan" sudah setengah
        # diberi jawabannya.
        terbaik, skor_terbaik = None, -1.0
        for k in range(2, min(self.maks_pola, len(arah) - 1) + 1):
            lab = AgglomerativeClustering(
                n_clusters=k, metric="cosine", linkage="average").fit_predict(arah)
            if len(set(lab)) < 2:
                continue
            s = silhouette_score(arah, lab, metric="cosine")
            if s > skor_terbaik:
                terbaik, skor_terbaik = lab, s

        if terbaik is None:
            return self

        self.siluet_ = float(skor_terbaik)
        for k in sorted(set(terbaik)):
            anggota = arah[terbaik == k]
            if len(anggota) < 3:      # pola dari dua hari bukan pola
                continue
            pusat = anggota.mean(axis=0)
            pusat = pusat / max(np.linalg.norm(pusat), 1e-9)
            nama = self._namai(pusat)
            # kalau dua kelompok menghasilkan nama sama, bedakan
            asli, n = nama, 2
            while nama in self.pola_:
                nama, n = f"{asli}_{n}", n + 1
            self.pola_[nama] = pusat
            self.n_anggota_[nama] = int(len(anggota))
        return self

    @staticmethod
    def _namai(pusat: np.ndarray) -> str:
        """Nama deskriptif dari aliran yang paling menonjol.

        Sengaja TIDAK memakai nama gangguan yang sebenarnya. Sistem
        tidak tahu istilah "perebusan kurang matang"; yang ia tahu
        hanyalah aliran mana yang naik bersama-sama. Penerjemahan ke
        istilah pabrik adalah pekerjaan manusia, dan memang seharusnya.
        """
        urut = np.argsort(-pusat)
        naik = [ALIRAN[i] for i in urut[:2] if pusat[i] > 0.1]
        if not naik:
            return "pola_lemah"
        return "naik_" + "+".join(a.split("_")[0] for a in naik)

    # -- diagnosis ---------------------------------------------------

    def diagnosa(self, baris: pd.Series | dict, *,
                 n_bootstrap: int = 400) -> Diagnosa:
        if self.dasar_ is None:
            raise RuntimeError("panggil pelajari() dulu")

        x = np.abs(np.array([float(baris[f"poin_{a}"]) for a in ALIRAN]))
        r = x / np.maximum(self.dasar_, 1e-9)
        d = r - 1.0
        skor = float(np.max(np.abs(d) / self.sebar_))

        if skor < self.ambang_anomali or not self.pola_:
            return Diagnosa(dugaan=[], poin_tak_terjelaskan=0.0,
                            anomali=False, skor_anomali=skor)

        # kelebihan kehilangan hari ini, dalam poin
        lebih = np.maximum(x - self.dasar_, 0.0)
        total_lebih = float(lebih.sum())

        arah = d / max(np.linalg.norm(d), 1e-9)
        rng = np.random.default_rng(self.seed)

        dugaan: list[Dugaan] = []
        for nama, pusat in self.pola_.items():
            mirip = float(np.dot(arah, pusat))
            if mirip <= 0:
                continue
            # bagian kelebihan yang dijelaskan pola ini: proyeksikan
            # kelebihan ke arah pola, jangan pernah melebihi totalnya
            bagian = float(np.clip(mirip, 0, 1)) * total_lebih
            if bagian < 1e-4:
                continue

            # Selang dari ketidakpastian pengukuran laboratorium, bukan
            # dari model. Sumber ragamnya memang di sana: satu contoh
            # ampas kempa tidak pernah memberi angka yang sama dua kali.
            derau = rng.normal(1.0, self.sebar_, size=(n_bootstrap, len(ALIRAN)))
            xb = x * derau
            lb = np.maximum(xb - self.dasar_, 0.0)
            rb = xb / np.maximum(self.dasar_, 1e-9) - 1.0
            nb = np.maximum(np.linalg.norm(rb, axis=1, keepdims=True), 1e-9)
            mb = np.clip((rb / nb) @ pusat, 0, 1)
            sampel = mb * lb.sum(axis=1)

            utama = [ALIRAN[i] for i in np.argsort(-pusat)[:3] if pusat[i] > 0.1]
            dugaan.append(Dugaan(
                nama=nama, kemiripan=mirip, poin=-bagian,
                poin_lo=-float(np.quantile(sampel, 0.95)),
                poin_hi=-float(np.quantile(sampel, 0.05)),
                aliran_utama=utama))

        dugaan.sort(key=lambda z: -z.kemiripan)
        dugaan = dugaan[:3]

        # Yang tidak tertangkap pola mana pun tetap harus muncul.
        terjelaskan = abs(dugaan[0].poin) if dugaan else 0.0
        return Diagnosa(dugaan=dugaan,
                        poin_tak_terjelaskan=-max(0.0, total_lebih - terjelaskan),
                        anomali=True, skor_anomali=skor)

    # -- ringkasan ---------------------------------------------------

    def ringkas(self) -> pd.DataFrame:
        baris = []
        for nama, pusat in self.pola_.items():
            b = {"pola": nama, "n_hari": self.n_anggota_[nama]}
            b.update({a: round(float(v), 3) for a, v in zip(ALIRAN, pusat)})
            baris.append(b)
        return pd.DataFrame(baris)


def _peragaan() -> None:
    from ai.simulator.mill import Pabrik

    df = Pabrik(seed=42).riwayat(400)
    m = Model6().pelajari(df)

    print("=" * 70)
    print("MODEL 6 — pola yang DITEMUKAN SENDIRI dari 400 hari")
    print("(label gangguan tidak pernah dilihat)")
    print("=" * 70)
    print(m.ringkas().to_string(index=False))
    print()
    print(f"siluet kelompok: {getattr(m, 'siluet_', float('nan')):.3f}")
    print()

    for g in ["normal", "perebusan_kurang_matang", "kempa_aus", "cst_dingin"]:
        sub = df[df._gangguan == g]
        if sub.empty:
            continue
        print(f"### hari dengan gangguan sebenarnya: {g} ###")
        m.diagnosa(sub.iloc[0]).cetak()
        print()


if __name__ == "__main__":
    _peragaan()
