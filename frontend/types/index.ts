// Tipe ini WAJIB cerminan dari backend/app/schemas/models.py.
// Kalau salah satu berubah, ubah keduanya.

/** Taksiran dengan selang. Jangan pernah pakai number polos untuk
 *  nilai hasil model -- seluruh sistem berjanji jujur soal
 *  ketidakpastian, termasuk di frontend. */
export type Estimate = { value: number; lo: number; hi: number }

export type Confidence = 'low' | 'medium' | 'high'
export type Side = 'supplier' | 'mill' | 'unknown'

export type RipenessClass =
  | 'unripe'
  | 'underripe'
  | 'ripe'
  | 'overripe'
  | 'rotten'
  | 'empty_bunch'
  | 'abnormal'

/** Satu tandan hasil Model 1. */
export type Detection = {
  bbox: [number, number, number, number] // x1, y1, x2, y2
  ripeness: RipenessClass
  confidence: number
  low_confidence: boolean // default false
}

export type CompositionItem = {
  ripeness: RipenessClass
  percent: Estimate
}

/** Keluaran gabungan Model 1 + 2 + 4 untuk satu muatan truk. */
export type GradingResult = {
  batch_id: number | null
  detections: Detection[]
  overlay_url: string | null
  composition: CompositionItem[]
  potential_oil_kg: Estimate
  low_confidence_count: number // default 0
  model_version: string
  processed_at: string // ISO datetime
}

/** Satu baris atribusi kehilangan (Model 6). */
export type LossAttribution = {
  cause: string
  side: Side
  points: Estimate
  confidence: Confidence
  detail: string | null
}

export type BalanceCard = {
  shift_date: string // ISO date (YYYY-MM-DD)
  potential_theoretical: number
  supplier_losses: LossAttribution[]
  potential_realistic: number
  mill_losses: LossAttribution[]
  unexplained: LossAttribution
  actual_oer: number
  loss_value_idr: number
}

// --- Helpers for computed_field equivalents (Pydantic computes these; TS types are static) ---

/** Mirrors Estimate.width (hi - lo). */
export function estimateWidth(e: Estimate): number {
  return e.hi - e.lo
}

/** Mirrors BalanceCard.total_loss_points (rounded to 3 decimals). */
export function totalLossPoints(card: Pick<BalanceCard, 'potential_theoretical' | 'actual_oer'>): number {
  return Math.round((card.potential_theoretical - card.actual_oer) * 1000) / 1000
}