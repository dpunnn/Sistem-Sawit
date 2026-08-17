"""Pemuatan indeks dataset — dipakai bersama oleh semua notebook.

Dipisahkan ke modul supaya definisi "apa itu satu tumpukan" hanya ada di
SATU tempat. Kalau logika ini diduplikasi di tiap notebook, cepat atau
lambat dua notebook akan memakai definisi yang berbeda dan angkanya tidak
lagi bisa dibandingkan.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

SPLITS_RESMI = {
    "train": "train_rev2/train",
    "valid": "valid_rev2/valid",
    "test": "test_rev2/test",
}

CLASS_NAMES = {
    0: "Janjang kosong",
    1: "Kurang masak",
    2: "TBS abnormal",
    3: "TBS masak",
    4: "TBS mentah",
    5: "Terlalu masak",
}

# Pemetaan ke 3 kelas STRUKTURAL untuk detektor.
# Empat tingkat kematangan dilebur jadi satu kelas `tandan`; urutan
# kematangannya ditangani model ordinal terpisah pada crop.
STRUCTURAL = {
    4: 0, 1: 0, 3: 0, 5: 0,   # mentah/kurang/masak/terlalu -> tandan
    0: 1,                      # janjang kosong
    2: 2,                      # abnormal
}
STRUCTURAL_NAMES = {0: "tandan", 1: "janjang_kosong", 2: "abnormal"}

# Indeks ordinal untuk head kematangan (0..3).
ORDINAL_INDEX = {4: 0, 1: 1, 3: 2, 5: 3}
ORDINAL_LABELS = ["TBS mentah", "Kurang masak", "TBS masak", "Terlalu masak"]


def parse_pile(stem: str) -> tuple[str, int]:
    """Ambil id tumpukan dan nomor frame dari nama berkas.

    frame1--10-_png.rf.<hash>  ->  ("frame1", 10)
    """
    head = stem.split("_png")[0]
    if "--" in head:
        pile, frame = head.split("--", 1)
        digits = re.sub(r"[^0-9]", "", frame)
        return pile, int(digits) if digits else -1
    return head, -1


def pile_group(pile: str) -> str:
    """Kelompok tumpukan — id tanpa digit di belakang."""
    return re.sub(r"\d+$", "", pile)


def load_index(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baca seluruh gambar + label menjadi dua tabel.

    Returns
    -------
    imgs  : satu baris per gambar
    boxes : satu baris per kotak anotasi
    """
    img_rows, box_rows = [], []
    for split, sub in SPLITS_RESMI.items():
        d = data_dir / sub
        for img in sorted(d.glob("*.jpg")):
            pile, frame = parse_pile(img.stem)
            lab = img.with_suffix(".txt")
            parsed = []
            if lab.exists():
                for line in lab.read_text().strip().splitlines():
                    p = line.split()
                    if len(p) >= 5:
                        parsed.append((int(p[0]), *map(float, p[1:5])))
            img_rows.append({
                "split_resmi": split, "file": img.name, "path": str(img),
                "pile": pile, "group": pile_group(pile), "frame": frame,
                "n_boxes": len(parsed),
            })
            for cid, x, y, w, h in parsed:
                box_rows.append({
                    "split_resmi": split, "file": img.name, "pile": pile,
                    "group": pile_group(pile), "class_id": cid,
                    "x": x, "y": y, "w": w, "h": h,
                })

    imgs = pd.DataFrame(img_rows)
    boxes = pd.DataFrame(box_rows)
    boxes["kelas"] = boxes["class_id"].map(CLASS_NAMES)
    boxes["struktural"] = boxes["class_id"].map(STRUCTURAL)
    return imgs, boxes


def pile_profile(imgs: pd.DataFrame, boxes: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan per tumpukan: jumlah frame, komposisi kelas, murni/campuran.

    Kolom `murni` menandai tumpukan yang seluruh tandannya berlabel sama —
    penting karena tumpukan seperti itu memungkinkan model mengambil jalan
    pintas (mengenali adegan, bukan membedakan tandan).
    """
    n_img = imgs.groupby("pile").size().rename("n_frame")
    grp = imgs.groupby("pile")["group"].first()
    comp = boxes.groupby(["pile", "class_id"]).size().unstack(fill_value=0)

    ripe_cols = [c for c in ORDINAL_INDEX if c in comp.columns]
    ripe = comp[ripe_cols]
    n_ripe = ripe.sum(axis=1)
    dominan = ripe.div(n_ripe.replace(0, 1), axis=0).max(axis=1)

    prof = pd.concat([n_img, grp, comp.sum(axis=1).rename("n_box")], axis=1)
    prof["n_kelas_kematangan"] = (ripe > 0).sum(axis=1)
    prof["dominasi"] = dominan.round(3)
    prof["murni"] = prof["n_kelas_kematangan"] <= 1
    return prof.reset_index()
