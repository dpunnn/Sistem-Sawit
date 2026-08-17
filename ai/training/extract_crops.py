"""Potong crop tandan dari kotak anotasi untuk melatih head ordinal.

## Kenapa ini ada

Head ordinal dipra-latih pada dataset buah tunggal yang bersih dan
beresolusi penuh, tetapi saat dipakai ia menerima **crop hasil deteksi**
dari citra 416x416 — kecil, sebagian terhalang, dan lebih buram. Kalau
head hanya pernah melihat citra bersih, ia akan kaget di dunia nyata.

Skrip ini menutup jarak itu: bounding box yang sudah ada di dataset
tumpukan dipotong menjadi crop berlabel kematangan, sehingga tersedia
ribuan contoh dengan **kondisi yang sama persis** dengan kondisi
inferensi nanti.

## Yang dipotong

Hanya empat tingkat kematangan. `Janjang kosong` dan `TBS abnormal`
bukan tingkat kematangan — keduanya ditangani detektor sebagai kelas
struktural dan tidak pernah masuk head ordinal.

## Pembagian split

Mengikuti manifes split PER TUMPUKAN dari Notebook 02, bukan split resmi.
Crop dari satu tumpukan tidak boleh tersebar ke dua sisi — kalau itu
terjadi, kebocoran yang sudah susah payah ditutup di tingkat gambar
muncul kembali di tingkat crop.

Jalankan:
    python ai/training/extract_crops.py
    python ai/training/extract_crops.py --pad 0.15 --min-size 24
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "data" / "processed" / "crops_ordinal"

# class_id asli -> indeks ordinal (0 = paling mentah)
ORDINAL_INDEX = {4: 0, 1: 1, 3: 2, 5: 3}
ORDINAL_NAMES = ["0_mentah", "1_kurang_masak", "2_masak", "3_terlalu_masak"]


def read_boxes(img_path: Path) -> list[tuple[int, float, float, float, float]]:
    lab = img_path.with_suffix(".txt")
    if not lab.exists():
        return []
    out = []
    for line in lab.read_text().strip().splitlines():
        p = line.split()
        if len(p) >= 5:
            out.append((int(p[0]), *map(float, p[1:5])))
    return out


def crop_box(im: Image.Image, x, y, w, h, pad: float) -> Image.Image:
    W, H = im.size
    bw, bh = w * W, h * H
    cx, cy = x * W, y * H
    # padding relatif terhadap sisi kotak, supaya konteks tepi ikut terbawa
    # pad negatif = memotong ke dalam kotak, membuang tepi yang paling
    # mungkin memuat latar dan tandan tetangga -- sumber petunjuk konteks
    # yang memungkinkan model mengenali TUMPUKAN alih-alih menilai TANDAN.
    px, py = bw * pad, bh * pad
    x1 = max(0, int(cx - bw / 2 - px))
    y1 = max(0, int(cy - bh / 2 - py))
    x2 = min(W, int(cx + bw / 2 + px))
    y2 = min(H, int(cy + bh / 2 + py))
    if x2 - x1 < 8 or y2 - y1 < 8:      # jaga-jaga kalau pad terlalu negatif
        x1, y1 = int(cx - bw / 2), int(cy - bh / 2)
        x2, y2 = int(cx + bw / 2), int(cy + bh / 2)
    return im.crop((max(0, x1), max(0, y1), min(W, x2), min(H, y2)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad", type=float, default=0.10,
                    help="padding relatif; NEGATIF memotong ke DALAM kotak "
                         "(-0.10 = buang 10%% tepi) untuk menghapus konteks latar")
    ap.add_argument("--out", type=str, default="crops_ordinal",
                    help="nama folder keluaran di data/processed/")
    ap.add_argument("--hanya-campuran", action="store_true",
                    help="hanya potong dari tumpukan campuran")
    ap.add_argument("--min-size", type=int, default=20,
                    help="buang crop yang sisi terpendeknya di bawah ini (px)")
    args = ap.parse_args()

    man_path = INTERIM / "manifest_gambar.csv"
    if not man_path.exists():
        print(f"[x] {man_path} tidak ada — jalankan Notebook 02 lebih dulu.")
        return 1
    man = pd.read_csv(man_path)

    out_dir = ROOT / "data" / "processed" / args.out
    globals()["OUT"] = out_dir
    OUT = out_dir
    if args.hanya_campuran:
        man = man[~man["murni"]]
        print(f"[filter] hanya tumpukan campuran: {man['pile'].nunique()} tumpukan")
    if OUT.exists():
        shutil.rmtree(OUT)
    for split in ["train", "val", "test"]:
        for nama in ORDINAL_NAMES:
            (OUT / split / nama).mkdir(parents=True, exist_ok=True)

    stats = {s: Counter() for s in ["train", "val", "test"]}
    dibuang = Counter()
    index_rows = []

    for _, r in man.iterrows():
        split = r["split"]
        if split not in stats:
            continue
        img_path = Path(r["path"])
        boxes = read_boxes(img_path)
        if not boxes:
            continue
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            for k, (cid, x, y, w, h) in enumerate(boxes):
                if cid not in ORDINAL_INDEX:
                    dibuang["bukan tingkat kematangan"] += 1
                    continue
                c = crop_box(im, x, y, w, h, args.pad)
                if min(c.size) < args.min_size:
                    dibuang["terlalu kecil"] += 1
                    continue
                idx = ORDINAL_INDEX[cid]
                nama = f"{img_path.stem}__b{k}.jpg"
                dest = OUT / split / ORDINAL_NAMES[idx] / nama
                c.save(dest, quality=95)
                stats[split][idx] += 1
                index_rows.append({
                    "file": nama, "split": split, "ordinal": idx,
                    "label": ORDINAL_NAMES[idx], "pile": r["pile"],
                    "group": r["group"], "murni": r["murni"],
                    "w": c.size[0], "h": c.size[1],
                    "path": str(dest),
                })

    idx_df = pd.DataFrame(index_rows)
    idx_df.to_csv(OUT / "index.csv", index=False)

    tab = pd.DataFrame(
        {s: {ORDINAL_NAMES[i]: stats[s].get(i, 0) for i in range(4)}
         for s in ["train", "val", "test"]}
    ).T
    tab["TOTAL"] = tab.sum(axis=1)
    tab.loc["TOTAL"] = tab.sum()

    print(f"Padding      : {args.pad:.0%}")
    print(f"Sisi minimum : {args.min_size} px")
    print()
    print(tab.to_string())
    print()
    for k, v in dibuang.items():
        print(f"  dibuang ({k}) : {v:,}")

    # Kesehatan: pastikan tidak ada tumpukan yang crop-nya tersebar dua split.
    bocor = (idx_df.groupby("pile")["split"].nunique() > 1).sum()
    print(f"\nTumpukan yang crop-nya tersebar di >1 split : {bocor}")
    print(f"[ok] index -> {OUT / 'index.csv'}")
    return 0 if bocor == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
