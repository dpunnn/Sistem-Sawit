"""Uji kalibrasi selang — apakah selangnya jujur?

Sebuah selang yang mengaku 90% tetapi hanya memuat nilai sebenarnya 87%
dari waktu adalah janji palsu. Karena keluaran sistem ini dipakai untuk
memotong uang orang, janji palsu itu punya korban.

Modul ini menyediakan alat ukurnya, terpisah dari model yang diukur.
Pemisahan itu disengaja: alat ukur yang tinggal serumah dengan model
yang diukurnya cenderung ikut menyesuaikan diri.

## Dua pemeriksaan yang harus lolos bersamaan

1. **Cakupan** — selang 1-alpha harus benar-benar memuat nilai
   sebenarnya sekitar 1-alpha dari waktu. Kurang dari itu berarti
   terlalu percaya diri; jauh lebih dari itu berarti tidak berguna.

2. **Lebar terhadap lantai pencuplikan** — dengan n tandan terlihat
   dari muatan berisi ratusan, galat baku proporsi adalah
   `sqrt(p(1-p)/n)`. Itu batas teoretis. Selang yang lebih sempit dari
   lantai bukan tanda model yang pintar, melainkan model yang berbohong.

Pemeriksaan kedua yang membuat modul ini lebih dari sekadar penghitung
persentase: cakupan 90% mudah dicapai dengan melebarkan selang
sebesar-besarnya. Yang sulit adalah mencapainya SAMBIL tetap sempit.

Jalankan:
    python ai/evaluation/calibration.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

Z_90 = 1.6448536269514722   # kuantil normal dua sisi untuk selang 90%


@dataclass
class HasilKalibrasi:
    nama: str
    cakupan: float
    target: float
    lebar_rerata: float
    lantai_rerata: float | None = None

    @property
    def rasio_lantai(self) -> float | None:
        if not self.lantai_rerata:
            return None
        return self.lebar_rerata / self.lantai_rerata

    @property
    def terlalu_percaya_diri(self) -> bool:
        """Cakupan meleset ke bawah lebih dari 2 poin persen."""
        return self.cakupan < self.target - 0.02

    @property
    def mustahil(self) -> bool:
        """Selang lebih sempit daripada yang dimungkinkan pencuplikan.

        Ambangnya 0,95 dan bukan 1,00 karena lantai dihitung dengan
        pendekatan normal; sedikit di bawah satu masih bisa dijelaskan
        pendekatan itu, jauh di bawah satu tidak.
        """
        r = self.rasio_lantai
        return r is not None and r < 0.95


def lantai_pencuplikan(n_terlihat: np.ndarray, p: np.ndarray,
                       z: float = Z_90) -> np.ndarray:
    """Lebar selang tersempit yang masih jujur, untuk proporsi.

    Bukan sifat model, melainkan sifat pencuplikan. Model apa pun —
    sekarang maupun sepuluh tahun lagi — terikat batas yang sama.
    """
    se = np.sqrt(np.clip(p * (1 - p), 0, None) / np.maximum(n_terlihat, 1))
    return 2 * z * se


def periksa(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, *,
            nama: str = "", target: float = 0.90,
            n_terlihat: np.ndarray | None = None) -> HasilKalibrasi:
    """Ukur cakupan dan lebar satu selang terhadap nilai sebenarnya."""
    y, lo, hi = np.asarray(y), np.asarray(lo), np.asarray(hi)
    if not (len(y) == len(lo) == len(hi)):
        raise ValueError("panjang y, lo, dan hi harus sama")
    lantai = None
    if n_terlihat is not None:
        lantai = float(np.mean(lantai_pencuplikan(np.asarray(n_terlihat), y)))
    return HasilKalibrasi(
        nama=nama,
        cakupan=float(np.mean((y >= lo) & (y <= hi))),
        target=target,
        lebar_rerata=float(np.mean(hi - lo)),
        lantai_rerata=lantai,
    )


def periksa_banyak(hasil: list[HasilKalibrasi]) -> pd.DataFrame:
    return pd.DataFrame([{
        "besaran": h.nama,
        "cakupan": round(h.cakupan, 4),
        "target": h.target,
        "lebar": round(h.lebar_rerata, 4),
        "lantai": round(h.lantai_rerata, 4) if h.lantai_rerata else None,
        "rasio": round(h.rasio_lantai, 3) if h.rasio_lantai else None,
        "vonis": ("MUSTAHIL" if h.mustahil
                  else "TERLALU PERCAYA DIRI" if h.terlalu_percaya_diri
                  else "JUJUR"),
    } for h in hasil])


def skor_conformal(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Skor konformitas CQR: E_i = max(lo_i - y_i, y_i - hi_i).

    Nilai positif berarti nilai sebenarnya berada DI LUAR selang.
    Kuantil ke-(1-alpha) dari skor ini adalah jarak yang perlu
    ditambahkan agar cakupan terjamin secara empiris.
    """
    return np.maximum(np.asarray(lo) - np.asarray(y),
                      np.asarray(y) - np.asarray(hi))


def koreksi_conformal(y: np.ndarray, lo: np.ndarray, hi: np.ndarray,
                      alpha: float = 0.10) -> float:
    """Berapa lebar tambahan yang dibutuhkan, dari data validasi.

    Faktor (n+1)/n menjaga jaminan cakupan pada sampel berhingga —
    tanpa itu jaminannya hanya berlaku asimtotik, dan data validasi
    tidak pernah tak hingga.
    """
    n = len(y)
    tingkat = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(skor_conformal(y, lo, hi), tingkat))


def _peragaan() -> None:
    """Periksa Model 2 yang sudah terlatih, sebelum dan sesudah kalibrasi."""
    from ai.perception import composition as M2

    root = Path(__file__).resolve().parents[2]
    df = pd.read_parquet(root / "data" / "processed" / "stack_sintetik"
                         / "muatan_sintetik.parquet")
    te = df[df.split == "test"]
    model = M2.Model2.muat()

    n_terlihat = te["n_terlihat"].to_numpy()
    tanpa, dengan = [], []
    for nama in M2.NAMA_KELAS:
        y = te[f"benar_{nama}"].to_numpy()
        X = M2.siapkan_fitur(te)
        lo = model.model[(nama, M2.KUANTIL[0])].predict(X)
        hi = model.model[(nama, M2.KUANTIL[2])].predict(X)
        k = model.koreksi.get(nama, 0.0)
        tanpa.append(periksa(y, lo, hi, nama=nama, n_terlihat=n_terlihat))
        dengan.append(periksa(y, lo - k, hi + k, nama=nama,
                              n_terlihat=n_terlihat))

    print("=" * 74)
    print("SEBELUM kalibrasi conformal")
    print("=" * 74)
    print(periksa_banyak(tanpa).to_string(index=False))
    print()
    print("=" * 74)
    print("SESUDAH kalibrasi conformal")
    print("=" * 74)
    print(periksa_banyak(dengan).to_string(index=False))
    print()
    print("Rasio mendekati 1,0 berarti selang berada tepat di lantai")
    print("pencuplikan: seluruh informasi yang tersedia sudah diperas,")
    print("dan tidak ada pengakuan tahu lebih banyak dari yang mungkin.")


if __name__ == "__main__":
    _peragaan()
