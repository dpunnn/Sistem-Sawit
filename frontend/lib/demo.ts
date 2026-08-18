// Data contoh untuk membangun & mendemokan tampilan selagi model masih
// dilatih dan router backend belum terpasang.
//
// Angka di sini SENGAJA konsisten dengan contoh di proposal (Bagian 8.3)
// supaya momen panggung dan dokumen bercerita hal yang sama:
//   21,4 potensi - 19,2 aktual = 2,2 poin, terurai jadi 5 penyebab.
//
// Layar yang memakai berkas ini WAJIB menandainya sebagai data contoh
// (lihat komponen SourceBadge) -- jangan pernah biarkan data simulasi
// tampil seolah hasil pengukuran.

import type { BalanceCard, Detection, GradingResult, RipenessClass } from '@/types'

/** 24 tandan; 14 di antaranya berkeyakinan rendah -- angka yang sama
 *  dengan contoh layar gerbang di proposal. */
const detections: Detection[] = [
  { bbox: [0.06, 0.12, 0.22, 0.34], ripeness: 'ripe', confidence: 0.94 },
  { bbox: [0.24, 0.08, 0.39, 0.29], ripeness: 'ripe', confidence: 0.91 },
  { bbox: [0.41, 0.1, 0.55, 0.3], ripeness: 'unripe', confidence: 0.58, low_confidence: true },
  { bbox: [0.57, 0.07, 0.72, 0.28], ripeness: 'ripe', confidence: 0.89 },
  { bbox: [0.74, 0.11, 0.9, 0.33], ripeness: 'overripe', confidence: 0.55, low_confidence: true },
  { bbox: [0.04, 0.36, 0.19, 0.56], ripeness: 'ripe', confidence: 0.87 },
  { bbox: [0.21, 0.33, 0.36, 0.54], ripeness: 'underripe', confidence: 0.49, low_confidence: true },
  { bbox: [0.38, 0.34, 0.53, 0.55], ripeness: 'ripe', confidence: 0.92 },
  { bbox: [0.55, 0.32, 0.7, 0.53], ripeness: 'ripe', confidence: 0.88 },
  { bbox: [0.72, 0.36, 0.88, 0.57], ripeness: 'unripe', confidence: 0.61, low_confidence: true },
  { bbox: [0.08, 0.58, 0.23, 0.79], ripeness: 'empty_bunch', confidence: 0.52, low_confidence: true },
  { bbox: [0.25, 0.57, 0.4, 0.78], ripeness: 'ripe', confidence: 0.9 },
  { bbox: [0.42, 0.59, 0.57, 0.8], ripeness: 'rotten', confidence: 0.47, low_confidence: true },
  { bbox: [0.59, 0.56, 0.74, 0.77], ripeness: 'ripe', confidence: 0.86 },
  { bbox: [0.76, 0.6, 0.92, 0.81], ripeness: 'overripe', confidence: 0.53, low_confidence: true },
  { bbox: [0.12, 0.8, 0.27, 0.97], ripeness: 'ripe', confidence: 0.84 },
  { bbox: [0.29, 0.81, 0.44, 0.98], ripeness: 'unripe', confidence: 0.44, low_confidence: true },
  { bbox: [0.46, 0.82, 0.61, 0.99], ripeness: 'ripe', confidence: 0.83 },
  { bbox: [0.63, 0.8, 0.78, 0.97], ripeness: 'underripe', confidence: 0.5, low_confidence: true },
  { bbox: [0.8, 0.83, 0.95, 0.99], ripeness: 'ripe', confidence: 0.81 },
  { bbox: [0.02, 0.24, 0.13, 0.42], ripeness: 'abnormal', confidence: 0.46, low_confidence: true },
  { bbox: [0.33, 0.2, 0.44, 0.38], ripeness: 'ripe', confidence: 0.57, low_confidence: true },
  { bbox: [0.64, 0.44, 0.76, 0.62], ripeness: 'unripe', confidence: 0.51, low_confidence: true },
  { bbox: [0.88, 0.26, 0.98, 0.45], ripeness: 'empty_bunch', confidence: 0.54, low_confidence: true },
]

