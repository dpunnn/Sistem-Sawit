"""Render bounding box ke gambar (server-side, PIL/OpenCV).

Server-side supaya hasilnya identik di semua layar — penting untuk
video proof of work dan demo di proyektor.

## Kenapa tidak digambar di browser saja

Frontend sudah punya `DetectionOverlay.tsx` yang menggambar kotak di
atas foto memakai SVG, dan untuk pemakaian sehari-hari itu memang lebih
baik: bisa di-hover, bisa disaring, tidak membebani server.

Yang tidak bisa dilakukan browser adalah menghasilkan **berkas gambar**
yang bisa dilampirkan ke sertifikat sortasi, dikirim lewat WhatsApp ke
petani yang tidak membuka aplikasi, atau ditempel di berita acara
sengketa. Untuk itu gambarnya harus jadi satu berkas utuh yang tidak
bergantung pada layar siapa pun.

## Warna mengikuti palet yang sama dengan frontend

Nilainya disalin dari `frontend/tailwind.config.ts`, dan itu memang
duplikasi. Alternatifnya — server membaca konfigurasi Tailwind — jauh
lebih rapuh daripada satu daftar pendek yang dijaga uji kecocokan.

Ramp kematangan satu keluarga hue dengan terang menurun, sehingga
urutannya terbaca dari warnanya sendiri. Tetapi karena satu hue berarti
warna tidak boleh memikul makna sendirian, tiap kotak SELALU diberi
label teks.

Jalankan:
    python ai/perception/overlay.py <gambar.jpg>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.perception.detector import Detection

# Disalin dari frontend/tailwind.config.ts (ripe.*). Dijaga uji.
WARNA = {
    "unripe": (203, 168, 113),
    "underripe": (185, 138, 68),
    "ripe": (160, 108, 34),
    "overripe": (125, 77, 24),
    "rotten": (84, 48, 14),
    "empty_bunch": (216, 210, 200),
    "abnormal": (179, 170, 156),
}
LABEL = {
    "unripe": "Mentah",
    "underripe": "Setengah matang",
    "ripe": "Matang",
    "overripe": "Lewat matang",
    "rotten": "Busuk",
    "empty_bunch": "Janjang kosong",
    "abnormal": "Abnormal",
}
TINTA = (42, 28, 16)
PUTIH = (255, 255, 255)


def _tinta_di_atas(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Pilih teks gelap atau terang supaya kontras selalu lolos."""
    r, g, b = (c / 255 for c in rgb)
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return TINTA if L > 0.42 else PUTIH


def _font(ukuran: int):
    from PIL import ImageFont
    for nama in ("segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nama, ukuran)
        except OSError:
            continue
    return ImageFont.load_default()


def render(gambar, deteksi: list[Detection], *, tebal: int | None = None,
           tampilkan_label: bool = True, hanya_ragu: bool = False):
    """Gambar kotak deteksi di atas citra, kembalikan PIL.Image baru.

    Deteksi berkeyakinan rendah digambar dengan garis PUTUS-PUTUS, bukan
    dengan warna berbeda. Warna sudah dipakai untuk tingkat kematangan;
    menumpangkan makna kedua ke kanal yang sama membuat keduanya kabur.
    """
    from PIL import Image, ImageDraw

    img = (Image.open(gambar) if isinstance(gambar, (str, Path))
           else gambar).convert("RGB").copy()
    W, H = img.size
    tebal = tebal or max(2, round(min(W, H) / 400))
    font = _font(max(11, round(min(W, H) / 45)))
    d = ImageDraw.Draw(img)

    tampil = [x for x in deteksi if x.low_confidence] if hanya_ragu else deteksi

    for det in tampil:
        x1, y1, x2, y2 = (det.bbox[0] * W, det.bbox[1] * H,
                          det.bbox[2] * W, det.bbox[3] * H)
        warna = WARNA.get(det.ripeness, WARNA["abnormal"])

        if det.low_confidence:
            _kotak_putus(d, (x1, y1, x2, y2), warna, tebal)
        else:
            d.rectangle([x1, y1, x2, y2], outline=warna, width=tebal)

        if not tampilkan_label:
            continue

        teks = LABEL.get(det.ripeness, det.ripeness)
        if det.low_confidence:
            teks += " ?"
        kotak = d.textbbox((0, 0), teks, font=font)
        tw, th = kotak[2] - kotak[0], kotak[3] - kotak[1]
        pad = max(2, tebal)
        # Label di atas kotak; kalau mepet tepi atas, dipindah ke dalam.
        ly = y1 - th - pad * 2 if y1 - th - pad * 2 > 0 else y1 + pad
        d.rectangle([x1, ly, x1 + tw + pad * 2, ly + th + pad * 2], fill=warna)
        d.text((x1 + pad, ly + pad), teks, fill=_tinta_di_atas(warna), font=font)

    return img


def _kotak_putus(d, kotak, warna, tebal, panjang: int = 9):
    """Garis putus-putus menandai deteksi yang perlu dilihat manusia."""
    x1, y1, x2, y2 = kotak
    for a, b, tegak in ((x1, x2, False), (y1, y2, True)):
        n = int(abs(b - a) // (panjang * 2)) + 1
        for i in range(n):
            p = a + i * panjang * 2
            q = min(p + panjang, b)
            if tegak:
                d.line([x1, p, x1, q], fill=warna, width=tebal)
                d.line([x2, p, x2, q], fill=warna, width=tebal)
            else:
                d.line([p, y1, q, y1], fill=warna, width=tebal)
                d.line([p, y2, q, y2], fill=warna, width=tebal)


def simpan(gambar, deteksi: list[Detection], tujuan: Path, **kw) -> Path:
    """Render lalu tulis ke berkas. Ini yang dipanggil backend."""
    tujuan = Path(tujuan)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    render(gambar, deteksi, **kw).save(tujuan, quality=88)
    return tujuan


def legenda(kelas: list[str] | None = None) -> list[dict]:
    """Kunci baca untuk gambar hasil render.

    Dikembalikan sebagai data, bukan digambar ke dalam citra: gambar yang
    sudah memuat legendanya sendiri sulit dipakai ulang pada tata letak
    yang berbeda.
    """
    kelas = kelas or list(WARNA)
    return [{"kelas": k, "label": LABEL.get(k, k),
             "warna": "#%02x%02x%02x" % WARNA[k]} for k in kelas if k in WARNA]


def _peragaan() -> None:
    import argparse

    from ai.perception.detector import Detector

    ap = argparse.ArgumentParser()
    ap.add_argument("gambar")
    ap.add_argument("--out", default="overlay.jpg")
    args = ap.parse_args()

    det = Detector().predict(args.gambar)
    out = simpan(args.gambar, det, args.out)
    print(f"{len(det)} kotak digambar -> {out}")
    ragu = sum(1 for x in det if x.low_confidence)
    print(f"garis putus-putus (perlu diperiksa): {ragu}")
    for it in legenda(sorted({x.ripeness for x in det})):
        print(f"  {it['warna']}  {it['label']}")


if __name__ == "__main__":
    _peragaan()
