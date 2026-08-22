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
/** Identitas muatan. Datang dari basis data, tidak pernah ditulis di layar. */
export type SupplierInfo = {
  name: string
  kind: string
  truck_plate: string
  gross_weight_kg: number
  queue_hours: number
  shift_date: string
}

/** Aritmetika potongan beserta sitasi koefisiennya.
 *
 *  Koefisien TIDAK BOLEH ditulis di frontend. Kalau nilainya berubah,
 *  layar yang menyalinnya akan memamerkan angka lama sambil terlihat
 *  sangat meyakinkan — dan yang dirugikan petani yang membaca
 *  sertifikatnya. */
export type DeductionBasis = {
  unripe_pct: number
  coefficient_per_pct: number
  coefficient_status: string
  coefficient_source: string
  citation: { judul?: string | null; penerbit?: string | null; url?: string | null }
  points: number
  formula?: string | null
}

/** Satu muatan truk yang tercatat di gerbang. */
export type BatchRow = {
  id: number
  truck_plate: string
  supplier: string
  kind: string
  gross_weight_kg: number
  queue_hours: number
  shift_date: string
  grading_id: number | null
  unripe_pct: number | null
}

export type SupplierRank = {
  name: string
  kind: string
  n_muatan: number
  unripe_pct: number | null
  ripe_pct: number | null
  gross_weight_kg: number
  queue_hours_avg: number
}

export type CorrectionStats = {
  n_keputusan: number
  n_koreksi: number
  rasio_koreksi: number | null
  cukup_data: boolean
  ambang_cukup_data: number
  per_minggu: { week: string; n_keputusan: number; n_koreksi: number; per_100_muatan: number }[]
  catatan: string
}

export type GradingResult = {
  /** Id MUATAN truk. */
  batch_id?: number | null
  /** Id HASIL GRADING — ini yang dipakai untuk tautan sertifikat. */
  grading_id?: number | null
  supplier?: SupplierInfo | null
  deduction_basis?: DeductionBasis | null
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
