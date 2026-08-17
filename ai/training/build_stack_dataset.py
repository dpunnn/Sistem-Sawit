"""Generator penumpukan sintetik — bahan latih Model 2.

## Masalah yang diselesaikan

Kamera hanya melihat lapisan permukaan tumpukan. Model 2 harus menaksir
komposisi SELURUH muatan dari yang terlihat itu. Persoalannya, tidak ada
data "komposisi seluruh muatan" yang sebenarnya — mengukurnya berarti
membongkar dan menyortir satu truk penuh secara manual.

Jalan keluarnya: **membuat datanya sendiri**. Kalau kita yang menyusun
tumpukan, kita tahu kebenarannya dengan sempurna. Yang dipakai adalah
label tandan NYATA dari dataset (11.102 crop berlabel), disusun menjadi
muatan buatan dengan komposisi yang kita tentukan.

## Dua mekanisme bias yang dimodelkan

Yang dipelajari Model 2 bukan sekadar "permukaan = keseluruhan", melainkan
**seberapa besar permukaan menipu**. Dua sumbernya:

1. **Penumpukan** — tandan yang lebih besar/berat cenderung tenggelam,
   sehingga kurang terwakili di permukaan.

   PERINGATAN PENTING: pemeriksaan atas data nyata menunjukkan ukuran
   kotak antar tingkat kematangan hanya berselisih 11% (rasio 1,114).
   Dasar empiris mekanisme ini LEMAH. Karena itu kekuatannya dijadikan
   parameter yang diacak — termasuk nilai nol — dan ketahanan model
   terhadap kesalahan asumsi ini diuji terpisah.

2. **Penataan sengaja** — buah bagus ditaruh di atas. Ini perilaku
   manusia, bukan fisika, jadi hanya muncul pada sebagian muatan.

## Batas yang tidak bisa dilewati siapa pun

Dengan hanya n tandan terlihat dari muatan berisi ratusan, galat baku
proporsi adalah sqrt(p(1-p)/n). Itu **lantai teoretis**: model yang
melaporkan selang lebih sempit dari itu sedang berbohong, bukan pintar.
Nilai tambah Model 2 adalah mengoreksi BIAS, bukan mengecilkan ragam.

Jalankan:
    python ai/training/build_stack_dataset.py
    python ai/training/build_stack_dataset.py --n-muatan 60000 --seed 7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CROPS = ROOT / "data" / "processed" / "crops_ordinal" / "index.csv"
OUT = ROOT / "data" / "processed" / "stack_sintetik"

N_KELAS = 4
NAMA_KELAS = ["mentah", "kurang_masak", "masak", "terlalu_masak"]

# Rentang parameter bias. Model dilatih di seluruh rentang ini supaya
# tidak bergantung pada satu asumsi tunggal.
RENTANG = dict(
    n_tandan=(80, 320),          # tandan per muatan truk
    fraksi_terlihat=(0.06, 0.35),  # bagian yang tertangkap kamera
    kekuatan_tenggelam=(0.0, 2.5),  # 0 = tidak ada bias ukuran
    peluang_penataan=0.30,        # proporsi muatan yang ditata sengaja
    kekuatan_penataan=(0.5, 3.0),  # penguatan keterlihatan buah bagus
)


def ukuran_relatif_nyata(path: Path = CROPS) -> np.ndarray:
    """Ukuran kotak relatif per tingkat, dari data NYATA.

    Dipakai sebagai proksi berat untuk mekanisme tenggelam. Nilainya
    diambil dari data alih-alih dikarang, meski selisihnya kecil.
    """
    if not path.exists():
        # nilai hasil pengukuran, dicantumkan agar generator tetap jalan
        # tanpa berkas crop
        return np.array([0.993, 0.935, 1.041, 1.007])
    d = pd.read_csv(path)
    d["luas"] = d["w"] * d["h"]
    med = d.groupby("ordinal")["luas"].median().reindex(range(N_KELAS))
    return (med / med.median()).to_numpy(dtype=float)


def _pilih_tanpa_pengembalian(rng, bobot: np.ndarray, k: int) -> np.ndarray:
    """Pencuplikan berbobot tanpa pengembalian (trik Gumbel top-k).

    Jauh lebih cepat daripada memanggil rng.choice berulang, dan hasilnya
    setara secara distribusi.
    """
    g = rng.gumbel(size=bobot.shape)
    kunci = np.log(np.clip(bobot, 1e-12, None)) + g
    return np.argpartition(-kunci, k - 1)[:k]


def satu_muatan(rng, ukuran_rel: np.ndarray, alpha_dirichlet=None) -> dict:
    """Bangkitkan satu muatan buatan beserta kebenarannya."""
    # komposisi sebenarnya — Dirichlet supaya mencakup dari muatan bersih
    # sampai muatan yang didominasi satu tingkat
    if alpha_dirichlet is None:
        # alpha kecil -> komposisi ekstrem; besar -> merata.
        alpha_dirichlet = rng.uniform(0.4, 3.0, size=N_KELAS)
    komposisi_benar = rng.dirichlet(alpha_dirichlet)

    n = int(rng.integers(*RENTANG["n_tandan"]))
    kelas = rng.choice(N_KELAS, size=n, p=komposisi_benar)

    # --- bobot keterlihatan ---
    kekuatan_tenggelam = rng.uniform(*RENTANG["kekuatan_tenggelam"])
    bobot = ukuran_rel[kelas] ** (-kekuatan_tenggelam)

    ditata = rng.random() < RENTANG["peluang_penataan"]
    kekuatan_penataan = 0.0
    if ditata:
        kekuatan_penataan = rng.uniform(*RENTANG["kekuatan_penataan"])
        # "buah bagus" = masak (indeks 2); kadang kurang masak ikut diangkat
        bagus = (kelas == 2) | ((kelas == 1) & (rng.random() < 0.4))
        bobot = bobot * np.where(bagus, 1.0 + kekuatan_penataan, 1.0)

    fraksi = rng.uniform(*RENTANG["fraksi_terlihat"])
    n_terlihat = max(1, min(n, int(round(n * fraksi))))
    idx = _pilih_tanpa_pengembalian(rng, bobot, n_terlihat)
    terlihat = kelas[idx]

    hitung_terlihat = np.bincount(terlihat, minlength=N_KELAS)
    komposisi_terlihat = hitung_terlihat / hitung_terlihat.sum()
    komposisi_aktual = np.bincount(kelas, minlength=N_KELAS) / n

    return {
        # --- fitur yang tersedia saat inferensi ---
        **{f"lihat_{NAMA_KELAS[i]}": komposisi_terlihat[i] for i in range(N_KELAS)},
        "n_terlihat": n_terlihat,
        "n_tandan_taksiran": n,      # dari berat bruto / berat rata-rata tandan
        # --- target: kebenaran yang hanya diketahui simulator ---
        **{f"benar_{NAMA_KELAS[i]}": komposisi_aktual[i] for i in range(N_KELAS)},
        # --- parameter bias, untuk analisis ketahanan (BUKAN fitur) ---
        "_fraksi_terlihat": fraksi,
        "_kekuatan_tenggelam": kekuatan_tenggelam,
        "_ditata": bool(ditata),
        "_kekuatan_penataan": kekuatan_penataan,
    }


def bangkitkan(n_muatan: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ukuran_rel = ukuran_relatif_nyata()
    return pd.DataFrame([satu_muatan(rng, ukuran_rel) for _ in range(n_muatan)])


def lantai_pencuplikan(n_terlihat: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Galat baku proporsi — lantai teoretis lebar selang.

    Tidak ada model yang bisa melaporkan selang lebih sempit dari ini
    secara jujur. Dipakai sebagai tolok ukur kalibrasi Model 2.
    """
    return np.sqrt(np.clip(p * (1 - p), 0, None) / np.maximum(n_terlihat, 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-muatan", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    ukuran_rel = ukuran_relatif_nyata()
    print("ukuran relatif per tingkat (dari data nyata):")
    for i, n in enumerate(NAMA_KELAS):
        print(f"  {n:14s} {ukuran_rel[i]:.3f}")
    print(f"  rasio maks/min : {ukuran_rel.max()/ukuran_rel.min():.3f}"
          "   <- dasar empiris mekanisme tenggelam LEMAH")
    print()

    # Latih & validasi dari seed yang sama; UJI dari seed berbeda supaya
    # tidak ada muatan yang sama muncul di dua sisi.
    df = bangkitkan(args.n_muatan, seed=args.seed)
    n_tr = int(len(df) * 0.8)
    df.loc[:n_tr - 1, "split"] = "train"
    df.loc[n_tr:, "split"] = "val"
    df_uji = bangkitkan(max(4000, args.n_muatan // 8), seed=args.seed + 1000)
    df_uji["split"] = "test"
    semua = pd.concat([df, df_uji], ignore_index=True)

    semua.to_parquet(OUT / "muatan_sintetik.parquet", index=False)

    print(semua.groupby("split").size().rename("muatan").to_frame().T.to_string())
    print()
    print("=== sebaran fitur (train) ===")
    tr = semua[semua.split == "train"]
    kol = [f"lihat_{n}" for n in NAMA_KELAS] + ["n_terlihat", "n_tandan_taksiran"]
    print(tr[kol].describe().loc[["mean", "std", "min", "max"]].round(3).to_string())
    print()
    print("=== seberapa besar permukaan menipu? ===")
    for i, n in enumerate(NAMA_KELAS):
        bias = (tr[f"lihat_{n}"] - tr[f"benar_{n}"])
        print(f"  {n:14s} bias rata-rata {bias.mean():+.4f}  "
              f"|bias| median {bias.abs().median():.4f}  "
              f"maks {bias.abs().max():.4f}")
    print()
    print("=== lantai pencuplikan teoretis (train) ===")
    for p_uji in [0.1, 0.2, 0.35]:
        se = lantai_pencuplikan(tr["n_terlihat"].to_numpy(), np.full(len(tr), p_uji))
        print(f"  p={p_uji:.2f} -> galat baku median {se.mean():.4f}  "
              f"(selang 90% ~ +/-{1.645*np.median(se):.3f})")
    print()
    print(f"[ok] {OUT / 'muatan_sintetik.parquet'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
