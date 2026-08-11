"""Kontrak data sistem.

Keputusan desain terpenting ada di kelas `Estimate`: SELURUH keluaran
sistem yang berupa taksiran WAJIB memakai tipe ini, bukan float
telanjang. Dengan begitu prinsip "jujur soal ketidakyakinan" ditegakkan
oleh sistem tipe, bukan oleh niat baik programmer.

Alasannya bukan estetika: keluaran sistem ini dipakai untuk MENYALAHKAN
ORANG dan MEMOTONG UANG. Sistem yang mengaku pasti padahal tidak akan
runtuh begitu ada satu kasus salah yang viral.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------- dasar


class Estimate(BaseModel):
    """Taksiran dengan selang keyakinan. Jangan pernah pakai float polos."""

    value: float
    lo: float
    hi: float

    @computed_field  # type: ignore[misc]
    @property
    def width(self) -> float:
        return self.hi - self.lo


class Confidence(str, Enum):
    """Ambang tindakan — bentuk konkret prinsip `learning to defer`.

    Bukan sekadar label. Tiap tingkat menentukan APA yang boleh
    dilakukan sistem terhadap hasilnya.
    """

    LOW = "low"        # hanya ditampilkan, tidak memicu apa pun
    MEDIUM = "medium"  # bahan diskusi / pemeriksaan manual
    HIGH = "high"      # boleh jadi dasar keputusan finansial


class RipenessClass(str, Enum):
    """Kelas BERURUTAN (ordinal). Urutan di bawah bermakna, jangan diacak."""

    UNRIPE = "unripe"
    UNDERRIPE = "underripe"
    RIPE = "ripe"
    OVERRIPE = "overripe"
    ROTTEN = "rotten"
    EMPTY_BUNCH = "empty_bunch"  # di luar skala ordinal
    ABNORMAL = "abnormal"        # di luar skala ordinal


class Side(str, Enum):
    """Pihak yang bertanggung jawab atas suatu kehilangan.

    Inti dari tesis "menunjuk dua arah". Sistem yang hanya punya
    nilai SUPPLIER adalah alat pabrik untuk mengawasi petani.
    """

    SUPPLIER = "supplier"
    MILL = "mill"
    UNKNOWN = "unknown"


# ------------------------------------------------------------- Lapis 1


class Detection(BaseModel):
    """Satu tandan hasil Model 1."""

    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    ripeness: RipenessClass
    confidence: float
    low_confidence: bool = False  # ditandai untuk diperiksa manusia


class CompositionItem(BaseModel):
    ripeness: RipenessClass
    percent: Estimate


class GradingResult(BaseModel):
    """Keluaran gabungan Model 1 + 2 + 4 untuk satu muatan truk."""

    batch_id: int | None = None
    detections: list[Detection]
    overlay_url: str | None = None

    # Model 2 — komposisi SELURUH muatan, bukan yang terlihat saja
    composition: list[CompositionItem]

    # Model 4 — dalam KILOGRAM, ini yang bisa masuk neraca
    potential_oil_kg: Estimate

    low_confidence_count: int = 0
    model_version: str
    processed_at: datetime


# ------------------------------------------------------------- Lapis 2


class LossAttribution(BaseModel):
    """Satu baris atribusi kehilangan (Model 6)."""

    cause: str
    side: Side
    points: Estimate          # dalam poin OER
    confidence: Confidence
    detail: str | None = None  # mis. "pemasok A, C, F"


class BalanceCard(BaseModel):
    """Kartu neraca — KLIMAKS produk.

    Struktur 3 baris. Jangan pernah disederhanakan jadi 2 baris:
    kalau potensi langsung dibandingkan dengan aktual, buah mentah
    terhitung DUA KALI (sekali sebagai pengurang potensi, sekali lagi
    sebagai penyebab kehilangan) dan seluruh neraca jadi salah.
    """

    shift_date: date

    potential_theoretical: float  # andai SELURUH muatan matang
    supplier_losses: list[LossAttribution]

    potential_realistic: float    # muatan ini apa adanya
    mill_losses: list[LossAttribution]
    unexplained: LossAttribution

    actual_oer: float

    loss_value_idr: float

    @computed_field  # type: ignore[misc]
    @property
    def total_loss_points(self) -> float:
        return round(self.potential_theoretical - self.actual_oer, 3)
