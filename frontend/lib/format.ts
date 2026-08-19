import type { Confidence, Estimate, RipenessClass, Side } from '@/types'

const idNum = (min: number, max = min) =>
  new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: min,
    maximumFractionDigits: max,
  })

export const fmtInt = (n: number) => idNum(0).format(n)
export const fmtPoint = (n: number) => idNum(1, 2).format(n)
export const fmtPct = (n: number) => `${idNum(0, 1).format(n)}%`

/** Rupiah dalam satuan yang bisa dibaca cepat di layar manajer. */
export function fmtIDR(n: number): string {
  if (n >= 1e12) return `Rp ${idNum(1).format(n / 1e12)} triliun`
  if (n >= 1e9) return `Rp ${idNum(1).format(n / 1e9)} miliar`
  if (n >= 1e6) return `Rp ${idNum(1).format(n / 1e6)} juta`
  return `Rp ${fmtInt(n)}`
}

/** Setengah lebar selang. Dipakai untuk menulis "nilai +/- margin". */
export const margin = (e: Estimate) => (e.hi - e.lo) / 2

/** Satu-satunya cara sah menuliskan hasil model di layar.
 *  Selalu "nilai ± margin" -- tidak pernah angka telanjang. */
export function fmtEstimate(e: Estimate, unit = '', digits: 0 | 1 | 2 = 1): string {
  const f = idNum(digits === 0 ? 0 : 1, digits)
  const u = unit ? ` ${unit}` : ''
  return `${f.format(e.value)} ± ${f.format(margin(e))}${u}`
}

export const RIPENESS_LABEL: Record<RipenessClass, string> = {
  unripe: 'Mentah',
  underripe: 'Setengah matang',
  ripe: 'Matang',
  overripe: 'Lewat matang',
  rotten: 'Busuk',
  empty_bunch: 'Janjang kosong',
  abnormal: 'Abnormal',
}

/** Urutan ordinal kematangan. Dipakai untuk mengurutkan tabel komposisi
 *  supaya barisnya mengikuti sumbu kematangan, bukan urutan abjad. */
export const RIPENESS_ORDER: RipenessClass[] = [
  'unripe',
  'underripe',
  'ripe',
  'overripe',
  'rotten',
  'empty_bunch',
  'abnormal',
]

export const RIPENESS_FILL: Record<RipenessClass, string> = {
  unripe: '#cba871',
  underripe: '#b98a44',
  ripe: '#a06c22',
  overripe: '#7d4d18',
  rotten: '#54300e',
  empty_bunch: '#d8d2c8',
  abnormal: '#b3aa9c',
}

/** Teks di dalam kotak berwarna: putih atau tinta, dipilih dari
 *  terangnya isian supaya kontras selalu lolos. */
export function inkOn(fill: string): string {
  const h = fill.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  return L > 0.42 ? '#2a1c10' : '#ffffff'
}

export const SIDE_LABEL: Record<Side, string> = {
  supplier: 'Sisi pemasok',
  mill: 'Sisi pabrik',
  unknown: 'Tidak terjelaskan',
}

export const SIDE_FILL: Record<Side, string> = {
  supplier: '#cf8c2a',
  mill: '#7d3f14',
  unknown: '#cfc8bc',
}

export const CONFIDENCE_LABEL: Record<Confidence, string> = {
  low: 'Keyakinan rendah',
  medium: 'Keyakinan sedang',
  high: 'Keyakinan tinggi',
}

/** Ambang tindakan -- inti janji "tahu kapan diam" (Bagian 7 proposal).
 *  Angka yang sama tidak boleh memicu konsekuensi yang sama bila
 *  keyakinannya berbeda. */
export const CONFIDENCE_ACTION: Record<Confidence, string> = {
  low: 'Ditampilkan saja, tidak memicu tindakan',
  medium: 'Cukup untuk bahan diskusi, belum untuk memotong pembayaran',
  high: 'Boleh jadi dasar keputusan finansial',
}