export const demoGrading: GradingResult = {
  batch_id: 4821,
  detections,
  overlay_url: null,
  // Menjumlah tepat 100%. Selang melebar pada kelas yang paling sering
  // tertukar (mentah/setengah matang), bukan seragam -- itu bagian dari
  // jujur soal ketidakpastian.
  composition: [
    { ripeness: 'unripe', percent: { value: 12, lo: 9, hi: 15 } },
    { ripeness: 'underripe', percent: { value: 8, lo: 5.5, hi: 10.5 } },
    { ripeness: 'ripe', percent: { value: 62, lo: 57, hi: 67 } },
    { ripeness: 'overripe', percent: { value: 9, lo: 7, hi: 11 } },
    { ripeness: 'rotten', percent: { value: 4, lo: 2.8, hi: 5.2 } },
    { ripeness: 'empty_bunch', percent: { value: 3, lo: 2.1, hi: 3.9 } },
    { ripeness: 'abnormal', percent: { value: 2, lo: 1.2, hi: 2.8 } },
  ],
  potential_oil_kg: { value: 4280, lo: 4090, hi: 4470 },
  low_confidence_count: detections.filter((d) => d.low_confidence).length,
  model_version: 'demo-0.1.0',
  processed_at: '2026-08-03T14:22:00Z',
}

/** Muatan yang sama, tapi didominasi buah mentah. Kelasnya diturunkan
 *  DAN keyakinannya ikut turun: mentah vs setengah matang adalah pasangan
 *  yang paling sering tertukar, jadi wajar detektor lebih ragu di sini. */
const UNRIPE_MIX: RipenessClass[] = [
  'unripe',
  'unripe',
  'underripe',
  'unripe',
  'ripe',
  'unripe',
  'underripe',
  'ripe',
  'unripe',
  'abnormal',
]

const unripeDetections: Detection[] = detections.map((d, i) => {
  const confidence = Math.round((d.confidence - 0.12) * 100) / 100
  return {
    ...d,
    ripeness: UNRIPE_MIX[i % UNRIPE_MIX.length],
    confidence,
    low_confidence: confidence < 0.65,
  }
})

/** Skenario demo kedua (README - Skenario Demo, langkah 2).
 *
 *  Dua hal yang WAJIB terlihat saat berpindah ke muatan ini: potensi
 *  minyak turun drastis, dan selangnya MELEBAR. Yang kedua itu bukan
 *  hiasan -- komposisi yang timpang lebih sulit ditaksir dari lapisan
 *  permukaan saja, jadi sistem harus mengaku lebih tidak yakin. */
export const demoGradingUnripe: GradingResult = {
  batch_id: 4822,
  detections: unripeDetections,
  overlay_url: null,
  // Tetap menjumlah 100%. Selang jauh lebih lebar daripada muatan bagus.
  composition: [
    { ripeness: 'unripe', percent: { value: 41, lo: 33, hi: 49 } },
    { ripeness: 'underripe', percent: { value: 19, lo: 14, hi: 24 } },
    { ripeness: 'ripe', percent: { value: 27, lo: 21, hi: 33 } },
    { ripeness: 'overripe', percent: { value: 5, lo: 3.4, hi: 6.6 } },
    { ripeness: 'rotten', percent: { value: 3, lo: 1.8, hi: 4.2 } },
    { ripeness: 'empty_bunch', percent: { value: 3, lo: 2, hi: 4 } },
    { ripeness: 'abnormal', percent: { value: 2, lo: 1.1, hi: 2.9 } },
  ],
  potential_oil_kg: { value: 3120, lo: 2790, hi: 3450 },
  low_confidence_count: unripeDetections.filter((d) => d.low_confidence).length,
  model_version: 'demo-0.1.0',
  processed_at: '2026-08-03T15:06:00Z',
}

