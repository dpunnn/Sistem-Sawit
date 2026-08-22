"""Orkestrasi grading: gambar masuk -> Model 1, 2, 4 -> response.

ATURAN 3: backend adalah JEMBATAN, bukan pemilik logika.

Tidak ada satu pun rumus rendemen di berkas ini. Yang ada hanya urutan
langkah dan penerjemahan bentuk. Kalau ada aritmetika domain menyelinap
ke sini, lapisannya bocor — dan gejalanya bukan error, melainkan dua
tempat yang menghitung hal sama dengan cara berbeda.

## Kenapa service, bukan langsung di router

Router mengurus HTTP: status code, bentuk request, validasi. Service
mengurus langkah. Pemisahan itu membuat seluruh alur bisa diuji tanpa
menyalakan server, dan membuat `ai/` bisa ditukar tanpa menyentuh
router sama sekali.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ai.perception import composition as M2  # noqa: E402
from ai.perception import overlay as OV  # noqa: E402
from ai.perception import potential as M4  # noqa: E402
from ai.perception.detector import Detector  # noqa: E402

from app.services import kontrak  # noqa: E402

# Folder tempat gambar overlay ditulis, lalu disajikan sebagai file
# statis. Frontend cukup memasang <img src=...>.
DIR_OVERLAY = ROOT / "data" / "overlays"

# Berat rata-rata satu tandan (kg). Dipakai menaksir berapa tandan ada
# di dalam muatan, yang menentukan lebar selang Model 2: melihat 30
# tandan dari 100 sangat berbeda dari melihat 30 dari 400.
#
# Nilai ini BELUM terverifikasi ke sumber terbit. Ia tidak mempengaruhi
# titik tengah, hanya lebar selang — dan arah kesalahannya aman: kalau
# ditaksir terlalu kecil, selangnya jadi lebih lebar, bukan lebih sempit.
BERAT_TANDAN_KG = 22.0

VERSI_MODEL = "detector-A/head-V3"


@dataclass
class HasilGrading:
    detections: list
    composition: dict
    potential_oil_kg: dict
    low_confidence_count: int
    overlay_url: str | None
    model_version: str
    processed_at: datetime
    n_terlihat: int
    n_tandan_taksiran: int


class LayananGrading:
    """Menyimpan satu detektor yang dipanaskan sekali, dipakai berkali-kali."""

    def __init__(self) -> None:
        self.detector = Detector()

    def warmup(self) -> None:
        """Muat bobot saat startup, bukan saat request pertama.

        Request pertama ke model yang belum dimuat bisa makan 10-20
        detik. Kalau itu terjadi di depan juri, yang terlihat bukan
        "model besar" melainkan "sistem lambat".
        """
        self.detector.warmup()

    @property
    def siap(self) -> bool:
        return self.detector.siap

    # ----------------------------------------------------------------

    def proses(self, gambar_path: Path, berat_bruto_kg: float,
               *, simpan_overlay: bool = True) -> HasilGrading:
        """Satu muatan, dari citra sampai kilogram."""
        # --- Model 1: di mana tandannya, seberapa matang ---
        deteksi = self.detector.predict(gambar_path)

        # --- overlay: bukti visual yang bisa dilampirkan ---
        overlay_url = None
        if simpan_overlay and deteksi:
            nama = f"{uuid.uuid4().hex[:12]}.jpg"
            OV.simpan(gambar_path, deteksi, DIR_OVERLAY / nama)
            overlay_url = f"/static/overlays/{nama}"

        # --- Model 2: dari permukaan ke SELURUH muatan ---
        terlihat = Detector.komposisi_terlihat(deteksi)
        n_terlihat = sum(1 for d in deteksi if d.ripeness in kontrak.KELAS_BALIK)
        n_taksiran = max(n_terlihat, int(round(berat_bruto_kg / BERAT_TANDAN_KG)))

        # Model 2 memakai nama internal; terjemahkan masuk lalu keluar.
        terlihat_ai = {kontrak.KELAS_BALIK[k]: v for k, v in terlihat.items()}
        selang = M2.infer(terlihat_ai, n_terlihat=max(n_terlihat, 1),
                          n_tandan_taksiran=n_taksiran)

        komposisi = {
            kontrak.kelas(k): {"value": round(v.nilai * 100, 2),
                               "lo": round(v.lo * 100, 2),
                               "hi": round(v.hi * 100, 2)}
            for k, v in selang.items()
        }

        # --- Model 4: komposisi jadi kilogram ---
        komposisi_selang = {k: (v.lo, v.nilai, v.hi) for k, v in selang.items()}
        potensi = M4.estimate(komposisi_selang, berat_bruto_kg)

        return HasilGrading(
            detections=[
                {"bbox": list(d.bbox), "ripeness": d.ripeness,
                 "confidence": round(d.confidence, 4),
                 "low_confidence": d.low_confidence}
                for d in deteksi
            ],
            composition=komposisi,
            potential_oil_kg={"value": round(potensi.potensi_kg, 2),
                              "lo": round(potensi.potensi_lo, 2),
                              "hi": round(potensi.potensi_hi, 2)},
            low_confidence_count=sum(1 for d in deteksi if d.low_confidence),
            overlay_url=overlay_url,
            model_version=VERSI_MODEL,
            processed_at=datetime.now(timezone.utc),
            n_terlihat=n_terlihat,
            n_tandan_taksiran=n_taksiran,
        )


# Satu instans bersama untuk seluruh aplikasi.
layanan = LayananGrading()
