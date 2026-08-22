"""Latih Model 1 — detektor tandan, tiga kelas STRUKTURAL.

## Rencana awal, dan bagaimana ia berubah

Rencana semula: dua varian dibandingkan head-to-head, (a) cross-entropy
standar dan (b) CORAL / ordinal regression, lalu laporkan mAP DAN MAE
indeks kelas; kalau ordinal kalah, laporkan jujur.

Ordinal memang kalah, dan itu dilaporkan (docs/experiments.md bagian 5).
Tetapi perbandingannya berpindah tempat: penilaian kematangan ternyata
tidak boleh dikerjakan detektor sama sekali.

Sebabnya ditemukan di notebook 06. Dari 91 tumpukan, 66 hanya berisi
SATU tingkat kematangan — jadi detektor tujuh kelas bisa lulus dengan
mengenali adegan, bukan membedakan tandan. Akurasinya jatuh dari 0,8365
pada tumpukan murni ke 0,5160 pada tumpukan campuran, dan justru
tumpukan campuran yang mewakili muatan truk sungguhan.

Karena itu detektor di berkas ini hanya menjawab **di mana tandannya**
(tandan / janjang kosong / abnormal). Perbandingan CE vs CORAL pindah ke
head kematangan yang melihat crop tunggal tanpa konteks tumpukan —
lihat notebook 05 dan 06.

## Dua eksperimen yang dijalankan berkas ini

    A  split per tumpukan (jujur)  <- bobot yang benar-benar dipakai
    B  split resmi bawaan (bocor)  <- pembanding, untuk mengukur inflasi

B sengaja dilatih meski tahu hasilnya palsu. Tanpa angka pembanding,
pernyataan "split resmi bocor" hanya tuduhan; dengan angka itu ia jadi
+10,4% mAP@50-95 dan +19,6% presisi yang bisa diperiksa siapa pun.

Berkas ini adalah bentuk CLI dari notebook 04. Notebook untuk membaca
analisisnya; CLI ini untuk melatih ulang tanpa membuka Jupyter.

Jalankan:
    python ai/training/train_detector.py                 # A saja
    python ai/training/train_detector.py --dengan-bocor  # A dan B
    python ai/training/train_detector.py --epochs 5      # uji cepat
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "ai" / "weights" / "runs"
DS_JUJUR = ROOT / "data" / "processed" / "yolo_per_tumpukan"
DS_BOCOR = ROOT / "data" / "processed" / "yolo_split_resmi"

NAMA_KELAS = ["tandan", "janjang_kosong", "abnormal"]

# Konfigurasi. Angka dipilih dengan alasan, bukan default.
CFG = dict(
    model="yolov8s.pt",   # 's': cukup kuat untuk 62 tumpukan, masih cepat
    imgsz=416,            # sama dengan resolusi asli dataset; menaikkan
                          # tidak menambah informasi karena citra sudah 416
    epochs=60,
    patience=15,          # berhenti dini: 62 tumpukan cepat overfit
    batch=16,
    seed=42,
    # Augmentasi pencahayaan diperkuat: foto gerbang PKS diambil kapan
    # saja, dari pagi mendung sampai sore backlight.
    hsv_h=0.015, hsv_s=0.7, hsv_v=0.5,
    degrees=8.0, translate=0.1, scale=0.4, fliplr=0.5,
    mosaic=1.0, close_mosaic=10,
)


def evaluasi(model, data_yaml: Path, device: str, split: str = "test") -> dict:
    """Metrik global dan per kelas pada sisi uji."""
    import numpy as np

    m = model.val(data=str(data_yaml), split=split, device=device,
                  verbose=False, plots=False)
    per_kelas = {}
    for i, nama in enumerate(NAMA_KELAS):
        try:
            p, r, ap50, ap = m.box.class_result(i)
            per_kelas[nama] = dict(precision=float(p), recall=float(r),
                                   mAP50=float(ap50), mAP50_95=float(ap))
        except Exception:
            per_kelas[nama] = dict(precision=float(np.nan), recall=float(np.nan),
                                   mAP50=float(np.nan), mAP50_95=float(np.nan))
    return {
        "global": dict(mAP50=float(m.box.map50), mAP50_95=float(m.box.map),
                       precision=float(m.box.mp), recall=float(m.box.mr)),
        "per_kelas": per_kelas,
    }


def latih(dataset: Path, nama: str, device: str, cfg: dict) -> tuple[Path, dict]:
    from ultralytics import YOLO

    if not (dataset / "data.yaml").exists():
        raise FileNotFoundError(
            f"{dataset / 'data.yaml'} tidak ada. Jalankan dulu:\n"
            "  python ai/training/prepare_split.py\n"
            "  python ai/training/materialize_yolo.py")

    t0 = time.time()
    model = YOLO(cfg["model"])
    res = model.train(
        data=str(dataset / "data.yaml"),
        project=str(RUNS), name=nama, exist_ok=True,
        device=device, verbose=False, plots=True,
        **{k: v for k, v in cfg.items() if k != "model"},
    )
    menit = (time.time() - t0) / 60
    out = Path(res.save_dir)
    best = YOLO(str(out / "weights" / "best.pt"))
    hasil = evaluasi(best, dataset / "data.yaml", device)
    hasil["menit"] = round(menit, 1)
    hasil["bobot"] = str(out / "weights" / "best.pt")
    return out, hasil


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dengan-bocor", action="store_true",
                    help="latih juga varian split resmi sebagai pembanding")
    ap.add_argument("--device", default="0",
                    help="'0' untuk GPU, 'cpu' untuk CPU")
    ap.add_argument("--epochs", type=int, default=CFG["epochs"])
    ap.add_argument("--model", default=CFG["model"])
    args = ap.parse_args()

    cfg = {**CFG, "epochs": args.epochs, "model": args.model}
    print("KONFIGURASI")
    for k, v in cfg.items():
        print(f"  {k:14s} {v}")
    print()

    print("=" * 62)
    print("EKSPERIMEN A — split per tumpukan (jujur)")
    print("=" * 62)
    _, a = latih(DS_JUJUR, "A_per_tumpukan", args.device, cfg)
    for k, v in a["global"].items():
        print(f"  {k:10s} {v:.4f}")
    print(f"  selesai dalam {a['menit']} menit")

    ringkas = {"A_per_tumpukan": a}

    if args.dengan_bocor:
        if not DS_BOCOR.exists():
            print("\n[lewati] dataset split resmi belum dibangun. Jalankan:")
            print("  python ai/training/materialize_yolo.py --split-resmi")
        else:
            print()
            print("=" * 62)
            print("EKSPERIMEN B — split resmi bawaan (BOCOR, pembanding)")
            print("=" * 62)
            print("Sengaja dilatih meski hasilnya palsu: tanpa angka")
            print("pembanding, 'split resmi bocor' hanya tuduhan.")
            print()
            _, b = latih(DS_BOCOR, "B_split_resmi", args.device, cfg)
            for k, v in b["global"].items():
                print(f"  {k:10s} {v:.4f}")
            ringkas["B_split_resmi"] = b

            print()
            print("INFLASI AKIBAT KEBOCORAN")
            for k in ("mAP50_95", "precision"):
                ja, bo = a["global"][k], b["global"][k]
                print(f"  {k:10s} {ja:.4f} (jujur) vs {bo:.4f} (bocor)  "
                      f"-> {(bo - ja) / ja * 100:+.1f}%")

    out = ROOT / "docs" / "hasil_detektor.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ringkas, indent=2), encoding="utf-8")
    print()
    print(f"[ok] {out}")
    print("     bobot dipakai inferensi lewat ai/perception/detector.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
