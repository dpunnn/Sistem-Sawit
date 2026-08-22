
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field




class Estimate(BaseModel):
    """Taksiran dengan selang. TIDAK ADA varian tanpa selang.

    Begitu selang boleh dimatikan, ia akan dimatikan — dan angka pasti
    yang lahir dari masukan tidak pasti adalah kebohongan matematis.
    Menjadikan ini tipe resmi berarti janji "jujur soal ketidakpastian"
    ditegakkan sistem tipe, bukan niat baik.
    """

    model_config = {"json_schema_extra": {
        "examples": [{"value": 1166.0, "lo": 1148.0, "hi": 1186.0}]}}

    value: float = Field(..., description="Titik tengah taksiran")
    lo: float = Field(..., description="Batas bawah selang 90%")
    hi: float = Field(..., description="Batas atas selang 90%")

    @computed_field  
    @property
    def width(self) -> float:
        return self.hi - self.lo


class Confidence(str, Enum):
    """Tingkat keyakinan, DAN konsekuensi tindakannya.

    Angka yang sama tidak boleh memicu konsekuensi yang sama bila
    keyakinannya berbeda. Inilah bentuk konkret *learning to defer*:
    model tahu kapan dirinya belum cukup yakin untuk mengambil alih
    keputusan manusia.
    """

    LOW = "low"        # ditampilkan saja, tidak memicu tindakan
    MEDIUM = "medium"  # bahan diskusi, belum untuk memotong pembayaran
    HIGH = "high"      # boleh jadi dasar keputusan finansial


class RipenessClass(str, Enum):

    UNRIPE = "unripe"
    UNDERRIPE = "underripe"
    RIPE = "ripe"
    OVERRIPE = "overripe"
    # Ada di kontrak tetapi TIDAK PERNAH dikeluarkan model: data latih
    # tidak punya satu pun crop busuk. Dibiarkan di enum supaya kontrak
    # tidak perlu berubah kalau nanti datanya ada, dan disebut di sini
    # supaya ketiadaannya tidak jadi teka-teki.
    ROTTEN = "rotten"

    # Di luar sumbu kematangan — bukan bagian ramp ordinal.
    EMPTY_BUNCH = "empty_bunch"
    ABNORMAL = "abnormal"


class Side(str, Enum):


    SUPPLIER = "supplier"
    MILL = "mill"
    UNKNOWN = "unknown"




class Detection(BaseModel):
    """Satu tandan hasil Model 1."""

    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    ripeness: RipenessClass
    confidence: float
    low_confidence: bool = False  


class CompositionItem(BaseModel):
    ripeness: RipenessClass
    percent: Estimate


class SupplierInfo(BaseModel):
    """Identitas muatan. Berasal dari basis data, tidak pernah dari layar."""

    name: str
    kind: str
    truck_plate: str
    gross_weight_kg: float
    queue_hours: float
    shift_date: date


class DeductionBasis(BaseModel):
    """Aritmetika potongan, lengkap dengan sitasi koefisiennya.

    Dikirim utuh supaya petani yang membantah bisa menelusuri sumbernya
    sendiri. Koefisien tidak pernah ditulis di frontend: kalau nilainya
    berubah, layar yang menyalinnya akan memamerkan angka lama sambil
    terlihat sangat meyakinkan.
    """

    unripe_pct: float
    coefficient_per_pct: float
    coefficient_status: str
    coefficient_source: str = Field(..., description="Kunci sumber di coefficients.yaml")
    citation: dict[str, str | None] = Field(
        default_factory=dict,
        description="Judul, penerbit, dan URL — supaya bisa ditelusuri sendiri")
    points: float
    formula: str


class GradingResult(BaseModel):
    """Keluaran gabungan Model 1 + 2 + 4 untuk satu muatan truk."""

    batch_id: int | None = None
    supplier: SupplierInfo | None = None
    deduction_basis: DeductionBasis | None = None
    detections: list[Detection]
    overlay_url: str | None = None

    composition: list[CompositionItem]

    potential_oil_kg: Estimate

    low_confidence_count: int = 0
    model_version: str
    processed_at: datetime




class LossAttribution(BaseModel):
    """Satu baris atribusi kehilangan (Model 6)."""

    cause: str
    side: Side
    points: Estimate          
    confidence: Confidence
    detail: str | None = None 


class StationLoss(BaseModel):
    """Kehilangan minyak terukur di satu stasiun pabrik.

    PERINGATAN SATUAN. `oil_content_pct` adalah kadar minyak DI DALAM
    aliran itu (persen terhadap contoh), bukan persen terhadap TBS.
    Menjumlahkan kolom itu memberi ~18% dan rendemen mustahil ~3%.
    Yang boleh dijumlahkan hanya `points`, yaitu kadar x nisbah massa.
    """

    station: str
    oil_content_pct: float
    mass_ratio: float
    points: float
    standard_pct: float | None = None


class GraderDecision(BaseModel):
    """Keputusan grader atas satu hasil grading.

    Tiap koreksi adalah data latih untuk kalibrasi ulang -- itu yang
    dijanjikan layar gerbang, jadi jalurnya harus benar-benar ada.
    """

    decision: Literal["agree", "correct"]
    note: str | None = None
    corrected_composition: list[CompositionItem] | None = None


class BalanceCard(BaseModel):

    shift_date: date

    potential_theoretical: float 
    supplier_losses: list[LossAttribution]

    potential_realistic: float   
    mill_losses: list[LossAttribution]
    unexplained: LossAttribution

    actual_oer: float

    loss_value_idr: float

    # Rincian kehilangan sisi pabrik per stasiun. Bagian neraca yang
    # bisa diaudit tanpa membongkar model sama sekali.
    station_losses: list[StationLoss] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def total_loss_points(self) -> float:
        return round(self.potential_theoretical - self.actual_oer, 3)


# --------------------------------------------------------------------
# Respons tambahan
# --------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Satu perintah untuk membuktikan API dan Postgres tersambung."""

    status: Literal["ok", "degraded"]
    version: str
    database: bool = Field(..., description="Koneksi Postgres hidup")
    detector_ready: bool = Field(..., description="Bobot model sudah dimuat")
    coefficients_healthy: bool = Field(
        ..., description="Tiap koefisien domain punya sumber yang terdaftar")


class LossCause(LossAttribution):
    """Penyebab kehilangan, lengkap dengan boleh-tidaknya jadi potongan."""

    may_deduct_payment: bool = Field(
        ...,
        description=(
            "Keyakinan `high` DAN selang tidak memuat nol. Dua syarat, bukan "
            "satu: selang yang masih memuat nol berarti kemungkinan 'tidak ada "
            "kehilangan sama sekali' belum tersingkir."
        ))
    action_threshold: str = Field(..., description="Terjemahan keyakinan jadi tindakan")


class AttributionResponse(BaseModel):
    shift_date: date
    total_loss_points: float
    causes: list[LossCause]
    share: dict[str, float] = Field(
        ..., description="Pangsa tiap pihak atas total selisih, 0..1")
    uncertainty_widens: bool = Field(
        ...,
        description=(
            "Apakah selang baris tak terjelaskan LEBIH LEBAR daripada seluruh "
            "penyumbangnya. Harus selalu true — selisih dua angka tidak pasti "
            "ragamnya menjumlah. Kalau false, ada yang keliru pada perambatan."
        ))
    closure_error: float = Field(
        ..., description="Sisa aritmetika neraca. Harus ~0 sampai presisi mesin.")
    coefficient_mode: str
    notes: list[str] = Field(
        default_factory=list,
        description="Koefisien yang dilewati dan kenapa. Sengaja tidak disembunyikan.")