export const demoBalance: BalanceCard = {
  shift_date: '2026-08-03',
  potential_theoretical: 21.4,

  supplier_losses: [
    {
      cause: 'Buah mentah',
      side: 'supplier',
      points: { value: 0.7, lo: 0.45, hi: 0.95 },
      confidence: 'medium',
      detail: 'Terkonsentrasi pada pemasok A, C, F',
    },
  ],

  potential_realistic: 20.7,

  mill_losses: [
    {
      cause: 'Restan 9 jam',
      side: 'mill',
      points: { value: 0.5, lo: 0.35, hi: 0.65 },
      confidence: 'high',
      detail: 'Keputusan antrian bongkar, bukan mutu buah',
    },
    {
      cause: 'Sterilisasi',
      side: 'mill',
      points: { value: 0.6, lo: 0.4, hi: 0.8 },
      confidence: 'medium',
      detail: 'Setelan tetap, tidak menyesuaikan komposisi muatan',
    },
    {
      cause: 'Ampas kempa',
      side: 'mill',
      points: { value: 0.2, lo: 0.1, hi: 0.3 },
      confidence: 'high',
      detail: 'Di atas standar 5%',
    },
  ],

  unexplained: {
    cause: 'Tidak terjelaskan',
    side: 'unknown',
    points: { value: 0.2, lo: -0.1, hi: 0.5 },
    confidence: 'low',
    detail: 'Perlu diperiksa: kebocoran, kalibrasi timbangan, atau galat ukur',
  },

  actual_oer: 19.2,
  loss_value_idr: 47_300_000,
  total_loss_points: 2.2,
}

/** Peringkat pemasok. Belum ada di kontrak Pydantic -- kalau backend
 *  nanti menyediakannya, tambahkan skemanya di kedua sisi sekaligus. */
export type SupplierRow = {
  name: string
  unripePct: number
  trend: number[]
  loads: number
}

export const demoSuppliers: SupplierRow[] = [
  { name: 'KUD Jaya Makmur', unripePct: 4.2, trend: [6.1, 5.4, 4.9, 4.2], loads: 38 },
  { name: 'KUD Tani Sejahtera', unripePct: 6.8, trend: [7.0, 6.6, 6.9, 6.8], loads: 24 },
  { name: 'Pemasok A', unripePct: 15.4, trend: [9.8, 11.6, 13.5, 15.4], loads: 31 },
  { name: 'Pemasok C', unripePct: 13.1, trend: [12.4, 12.9, 12.6, 13.1], loads: 19 },
  { name: 'Pemasok F', unripePct: 11.7, trend: [8.2, 9.4, 10.8, 11.7], loads: 22 },
]

/** Kehilangan minyak terukur per stasiun. Belum ada di kontrak Pydantic
 *  (tabel `station_loss` menyusul) -- kalau backend nanti menyediakannya,
 *  tambahkan skemanya di kedua sisi sekaligus. */
export type StationLossRow = {
  station: string
  stream: string
  pct: number
}

/** Nilai kalibrasi dari studi kasus terpublikasi, sama persis dengan
 *  yang dipakai simulator di `ai/simulator/mill.py`.
 *
 *  Angka-angka ini SENGAJA ditampilkan mentah di layar: inilah bagian
 *  sistem yang deterministik dan bisa diaudit siapa pun. Kalau juri
 *  ingin memeriksa dasar ilmiahnya, cukup satu berkas -- tidak perlu
 *  membongkar bobot model. */
export const demoStationLosses: StationLossRow[] = [
  { station: 'Sterilizer', stream: 'Kondensat', pct: 1.83 },
  { station: 'Thresher', stream: 'Janjang kosong', pct: 2.44 },
  { station: 'Press', stream: 'Ampas kempa', pct: 4.17 },
  { station: 'Press', stream: 'Nut in fiber', pct: 0.41 },
  { station: 'Klarifikasi', stream: 'Underflow CST', pct: 7.04 },
  { station: 'Klarifikasi', stream: 'Sludge', pct: 0.66 },
  { station: 'Klarifikasi', stream: 'Fat pit', pct: 0.81 },
  { station: 'Klarifikasi', stream: 'Deoiling pond', pct: 0.65 },
]

/** Kurva andalan: koreksi grader per 100 muatan, minggu ke minggu.
 *  Bukti sistem benar-benar mempelajari pabrik ini. */
export const demoCorrectionCurve = [
  { week: 'M1', corrections: 31 },
  { week: 'M2', corrections: 26 },
  { week: 'M3', corrections: 22 },
  { week: 'M4', corrections: 17 },
  { week: 'M5', corrections: 14 },
  { week: 'M6', corrections: 11 },
]
