"""Split train/val/test BERDASARKAN ID TUMPUKAN/VIDEO, bukan per gambar.

Dataset dibuat dari video rotasi 360 derajat -> banyak frame nyaris
duplikat dari tumpukan yang sama. Split per gambar = kebocoran =
metrik melambung dan angkanya PALSU.

## Besaran kebocoran itu terukur, bukan dugaan

Split resmi dataset publik yang dipakai bocor SEPENUHNYA: seluruh 91
tumpukan muncul di sisi latih, dan 88,7% gambar uji punya frame
bersebelahan langsung di sisi latih. Melatih detektor pada kedua split
memberi selisihnya:

    mAP@50-95   0,7892 (jujur)  vs  0,8712 (bocor)   ->  +10,4%
    presisi     0,8309 (jujur)  vs  0,9942 (bocor)   ->  +19,6%

Angka yang kedua itulah yang akan dilaporkan siapa pun yang memakai
split bawaan tanpa memeriksanya.

## Kenapa 300 seed, bukan satu

Penugasan serakah dengan satu seed memenuhi kuota tetapi tidak menjamin
distribusi kelasnya wajar. Karena itu 300 kandidat dibangkitkan, yang
melanggar kendala dibuang, dan yang tersisa diperingkat menurut
divergensi Jensen-Shannon terhadap distribusi keseluruhan.

Kendala yang harus dipenuhi bersamaan:
  - proporsi gambar latih 70% +/- 6%, val dan test masing-masing >= 10%
  - tiap split memuat SEMUA kelas
  - tiap split memuat tumpukan murni DAN campuran

Kendala terakhir yang paling sering dilupakan. Tanpa tumpukan campuran
di sisi uji, jalan pintas tingkat tumpukan tidak akan pernah ketahuan --
dan itu persis kegagalan yang ditemukan di notebook 06.

Berkas ini adalah bentuk CLI dari notebook 02, memakai fungsi yang sama
dari `ai/notebooks/dataio.py` supaya tidak ada logika yang berganda.
Notebook untuk membaca hasilnya; CLI ini untuk membangun ulang tanpa
membuka Jupyter.

Jalankan:
    python ai/training/prepare_split.py
    python ai/training/prepare_split.py --n-seed 600 --out data/interim
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ai" / "notebooks"))

import dataio  # noqa: E402

TARGET = {"train": 0.70, "val": 0.15, "test": 0.15}


def js_divergence(p, q, eps: float = 1e-9) -> float:
    """Jarak Jensen-Shannon — simetris, terbatas 0..1, aman untuk proporsi."""
    p = np.asarray(p, float) + eps
    q = np.asarray(q, float) + eps
    p /= p.sum()
    q /= q.sum()
    m = 0.5 * (p + q)
    kl = lambda a, b: np.sum(a * np.log2(a / b))  # noqa: E731
    return float(np.sqrt(0.5 * kl(p, m) + 0.5 * kl(q, m)))


def split_per_tumpukan(prof: pd.DataFrame, target=TARGET, seed: int = 42) -> dict:
    """Penugasan serakah yang sadar bobot frame.

    Tumpukan besar ditugaskan lebih dulu supaya sisa kuota bisa diisi
    tumpukan kecil; urutan sebaliknya membuat split terakhir kebanjiran.
    Kelompok rekaman dijaga utuh agar tidak ada frame bersaudara yang
    terpisah ke dua sisi.
    """
    assign: dict[str, str] = {}
    total = prof["n_frame"].sum()
    kuota = {k: v * total for k, v in target.items()}
    terisi = {k: 0.0 for k in target}

    for _, sub in prof.groupby("group"):
        sub = sub.sample(frac=1.0, random_state=seed)      # pecah ikatan
        sub = sub.sort_values("n_frame", ascending=False)  # besar dulu
        g_total = sub["n_frame"].sum()
        g_kuota = {k: v * g_total for k, v in target.items()}
        g_terisi = {k: 0.0 for k in target}

        for _, row in sub.iterrows():
            # pilih split yang paling tertinggal secara relatif di kelompok
            # ini, dengan kekurangan global sebagai pemecah imbang
            defisit = {k: (g_kuota[k] - g_terisi[k]) / max(g_kuota[k], 1e-9)
                       for k in target}
            best = max(defisit, key=lambda k: (defisit[k], kuota[k] - terisi[k]))
            assign[row["pile"]] = best
            g_terisi[best] += row["n_frame"]
            terisi[best] += row["n_frame"]
    return assign


def nilai_split(assign: dict, prof: pd.DataFrame, boxes: pd.DataFrame,
                kelas, ref) -> tuple[bool, float]:
    """(memenuhi kendala, skor). Skor makin kecil makin baik."""
    p = prof.assign(split=prof["pile"].map(assign))
    b = boxes.assign(split=boxes["pile"].map(assign))

    share = p.groupby("split")["n_frame"].sum() / p["n_frame"].sum()
    if not set(share.index) >= {"train", "val", "test"}:
        return False, np.inf
    if abs(share["train"] - 0.70) > 0.06 or min(share["val"], share["test"]) < 0.10:
        return False, np.inf

    tab = (b.groupby(["split", "class_id"]).size().unstack(fill_value=0)
           .reindex(columns=kelas, fill_value=0))
    if (tab == 0).any().any():
        return False, np.inf

    kar = p.groupby(["split", "murni"]).size().unstack(fill_value=0)
    if kar.shape[1] < 2 or (kar == 0).any().any():
        return False, np.inf

    return True, max(js_divergence(tab.loc[s].values, ref) for s in ("val", "test"))


def cari(prof, boxes, n_seed: int = 300) -> list[tuple[float, int, dict]]:
    kelas = sorted(boxes["class_id"].unique())
    ref = boxes["class_id"].value_counts().reindex(kelas, fill_value=0).values
    hasil = []
    for seed in range(n_seed):
        a = split_per_tumpukan(prof, seed=seed)
        ok, skor = nilai_split(a, prof, boxes, kelas, ref)
        if ok:
            hasil.append((skor, seed, a))
    hasil.sort(key=lambda t: t[0])
    return hasil


def periksa_kebocoran(prof: pd.DataFrame, assign: dict) -> dict:
    """Tidak boleh ada tumpukan yang muncul di lebih dari satu split.

    Pemeriksaan ini murah dan wajib. Kebocoran tidak menimbulkan error --
    ia hanya membuat angka membaik, dan angka yang membaik tanpa sebab
    adalah hal terakhir yang akan dicurigai orang.
    """
    p = prof.assign(split=prof["pile"].map(assign))
    per_pile = p.groupby("pile")["split"].nunique()
    per_group = p.groupby("group")["split"].nunique()
    return {
        "tumpukan_di_lebih_satu_split": int((per_pile > 1).sum()),
        "kelompok_terbelah": int((per_group > 1).sum()),
        "bersih": bool((per_pile > 1).sum() == 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/piles-kalsel",
                    help="folder dataset mentah (berisi train/valid/test)")
    ap.add_argument("--out", default="data/interim")
    ap.add_argument("--n-seed", type=int, default=300)
    args = ap.parse_args()

    imgs, boxes = dataio.load_index(ROOT / args.data)
    prof = dataio.pile_profile(imgs, boxes)
    print(f"{len(imgs):,} gambar · {len(boxes):,} kotak · {len(prof)} tumpukan")
    print(f"tumpukan murni (satu tingkat saja): "
          f"{int(prof['murni'].sum())} dari {len(prof)}")
    print()

    hasil = cari(prof, boxes, args.n_seed)
    if not hasil:
        print("[GAGAL] tidak ada kandidat yang memenuhi kendala. "
              "Longgarkan target atau periksa datanya.")
        return 1

    skor, seed, assign = hasil[0]
    print(f"seed diuji         : {args.n_seed}")
    print(f"memenuhi kendala   : {len(hasil)}")
    print(f"divergensi terburuk: {hasil[-1][0]:.4f}")
    print(f"divergensi terpilih: {skor:.4f}  (seed {seed})")
    print()

    lk = periksa_kebocoran(prof, assign)
    print("PEMERIKSAAN KEBOCORAN")
    print(f"  tumpukan di >1 split : {lk['tumpukan_di_lebih_satu_split']}")
    print(f"  kelompok terbelah    : {lk['kelompok_terbelah']}  "
          "(boleh >0: kelompok memang dibagi, tumpukan tidak)")
    print(f"  status               : {'BERSIH' if lk['bersih'] else 'BOCOR'}")
    if not lk["bersih"]:
        return 1
    print()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    prof.assign(split=prof["pile"].map(assign)).to_csv(
        out / "split_per_tumpukan.csv", index=False)
    imgs.to_csv(out / "manifest_gambar.csv", index=False)

    p = prof.assign(split=prof["pile"].map(assign))
    ring = p.groupby("split").agg(tumpukan=("pile", "size"),
                                  gambar=("n_frame", "sum"),
                                  kotak=("n_box", "sum"),
                                  murni=("murni", "sum"))
    ring["bagian_gambar"] = (ring["gambar"] / ring["gambar"].sum() * 100).round(1)
    print(ring.to_string())
    print()
    print(f"[ok] {out / 'split_per_tumpukan.csv'}")
    print("     lanjutkan dengan: python ai/training/materialize_yolo.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
