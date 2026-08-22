"""MODEL 1 — Deteksi & klasifikasi ordinal per tandan.

INPUT   : citra tumpukan TBS
OUTPUT  : bounding box tiap tandan + kelas kematangan + keyakinan
KELAS   : unripe -> underripe -> ripe -> overripe -> rotten
          (+ empty_bunch, abnormal)

CATATAN : kematangan itu BERURUTAN, jadi hipotesis awalnya memakai loss
          ordinal (CORAL) — salah tebak "ripe"->"overripe" jauh lebih
          murah daripada "unripe"->"rotten".

          HIPOTESIS ITU DIUJI DAN KALAH. Cross-entropy biasa lebih baik,
          dan dugaan penyebabnya (hambatan rank-1 pada CoralHead) sudah
          dibantah lewat varian berkapasitas 256x yang tetap tidak
          menolong. Bobot yang dipakai di sini karena itu bermode `ce`.
          Rinciannya di docs/experiments.md bagian 5.

          Modul ini membaca mode langsung dari checkpoint, bukan
          menebaknya — supaya kalau nanti CORAL menang pada data yang
          lebih baik, tidak ada kode yang perlu diubah di sini.

## Kenapa dua tahap, bukan satu detektor tujuh kelas

Percobaan di notebook 04-06 menunjukkan detektor tujuh kelas belajar
mengenali TUMPUKAN, bukan membedakan tandan: 66 dari 91 tumpukan hanya
berisi satu tingkat kematangan, jadi menghafal adegan sudah cukup untuk
lulus. Akurasinya jatuh dari 0,8365 pada tumpukan murni ke 0,5160 pada
tumpukan campuran — dan tumpukan campuran justru yang mewakili muatan
truk sungguhan.

Karena itu tugasnya dipecah:

    Model 1a  YOLO, 3 kelas STRUKTURAL   -> di mana tandannya
              (tandan / janjang kosong / abnormal)
    Model 1b  head CORAL, 4 tingkat      -> seberapa matang tandan itu

Head kematangan melihat crop tunggal tanpa konteks tumpukan, sehingga
tidak punya adegan untuk dihafal. Setelah pemisahan ini akurasi muatan
campuran naik ke 0,6346 dan kesalahan >=2 tingkat turun 9,17% -> 1,50%.

## Batas yang harus ikut dibaca

Akurasi 0,6346 pada muatan campuran menempatkan komponen kematangan di
**keyakinan sedang**: bahan diskusi, BELUM cukup untuk memotong
pembayaran. `low_confidence` pada tiap deteksi bukan hiasan — itu
mekanisme yang membuat sistem menunjuk apa yang perlu dilihat manusia.

## `rotten` tidak pernah dikeluarkan

Kontrak memuat tujuh kelas, tetapi data latih hanya punya enam. Tidak
ada crop `rotten` sama sekali, jadi model ini tidak akan pernah
mengeluarkannya. Disebut di sini alih-alih dibiarkan jadi teka-teki.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[2]
BOBOT_DETEKTOR = ROOT / "ai" / "weights" / "runs" / "A_per_tumpukan" / "weights" / "best.pt"
BOBOT_HEAD = ROOT / "ai" / "weights" / "head_ordinal_v3_inset_campuran.pt"

# Kelas struktural YOLO -> nama kontrak.
STRUKTURAL = {0: "tandan", 1: "empty_bunch", 2: "abnormal"}

# Indeks ordinal head -> nama kontrak (lihat types/index.ts).
ORDINAL = ["unripe", "underripe", "ripe", "overripe"]

# Di bawah ini deteksi ditandai perlu diperiksa manusia. Dipisah karena
# keduanya menjawab pertanyaan berbeda: yang pertama "apakah ini benar
# tandan", yang kedua "apakah tingkat kematangannya bisa dipercaya".
AMBANG_KOTAK = 0.25
AMBANG_KEMATANGAN = 0.60

# Pad negatif, sama persis dengan yang dipakai saat melatih head
# (ai/training/extract_crops.py --pad -0.08). Kalau angka ini berbeda
# antara latih dan pakai, head menerima gambar yang tidak pernah
# dilihatnya sewaktu belajar.
PAD_CROP = -0.08


@dataclass(frozen=True)
class Detection:
    """Satu tandan. Cerminan `Detection` di backend/app/schemas/models.py."""

    bbox: tuple[float, float, float, float]   # x1,y1,x2,y2 ternormalisasi
    ripeness: str
    confidence: float
    low_confidence: bool = False

    def sebagai_dict(self) -> dict:
        return asdict(self)


class Detector:
    """Model 1 utuh: dari citra ke daftar tandan berkelas.

    Bobot dimuat malas (lazy) supaya mengimpor modul ini tidak menahan
    startup backend selama beberapa detik. Pemanasan eksplisit dilakukan
    lewat `warmup()` di lifespan FastAPI.
    """

    def __init__(self, *, bobot_detektor: Path | None = None,
                 bobot_head: Path | None = None, device: str = "cpu",
                 imgsz: int = 640, ambang_kotak: float = AMBANG_KOTAK):
        self.bobot_detektor = Path(bobot_detektor or BOBOT_DETEKTOR)
        self.bobot_head = Path(bobot_head or BOBOT_HEAD)
        self.device = device
        self.imgsz = imgsz
        self.ambang_kotak = ambang_kotak
        self._yolo = None
        self._head = None
        self._tf = None
        self._mode_head = "ce"
        self.varian_head = "?"
        self.ukuran_crop = 128

    # -- pemuatan ----------------------------------------------------

    @property
    def siap(self) -> bool:
        return self._yolo is not None and self._head is not None

    def warmup(self) -> "Detector":
        """Muat kedua bobot sekarang, bukan saat request pertama datang.

        Request pertama yang menanggung biaya pemuatan model akan tampak
        seperti sistem yang menggantung — tepat pada saat juri mencobanya.
        """
        self._muat_yolo()
        self._muat_head()
        return self

    def _muat_yolo(self):
        if self._yolo is None:
            if not self.bobot_detektor.exists():
                raise FileNotFoundError(
                    f"bobot detektor tidak ada di {self.bobot_detektor}. "
                    "Jalankan pelatihan di ai/notebooks/04_train_detektor.ipynb "
                    "atau salin dari rilis.")
            from ultralytics import YOLO
            self._yolo = YOLO(str(self.bobot_detektor))
        return self._yolo

    def _muat_head(self):
        """Muat head kematangan, dengan SELURUH pengaturan dibaca dari
        checkpoint alih-alih ditulis ulang di sini.

        Ukuran citra, normalisasi, dan mode loss disimpan bersama bobot
        justru supaya tidak ada kesempatan salah pasang. Menuliskannya
        lagi di sisi inferensi adalah cara paling umum head menerima
        gambar yang tidak pernah dilihatnya sewaktu belajar — dan
        gejalanya bukan error, melainkan akurasi yang diam-diam anjlok.
        """
        if self._head is None:
            if not self.bobot_head.exists():
                raise FileNotFoundError(
                    f"bobot head kematangan tidak ada di {self.bobot_head}.")
            import torch
            from torchvision import transforms

            sys.path.insert(0, str(ROOT / "ai" / "notebooks"))
            import ordinal_lib as OL

            ck = torch.load(self.bobot_head, map_location=self.device)
            sd = ck.get("state_dict", ck) if isinstance(ck, dict) else ck

            # CoralHead punya `head.fc.weight`; Linear biasa punya
            # `head.weight`. Bentuk bobotnya sendiri yang memberi tahu.
            self._mode_head = "coral" if "head.fc.weight" in sd else "ce"
            self.varian_head = ck.get("varian", "?") if isinstance(ck, dict) else "?"

            model = OL.Model(len(ORDINAL), mode=self._mode_head)
            model.load_state_dict(sd)
            model.eval().to(self.device)
            self._head = model

            size = int(ck.get("size", 128)) if isinstance(ck, dict) else 128
            mean = ck.get("mean", [0.485, 0.456, 0.406]) if isinstance(ck, dict) else [0.485, 0.456, 0.406]
            std = ck.get("std", [0.229, 0.224, 0.225]) if isinstance(ck, dict) else [0.229, 0.224, 0.225]
            self.ukuran_crop = size
            self._tf = transforms.Compose([
                transforms.Resize((size, size)),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
            ])
        return self._head

    # -- inferensi ---------------------------------------------------

    @staticmethod
    def _potong(img, kotak, pad: float = PAD_CROP):
        """Ambil crop dengan pad NEGATIF — memotong ke dalam kotak.

        Tepi kotak adalah bagian yang paling mungkin memuat latar dan
        tandan tetangga. Membuangnya terbukti membantu, tetapi hanya
        ketika digabung dengan pelatihan pada tumpukan campuran; sendirian
        ia justru merugikan (lihat docs/experiments.md bagian 6).
        """
        w, h = img.size
        x1, y1, x2, y2 = kotak
        bw, bh = x2 - x1, y2 - y1
        px, py = bw * pad, bh * pad
        cx1 = int(max(0, x1 - px))
        cy1 = int(max(0, y1 - py))
        cx2 = int(min(w, x2 + px))
        cy2 = int(min(h, y2 + py))
        if cx2 - cx1 < 8 or cy2 - cy1 < 8:      # jaga-jaga kalau pad terlalu negatif
            cx1, cy1, cx2, cy2 = int(x1), int(y1), int(x2), int(y2)
        return img.crop((cx1, cy1, cx2, cy2))

    def predict(self, gambar) -> list[Detection]:
        """Dari citra ke daftar tandan. Ini API yang dipanggil backend.

        `gambar` boleh berupa path, objek PIL.Image, atau array numpy.
        """
        import torch
        from PIL import Image

        yolo = self._muat_yolo()
        head = self._muat_head()

        img = (Image.open(gambar).convert("RGB")
               if isinstance(gambar, (str, Path)) else gambar)
        if not hasattr(img, "crop"):
            img = Image.fromarray(np.asarray(img)).convert("RGB")
        W, H = img.size

        hasil = yolo.predict(img, imgsz=self.imgsz, conf=self.ambang_kotak,
                             device=self.device, verbose=False)[0]

        keluaran: list[Detection] = []
        crops, indeks = [], []

        for i, kotak in enumerate(hasil.boxes):
            x1, y1, x2, y2 = (float(v) for v in kotak.xyxy[0].tolist())
            conf = float(kotak.conf[0])
            kelas = STRUKTURAL.get(int(kotak.cls[0]), "abnormal")
            bbox = (x1 / W, y1 / H, x2 / W, y2 / H)

            if kelas != "tandan":
                # Janjang kosong dan abnormal tidak punya tingkat
                # kematangan — memaksakan salah satu tingkat kepada
                # mereka akan mengarang informasi.
                keluaran.append(Detection(
                    bbox=bbox, ripeness=kelas, confidence=conf,
                    low_confidence=conf < AMBANG_KOTAK * 2))
                continue

            crops.append(self._tf(self._potong(img, (x1, y1, x2, y2))))
            indeks.append((bbox, conf))

        if crops:
            with torch.no_grad():
                batch = torch.stack(crops).to(self.device)
                logits = head(batch)
                if self._mode_head == "coral":
                    # Tiap ambang menjawab "apakah lebih matang dari k?".
                    # Keyakinan = seberapa tegas ambang-ambang itu dijawab;
                    # semuanya di dekat 0,5 berarti model sebenarnya tidak
                    # memutuskan apa-apa.
                    p = torch.sigmoid(logits)
                    tingkat = (p > 0.5).sum(dim=1).cpu().numpy()
                    ketegasan = (2 * (p - 0.5).abs()).mean(dim=1).cpu().numpy()
                else:
                    p = torch.softmax(logits, dim=1)
                    tingkat = p.argmax(dim=1).cpu().numpy()
                    ketegasan = p.max(dim=1).values.cpu().numpy()

            for (bbox, conf_kotak), t, tegas in zip(indeks, tingkat, ketegasan):
                t = int(np.clip(t, 0, len(ORDINAL) - 1))
                gabungan = float(conf_kotak * tegas)
                keluaran.append(Detection(
                    bbox=bbox, ripeness=ORDINAL[t], confidence=gabungan,
                    low_confidence=gabungan < AMBANG_KEMATANGAN))

        return keluaran

    # -- ringkasan untuk Model 2 -------------------------------------

    @staticmethod
    def komposisi_terlihat(deteksi: list[Detection]) -> dict[str, float]:
        """Proporsi tiap tingkat pada LAPISAN YANG TERLIHAT.

        Ini BUKAN komposisi muatan. Menyamakan keduanya persis kesalahan
        yang dilawan sistem ini — permukaan bisa ditata. Keluaran ini
        adalah masukan untuk Model 2, bukan jawaban akhir.
        """
        tandan = [d for d in deteksi if d.ripeness in ORDINAL]
        if not tandan:
            return {k: 0.0 for k in ORDINAL}
        n = len(tandan)
        return {k: sum(1 for d in tandan if d.ripeness == k) / n for k in ORDINAL}


# GATE AI-1 menyebut API ini dengan nama tersebut; disediakan sebagai
# fungsi tingkat modul supaya backend tidak perlu tahu soal daur hidup
# objek.
_bawaan: Detector | None = None


def detector_bawaan() -> Detector:
    global _bawaan
    if _bawaan is None:
        _bawaan = Detector()
    return _bawaan


def predict(gambar) -> list[Detection]:
    """Bentuk fungsi dari `Detector.predict`, memakai satu instans bersama."""
    return detector_bawaan().predict(gambar)


def _peragaan() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("gambar", nargs="?", help="path citra tumpukan")
    args = ap.parse_args()

    d = Detector()
    print(f"bobot detektor : {d.bobot_detektor}")
    print(f"  ada          : {d.bobot_detektor.exists()}")
    print(f"bobot head     : {d.bobot_head}")
    print(f"  ada          : {d.bobot_head.exists()}")

    if not args.gambar:
        print("\nBerikan path citra untuk mencoba inferensi:")
        print("  python ai/perception/detector.py <gambar.jpg>")
        return

    hasil = d.predict(args.gambar)
    print(f"\nvarian head {d.varian_head} · mode {d._mode_head} · "
          f"crop {d.ukuran_crop}px")
    print(f"{len(hasil)} tandan terdeteksi")
    hit: dict[str, int] = {}
    for x in hasil:
        hit[x.ripeness] = hit.get(x.ripeness, 0) + 1
    for k, v in sorted(hit.items(), key=lambda z: -z[1]):
        print(f"  {k:14s} {v:4d}")
    ragu = sum(1 for x in hasil if x.low_confidence)
    print(f"\nperlu diperiksa manusia: {ragu} ({ragu / max(len(hasil), 1):.1%})")
    print(f"komposisi terlihat: {Detector.komposisi_terlihat(hasil)}")


if __name__ == "__main__":
    _peragaan()
