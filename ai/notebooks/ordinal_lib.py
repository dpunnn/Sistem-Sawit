"""Komponen head ordinal — dipakai bersama Notebook 05 dan 06.

Dipisahkan ke modul supaya definisi arsitektur, fungsi loss, dan rutin
pelatihan hanya ada di SATU tempat. Kalau tiap notebook menyalin sendiri,
cepat atau lambat dua notebook memakai varian yang sedikit berbeda dan
angkanya tidak lagi bisa dibandingkan.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import Dataset
from torchvision import models, transforms

SIZE = 128
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
ORDINAL_NAMES = ["0_mentah", "1_kurang_masak", "2_masak", "3_terlalu_masak"]
LABEL_PENDEK = ["mentah", "kurang\nmasak", "masak", "terlalu\nmasak"]


# ------------------------------------------------------------ augmentasi

def augmentasi(kuat: bool = False):
    """Augmentasi pelatihan.

    `kuat=True` dirancang khusus untuk MEMATAHKAN JALAN PINTAS KONTEKS:
    pemotongan jauh lebih agresif dan penghapusan acak diperbesar, sehingga
    latar, sudut kamera, dan potongan tandan tetangga tidak lagi jadi
    petunjuk yang bisa diandalkan model.

    Warna sengaja TIDAK dirusak berat (tanpa grayscale): pada tugas ini
    warna justru sinyal utama kematangan, bukan gangguan.
    """
    if kuat:
        return transforms.Compose([
            transforms.RandomResizedCrop(SIZE, scale=(0.45, 1.0), ratio=(0.7, 1.45)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.ColorJitter(0.3, 0.3, 0.25, 0.03),
            transforms.ToTensor(), transforms.Normalize(MEAN, STD),
            transforms.RandomErasing(p=0.5, scale=(0.05, 0.25)),
        ])
    return transforms.Compose([
        transforms.RandomResizedCrop(SIZE, scale=(0.75, 1.0), ratio=(0.75, 1.4)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(0.3, 0.3, 0.25, 0.03),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD),
    ])


def transformasi_eval():
    return transforms.Compose([
        transforms.Resize((SIZE, SIZE)),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD),
    ])


class CropDS(Dataset):
    def __init__(self, df, tf):
        self.df = df.reset_index(drop=True)
        self.tf = tf

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        return self.tf(Image.open(r["path"]).convert("RGB")), int(r["ordinal"])


# ------------------------------------------------------------- arsitektur

class Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        m = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        self.body = nn.Sequential(*list(m.children())[:-1])
        self.dim = m.fc.in_features

    def forward(self, x):
        return self.body(x).flatten(1)


class CoralHead(nn.Module):
    """K-1 ambang berjenjang dengan bobot dibagi bersama."""

    def __init__(self, in_dim: int, n_kelas: int):
        super().__init__()
        self.fc = nn.Linear(in_dim, 1, bias=False)
        self.bias = nn.Parameter(torch.zeros(n_kelas - 1))

    def forward(self, x):
        return self.fc(x) + self.bias


class Model(nn.Module):
    def __init__(self, n_kelas, mode="ce", backbone=None):
        super().__init__()
        self.backbone = backbone or Backbone()
        self.mode = mode
        self.head = (CoralHead(self.backbone.dim, n_kelas) if mode == "coral"
                     else nn.Linear(self.backbone.dim, n_kelas))

    def forward(self, x):
        return self.head(self.backbone(x))


def coral_targets(y, n_kelas):
    lv = torch.arange(n_kelas - 1, device=y.device).unsqueeze(0)
    return (y.unsqueeze(1) > lv).float()


def coral_loss(logits, y, n_kelas):
    return F.binary_cross_entropy_with_logits(
        logits, coral_targets(y, n_kelas), reduction="mean")


def coral_predict(logits):
    return (torch.sigmoid(logits) > 0.5).sum(dim=1)


# --------------------------------------------------------------- pelatihan

def jalankan(model, dl_tr, dl_va, n_kelas, mode, dev, epochs=25, lr=3e-4,
             label="", bobot_kelas=None):
    """Latih, pilih bobot dengan MAE validasi terbaik."""
    import pandas as pd

    model = model.to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    hist, best, best_state = [], np.inf, None

    for ep in range(epochs):
        model.train()
        tl = 0.0
        for x, y in dl_tr:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            out = model(x)
            loss = (coral_loss(out, y, n_kelas) if mode == "coral"
                    else F.cross_entropy(out, y, weight=bobot_kelas))
            loss.backward()
            opt.step()
            tl += loss.item() * len(x)
        sch.step()

        met, _, _ = evaluasi(model, dl_va, mode, dev)
        hist.append({"epoch": ep + 1, "train_loss": tl / len(dl_tr.dataset),
                     "val_mae": met["MAE_indeks"], "val_acc": met["akurasi"]})
        if met["MAE_indeks"] < best:
            best = met["MAE_indeks"]
            best_state = {k: v.detach().cpu().clone()
                          for k, v in model.state_dict().items()}
        if (ep + 1) % 5 == 0 or ep == 0:
            print(f"  [{label}] epoch {ep+1:2d}/{epochs}  "
                  f"val_mae {met['MAE_indeks']:.4f}  val_acc {met['akurasi']:.4f}")

    model.load_state_dict(best_state)
    return model, pd.DataFrame(hist)


def evaluasi(model, dl, mode, dev):
    model.eval()
    preds, ys = [], []
    with torch.no_grad():
        for x, y in dl:
            out = model(x.to(dev))
            p = (coral_predict(out) if mode == "coral" else out.argmax(1))
            preds.append(p.cpu())
            ys.append(y)
    p = torch.cat(preds).numpy()
    y = torch.cat(ys).numpy()
    return {
        "akurasi": float((p == y).mean()),
        "MAE_indeks": float(np.abs(p - y).mean()),
        "salah_>=2_tingkat": float((np.abs(p - y) >= 2).mean()),
        "n": int(len(y)),
    }, p, y


def bobot_seimbang(df, dev, n_kelas=4):
    """Bobot kelas berbanding terbalik dengan frekuensi."""
    frek = df["ordinal"].value_counts().reindex(range(n_kelas), fill_value=1).values
    w = frek.sum() / (n_kelas * frek)
    return torch.tensor(w, dtype=torch.float32).to(dev)
