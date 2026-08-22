
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field




class Estimate(BaseModel):
    
    value: float
    lo: float
    hi: float

    @computed_field  
    @property
    def width(self) -> float:
        return self.hi - self.lo


class Confidence(str, Enum):
 

    LOW = "low"        
    MEDIUM = "medium"  
    HIGH = "high"      


class RipenessClass(str, Enum):

    UNRIPE = "unripe"
    UNDERRIPE = "underripe"
    RIPE = "ripe"
    OVERRIPE = "overripe"
    ROTTEN = "rotten"
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


class GradingResult(BaseModel):
    """Keluaran gabungan Model 1 + 2 + 4 untuk satu muatan truk."""

    batch_id: int | None = None
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
