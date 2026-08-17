"""Bangun struktur dataset YOLO dari manifes split per tumpukan.

Dua hal terjadi di sini:

1. **Pemetaan ulang kelas.** Label asli punya enam kelas dengan `class_id`
   tersusun alfabetis. Detektor hanya perlu tiga kelas STRUKTURAL:

       tandan          <- mentah, kurang masak, masak, terlalu masak (dilebur)
       janjang_kosong
       abnormal

   Peleburan empat tingkat kematangan menjadi satu kelas `tandan` menaikkan
   jumlah kotak untuk kelas itu dari ~2.400 menjadi ~11.100 — penting ketika
   hanya ada 91 tumpukan. Urutan kematangannya ditangani head ordinal
   terpisah yang bekerja pada crop, sehingga persoalan urutan `class_id`
   yang alfabetis lenyap dari detektor.

2. **Penempatan ulang berkas** menurut split per tumpukan hasil Notebook 02,
   bukan split resmi yang terbukti bocor.

Jalankan:
    python ai/training/materialize_yolo.py
    python ai/training/materialize_yolo.py --split-resmi   # pembanding
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
RAW = ROOT / "data" / "raw" / "piles-kalsel"

# class_id asli -> class_id struktural
STRUCTURAL = {4: 0, 1: 0, 3: 0, 5: 0, 0: 1, 2: 2}
NAMES = ["tandan", "janjang_kosong", "abnormal"]


def remap_label(src: Path) -> tuple[str, Counter]:
    """Baca label asli, kembalikan isi label struktural + hitungan kelas."""
    out, cnt = [], Counter()
    if src.exists():
        for line in src.read_text().strip().splitlines():
            p = line.split()
            if len(p) < 5:
                continue
            new = STRUCTURAL[int(p[0])]
            cnt[new] += 1
            out.append(" ".join([str(new), *p[1:5]]))
    return "\n".join(out), cnt


def build(manifest: pd.DataFrame, split_col: str, out_dir: Path) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)

    stats = {}
    for split in sorted(manifest[split_col].dropna().unique()):
        sub = manifest[manifest[split_col] == split]
        img_dir = out_dir / split / "images"
        lab_dir = out_dir / split / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lab_dir.mkdir(parents=True, exist_ok=True)

        total = Counter()
        for _, r in sub.iterrows():
            src_img = Path(r["path"])
            shutil.copy2(src_img, img_dir / src_img.name)
            text, cnt = remap_label(src_img.with_suffix(".txt"))
            (lab_dir / f"{src_img.stem}.txt").write_text(text, encoding="utf-8")
            total.update(cnt)

        stats[split] = {
            "gambar": len(sub),
            "tumpukan": int(sub["pile"].nunique()),
            **{NAMES[i]: int(total.get(i, 0)) for i in range(3)},
        }

    # data.yaml untuk Ultralytics
    names_map = {i: n for i, n in enumerate(NAMES)}
    cfg = {
        "path": str(out_dir.resolve()),
        "train": "train/images",
        "val": "val/images" if "val" in stats else "valid/images",
        "test": "test/images",
        "nc": len(NAMES),
        "names": names_map,
    }
    (out_dir / "data.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-resmi", action="store_true",
                    help="pakai split resmi (bocor) sebagai pembanding")
    args = ap.parse_args()

    man_path = INTERIM / "manifest_gambar.csv"
    if not man_path.exists():
        print(f"[x] {man_path} tidak ada — jalankan Notebook 02 lebih dulu.")
        return 1

    man = pd.read_csv(man_path)
    col = "split_resmi" if args.split_resmi else "split"
    out = ROOT / "data" / "processed" / (
        "yolo_split_resmi" if args.split_resmi else "yolo_per_tumpukan")

    print(f"Sumber split : kolom '{col}'")
    print(f"Keluaran     : {out}")
    stats = build(man, col, out)

    df = pd.DataFrame(stats).T
    df.loc["TOTAL"] = df.sum()
    print()
    print(df.to_string())
    print(f"\n[ok] data.yaml -> {out / 'data.yaml'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
