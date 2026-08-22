"""MODEL 2 — Dari permukaan ke seluruh muatan.  *** INTI ILMIAH ***

## Persoalannya bukan klasifikasi

Kamera melihat lapisan permukaan; yang dibutuhkan komposisi SELURUH muatan.
Jadi ini **inferensi statistik di bawah observasi parsial** — menaksir
distribusi populasi dari cuplikan yang bias.

## Dua sumber ketidakpastian, dan hanya satu yang bisa dikurangi

1. **Bias sistematis** — permukaan tidak mewakili keseluruhan. Tandan besar
   tenggelam; buah bagus kadang sengaja ditaruh di atas. Bias INI yang
   dikoreksi Model 2.

2. **Galat pencuplikan** — dengan n tandan terlihat dari muatan berisi
   ratusan, galat baku proporsi adalah sqrt(p(1-p)/n). Ini **lantai
   teoretis** yang tidak bisa dilewati model mana pun. Melaporkan selang
   lebih sempit dari lantai ini bukan kepintaran, melainkan kebohongan.

Karena itu keluaran model berupa SELANG, bukan angka tunggal — dan lebar
selangnya diperiksa terhadap lantai pencuplikan sebagai uji kejujuran.

## Bentuk keluaran

Regresi kuantil per tingkat kematangan pada tiga kuantil (0,05 / 0,50 /
0,95), menghasilkan selang 90%. Prediksi tengah dinormalkan agar berjumlah
1; batas selang TIDAK dinormalkan karena masing-masing selang marginal.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "stack_sintetik" / "muatan_sintetik.parquet"
BOBOT = ROOT / "ai" / "weights" / "model2_komposisi.joblib"

NAMA_KELAS = ["mentah", "kurang_masak", "masak", "terlalu_masak"]
KUANTIL = (0.05, 0.50, 0.95)
FITUR = ([f"lihat_{n}" for n in NAMA_KELAS]
         + ["n_terlihat", "n_tandan_taksiran", "fraksi_terlihat"])


@dataclass(frozen=True)
class Selang:
    """Taksiran dengan batas bawah dan atas."""
    nilai: float
    lo: float
    hi: float

    @property
    def lebar(self) -> float:
        return self.hi - self.lo


def siapkan_fitur(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # fraksi terlihat dapat dihitung saat inferensi: jumlah deteksi dibagi
    # taksiran jumlah tandan dari berat bruto
    d["fraksi_terlihat"] = d["n_terlihat"] / d["n_tandan_taksiran"].clip(lower=1)
    return d[FITUR]


def lantai_pencuplikan(n_terlihat, p) -> np.ndarray:
    """Galat baku proporsi — batas bawah lebar selang yang jujur."""
    n_terlihat = np.asarray(n_terlihat, dtype=float)
    p = np.asarray(p, dtype=float)
    return np.sqrt(np.clip(p * (1 - p), 0, None) / np.maximum(n_terlihat, 1))


class Model2:
    """Regresi kuantil per tingkat kematangan."""

    def __init__(self, max_iter: int = 300, seed: int = 42):
        self.max_iter = max_iter
        self.seed = seed
        self.model: dict[tuple[str, float], HistGradientBoostingRegressor] = {}
        # koreksi conformal per kelas; nol berarti belum dikalibrasi
        self.koreksi: dict[str, float] = {}

    def latih(self, df_train: pd.DataFrame, verbose: bool = True) -> "Model2":
        X = siapkan_fitur(df_train)
        for nama in NAMA_KELAS:
            y = df_train[f"benar_{nama}"].to_numpy()
            for q in KUANTIL:
                m = HistGradientBoostingRegressor(
                    loss="quantile", quantile=q, max_iter=self.max_iter,
                    learning_rate=0.08, max_depth=6, min_samples_leaf=40,
                    l2_regularization=1.0, random_state=self.seed,
                    early_stopping=True, validation_fraction=0.1,
                )
                m.fit(X, y)
                self.model[(nama, q)] = m
            if verbose:
                print(f"  {nama:14s} selesai")
        return self

    def prediksi(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """Kembalikan dict berisi array (n,4) untuk lo, tengah, hi."""
        X = siapkan_fitur(df)
        keluar = {}
        for k, q in zip(["lo", "tengah", "hi"], KUANTIL):
            keluar[k] = np.column_stack(
                [self.model[(nama, q)].predict(X) for nama in NAMA_KELAS])
        if self.koreksi:
            d = np.array([self.koreksi.get(n, 0.0) for n in NAMA_KELAS])
            keluar["lo"] = keluar["lo"] - d
            keluar["hi"] = keluar["hi"] + d
        # jaga batas dalam [0,1] dan urutan lo <= tengah <= hi
        for k in keluar:
            keluar[k] = np.clip(keluar[k], 0.0, 1.0)
        keluar["tengah"] = np.clip(keluar["tengah"], keluar["lo"], keluar["hi"])
        # prediksi tengah dinormalkan agar berjumlah 1 (komposisi)
        s = keluar["tengah"].sum(axis=1, keepdims=True)
        keluar["tengah_normal"] = keluar["tengah"] / np.where(s == 0, 1, s)
        return keluar

    def prediksi_satu(self, komposisi_terlihat: dict[str, float],
                      n_terlihat: int, n_tandan_taksiran: int
                      ) -> dict[str, Selang]:
        """Antarmuka untuk satu muatan — dipakai backend."""
        baris = {f"lihat_{n}": float(komposisi_terlihat.get(n, 0.0))
                 for n in NAMA_KELAS}
        baris.update(n_terlihat=n_terlihat,
                     n_tandan_taksiran=n_tandan_taksiran)
        p = self.prediksi(pd.DataFrame([baris]))
        return {
            n: Selang(nilai=float(p["tengah_normal"][0, i]),
                      lo=float(p["lo"][0, i]), hi=float(p["hi"][0, i]))
            for i, n in enumerate(NAMA_KELAS)
        }

    # ---------------------------------------------------- kalibrasi CQR

    def kalibrasi(self, df_val: pd.DataFrame, alpha: float = 0.10) -> "Model2":
        """Kalibrasi conformal atas selang kuantil (CQR).

        Regresi kuantil memberi selang yang MENDEKATI benar, tetapi tidak
        menjamin cakupan. Di sini selang dilebarkan berdasarkan galat yang
        teramati di data validasi, sehingga cakupan 1-alpha dijamin secara
        empiris.

        Skor konformitas: E_i = max(lo_i - y_i, y_i - hi_i). Nilai positif
        berarti nilai sebenarnya berada DI LUAR selang. Kuantil ke-(1-alpha)
        dari skor itu adalah jarak yang perlu ditambahkan.

        Ini penting justru karena keluaran sistem dipakai memotong uang:
        selang yang mengaku 90% tetapi hanya memuat 87% adalah janji palsu.
        """
        X = siapkan_fitur(df_val)
        self.koreksi = {}
        n = len(df_val)
        # faktor (n+1)/n menjaga jaminan cakupan pada sampel berhingga
        tingkat = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        for i, nama in enumerate(NAMA_KELAS):
            lo = self.model[(nama, KUANTIL[0])].predict(X)
            hi = self.model[(nama, KUANTIL[2])].predict(X)
            y = df_val[f"benar_{nama}"].to_numpy()
            skor = np.maximum(lo - y, y - hi)
            self.koreksi[nama] = float(np.quantile(skor, tingkat))
        return self

    def simpan(self, path: Path = BOBOT) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "fitur": FITUR, "kuantil": KUANTIL,
                     "kelas": NAMA_KELAS, "koreksi": self.koreksi}, path)

    @classmethod
    def muat(cls, path: Path = BOBOT) -> "Model2":
        d = joblib.load(path)
        obj = cls()
        obj.model = d["model"]
        obj.koreksi = d.get("koreksi", {})
        return obj


# ------------------------------------------------------------- evaluasi

def evaluasi(model: Model2, df: pd.DataFrame) -> dict:
    """Bandingkan model terhadap dua tolok ukur.

    1. **Dasar naif** — anggap komposisi permukaan = komposisi seluruh
       muatan. Ini yang dilakukan semua sistem yang ada.
    2. **Lantai pencuplikan** — batas teoretis lebar selang. Model yang
       selangnya jauh lebih sempit dari lantai berarti terlalu percaya diri.
    """
    p = model.prediksi(df)
    benar = df[[f"benar_{n}" for n in NAMA_KELAS]].to_numpy()
    naif = df[[f"lihat_{n}" for n in NAMA_KELAS]].to_numpy()
    n_lihat = df["n_terlihat"].to_numpy()

    mae_model = np.abs(p["tengah_normal"] - benar).mean(axis=0)
    mae_naif = np.abs(naif - benar).mean(axis=0)

    # cakupan: apakah selang 90% benar-benar memuat nilai sebenarnya 90%?
    dalam = (benar >= p["lo"]) & (benar <= p["hi"])
    cakupan = dalam.mean(axis=0)
    lebar = (p["hi"] - p["lo"]).mean(axis=0)

    lantai = np.column_stack(
        [1.645 * 2 * lantai_pencuplikan(n_lihat, benar[:, i])
         for i in range(len(NAMA_KELAS))]).mean(axis=0)

    return {
        "per_kelas": {
            NAMA_KELAS[i]: {
                "MAE_model": float(mae_model[i]),
                "MAE_naif": float(mae_naif[i]),
                "perbaikan_relatif": float((mae_naif[i] - mae_model[i])
                                           / max(mae_naif[i], 1e-9)),
                "cakupan_90": float(cakupan[i]),
                "lebar_selang": float(lebar[i]),
                "lantai_pencuplikan_90": float(lantai[i]),
                "rasio_lebar_thd_lantai": float(lebar[i] / max(lantai[i], 1e-9)),
            } for i in range(len(NAMA_KELAS))
        },
        "ringkas": {
            "MAE_model_rerata": float(mae_model.mean()),
            "MAE_naif_rerata": float(mae_naif.mean()),
            "perbaikan_relatif": float((mae_naif.mean() - mae_model.mean())
                                       / max(mae_naif.mean(), 1e-9)),
            "cakupan_90_rerata": float(cakupan.mean()),
            "n_muatan": int(len(df)),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--max-iter", type=int, default=300)
    args = ap.parse_args()

    if not args.data.exists():
        print(f"[x] {args.data} tidak ada — jalankan build_stack_dataset.py dulu")
        return 1

    df = pd.read_parquet(args.data)
    tr = df[df.split == "train"]
    te = df[df.split == "test"]
    print(f"latih {len(tr):,} muatan | uji {len(te):,} muatan")
    print("melatih 4 tingkat x 3 kuantil ...")

    va = df[df.split == "val"]
    m = Model2(max_iter=args.max_iter).latih(tr)

    sebelum = evaluasi(m, te)["ringkas"]["cakupan_90_rerata"]
    m.kalibrasi(va)
    m.simpan()
    print()
    print(f"kalibrasi conformal ({len(va):,} muatan validasi):")
    for k, v in m.koreksi.items():
        print(f"  {k:14s} pelebaran +/- {v:+.4f}")

    hasil = evaluasi(m, te)
    hasil["cakupan_sebelum_kalibrasi"] = float(sebelum)
    print()
    print(pd.DataFrame(hasil["per_kelas"]).T.round(4).to_string())
    print()
    r = hasil["ringkas"]
    print(f"MAE model  : {r['MAE_model_rerata']:.4f}")
    print(f"MAE naif   : {r['MAE_naif_rerata']:.4f}")
    print(f"perbaikan  : {r['perbaikan_relatif']*100:+.1f}%")
    print(f"cakupan 90%: {r['cakupan_90_rerata']:.4f}  (target 0,90)")

    # Di mana nilai Model 2 paling besar? Pecah menurut muatan yang ditata.
    print()
    print("=== pecahan menurut karakter muatan ===")
    pecah = {}
    for label, sub in [("ditata sengaja", te[te._ditata]),
                       ("tidak ditata", te[~te._ditata])]:
        h = evaluasi(m, sub)["ringkas"]
        pecah[label] = h
        print(f"  {label:16s} n={h['n_muatan']:5,}  "
              f"MAE model {h['MAE_model_rerata']:.4f}  "
              f"naif {h['MAE_naif_rerata']:.4f}  "
              f"perbaikan {h['perbaikan_relatif']*100:+.1f}%")
    hasil["pecahan_karakter"] = pecah

    print()
    print("=== ketahanan terhadap kekuatan tenggelam ===")
    tahan = {}
    for lo_b, hi_b in [(0.0, 0.5), (0.5, 1.5), (1.5, 2.5)]:
        sub = te[(te._kekuatan_tenggelam >= lo_b) & (te._kekuatan_tenggelam < hi_b)]
        if len(sub) < 50:
            continue
        h = evaluasi(m, sub)["ringkas"]
        tahan[f"{lo_b}-{hi_b}"] = h
        print(f"  kekuatan {lo_b}-{hi_b}  n={h['n_muatan']:5,}  "
              f"MAE {h['MAE_model_rerata']:.4f}  "
              f"cakupan {h['cakupan_90_rerata']:.3f}")
    hasil["ketahanan_tenggelam"] = tahan

    out = ROOT / "docs" / "hasil_model2.json"
    out.write_text(json.dumps(hasil, indent=2), encoding="utf-8")
    print(f"\n[ok] bobot -> {BOBOT}")
    print(f"[ok] angka -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# --------------------------------------------------------------------
# Permukaan resmi (GATE AI-2). Backend memanggil nama ini.
# --------------------------------------------------------------------

_model_bawaan: Model2 | None = None


def model_bawaan(path: Path = BOBOT) -> Model2:
    """Satu instans bersama, dimuat sekali."""
    global _model_bawaan
    if _model_bawaan is None:
        _model_bawaan = Model2.muat(path)
    return _model_bawaan


def infer(komposisi_terlihat: dict[str, float], n_terlihat: int,
          n_tandan_taksiran: int) -> dict[str, Selang]:
    """Dari komposisi PERMUKAAN ke komposisi SELURUH MUATAN, berselang.

    `komposisi_terlihat` adalah keluaran `Detector.komposisi_terlihat`,
    yaitu proporsi tandan pada lapisan yang tertangkap kamera.

    `n_tandan_taksiran` biasanya berat_bruto / berat rata-rata tandan.
    Ia dibutuhkan karena lebar selang bergantung pada seberapa kecil
    cuplikan permukaan dibanding muatan penuh — melihat 30 tandan dari
    100 sangat berbeda dari melihat 30 dari 400.
    """
    return model_bawaan().prediksi_satu(
        komposisi_terlihat, n_terlihat, n_tandan_taksiran)
