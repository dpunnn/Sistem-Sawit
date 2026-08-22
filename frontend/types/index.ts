// Tipe ini WAJIB cerminan dari backend/app/schemas/models.py.
// Kalau salah satu berubah, ubah keduanya dalam commit yang sama.

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

/** Satu tandan hasil Model 1. bbox = [x1, y1, x2, y2] ternormalisasi 0..1. */
export type Detection = {
  bbox: [number, number, number, number]
  ripeness: RipenessClass
  confidence: number
  low_confidence?: boolean
}

export type CompositionItem = {
  ripeness: RipenessClass
  percent: Estimate
}

/** Keluaran gabungan Model 1 + 2 + 4 untuk satu muatan truk. */
export type GradingResult = {
  batch_id?: number | null
  detections: Detection[]
  overlay_url?: string | null
  composition: CompositionItem[]
  potential_oil_kg: Estimate
  low_confidence_count: number
  model_version: string
  processed_at: string
}

/** Satu baris atribusi kehilangan (Model 6), dalam poin OER. */
export type LossAttribution = {
  cause: string
  side: Side
  points: Estimate
  confidence: Confidence
  detail?: string | null
}

/** Kehilangan minyak terukur di satu stasiun pabrik.
 *
 *  `oil_content_pct` adalah KADAR MINYAK DI DALAM ALIRAN ITU (persen
 *  terhadap contoh), bukan persen terhadap TBS. Keduanya sempat
 *  tertukar di sisi AI dan menghasilkan rendemen mustahil ~3%.
 *  Yang boleh dijumlahkan hanya `points`. */
export type StationLoss = {
  station: string
  oil_content_pct: number
  mass_ratio: number
  points: number
  standard_pct?: number | null
}

export type BalanceCard = {
  shift_date: string

  /** Potensi teoretis dari muatan yang masuk (%). */
  potential_theoretical: number
  supplier_losses: LossAttribution[]

  /** Potensi setelah kehilangan sisi pemasok dipotong (%). */
  potential_realistic: number
  mill_losses: LossAttribution[]
  unexplained: LossAttribution

  actual_oer: number
  loss_value_idr: number

  /** Rincian kehilangan sisi pabrik per stasiun. Bagian neraca yang
   *  bisa diaudit tanpa membongkar model sama sekali. */
  station_losses: StationLoss[]

  /** computed_field di backend: potential_theoretical - actual_oer. */
  total_loss_points: number
}

/** Keputusan grader atas satu hasil grading. Tiap koreksi adalah
 *  data latih untuk kalibrasi ulang. */
export type GraderDecision = {
  decision: 'agree' | 'correct'
  note?: string
  corrected_composition?: CompositionItem[]
}
