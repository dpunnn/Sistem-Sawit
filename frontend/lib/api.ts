// Klien fetch ke backend. Selalu lewat path relatif /api/* supaya
// ditangani rewrites di next.config.js -- jangan pernah hardcode
// http://backend:8000 di sini, itu tidak dikenal browser.
import type {
  BalanceCard,
  BatchRow,
  CorrectionStats,
  GraderDecision,
  GradingResult,
  SupplierRank,
} from '@/types'

export const API_BASE = '/api'

/** Di browser, path relatif ditangani rewrites di next.config.js.
 *  Di server (React Server Component) tidak ada origin, jadi fetch
 *  dengan path relatif akan gagal -- di sana kita pakai API_URL
 *  langsung, host yang sama dengan tujuan rewrites itu. */
function resolve(path: string): string {
  if (typeof window !== 'undefined') return `${API_BASE}${path}`
  const origin = process.env.API_URL || 'http://localhost:8000'
  return `${origin}${API_BASE}${path}`
}

/** Sumber data yang benar-benar dipakai untuk sebuah tampilan.
 *  Dibawa sampai ke UI supaya layar bisa mengaku jujur ketika yang
 *  tampil adalah data contoh, bukan hasil model. */
export type DataSource = 'live' | 'demo'

export type Loaded<T> = {
  data: T
  source: DataSource
  /** Alasan kenapa jatuh ke data contoh. Kosong berarti memang belum
   *  ada backend yang dihubungi, BUKAN bahwa semuanya baik-baik saja. */
  error?: string
}

const TIMEOUT_MS = 15_000

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  // Tanpa batas waktu, backend yang menggantung membuat layar berputar
  // selamanya dan orang mengira aplikasinya yang rusak.
  const ac = new AbortController()
  const timer = setTimeout(() => ac.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(resolve(path), {
      cache: 'no-store',
      signal: ac.signal,
      ...init,
    })
    if (!res.ok) throw new Error(`${path} menjawab HTTP ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

function pesan(e: unknown, path: string): string {
  if (e instanceof DOMException && e.name === 'AbortError') {
    return `${path} tidak menjawab dalam ${TIMEOUT_MS / 1000} detik`
  }
  if (e instanceof Error) return e.message
  return `${path} gagal karena sebab yang tidak dikenali`
}

/** Ambil data, atau AKUI GAGAL.
 *
 *  Sebelumnya setiap kegagalan diganti data contoh: backend mati, id
 *  tidak ada, HTTP 500 — semuanya berubah jadi angka yang terlihat
 *  nyata, ditandai hanya oleh badge kecil di pojok.
 *
 *  Akibatnya bisa dilihat sendiri: tautan sertifikat menunjuk id 4821
 *  yang tidak pernah ada, dan yang muncul adalah halaman lengkap berisi
 *  "4.280 kg" seolah itu hasil pengukuran. Sistem forensik yang
 *  menampilkan angka karangan saat gagal kehilangan satu-satunya hal
 *  yang dijualnya.
 *
 *  Sekarang `data` bernilai null saat gagal, dan layar WAJIB
 *  menampilkan keadaan kosong atau pesan error — bukan angka. */
async function ambil<T>(path: string, fn: () => Promise<T>): Promise<Loaded<T | null>> {
  try {
    return { data: await fn(), source: 'live' }
  } catch (e) {
    return { data: null, source: 'demo', error: pesan(e, path) }
  }
}

export function fetchBalance(shift?: string): Promise<Loaded<BalanceCard | null>> {
  const q = shift ? `?shift_date=${encodeURIComponent(shift)}` : ''
  const path = `/balance${q}`
  return ambil(path, () => getJSON<BalanceCard>(path))
}

/** Daftar muatan truk pada shift. Dipakai layar gerbang untuk menautkan
 *  hasil grading ke muatan yang benar-benar tercatat. */
export function fetchBatches(): Promise<Loaded<BatchRow[] | null>> {
  return ambil('/batches', () => getJSON<BatchRow[]>('/batches'))
}

export function fetchBatch(id: string | number): Promise<Loaded<GradingResult | null>> {
  const path = `/grading/${id}`
  return ambil(path, () => getJSON<GradingResult>(path))
}

/** Peringkat pemasok, dihitung backend dari hasil grading tersimpan.
 *  Jalur mundurnya daftar KOSONG, bukan daftar karangan: kartu yang
 *  tidak punya data harus mengaku kosong, bukan menampilkan nama
 *  pemasok yang tidak pernah ada. */
export function fetchSuppliers(shift?: string): Promise<Loaded<SupplierRank[] | null>> {
  const q = shift ? `?shift_date=${encodeURIComponent(shift)}` : ''
  const path = `/suppliers${q}`
  return ambil(path, () => getJSON<SupplierRank[]>(path))
}

/** Statistik koreksi grader. Jalur mundurnya `cukup_data: false`,
 *  supaya layar menampilkan keadaan kosong alih-alih tren palsu. */
export function fetchCorrections(): Promise<Loaded<CorrectionStats | null>> {
  return ambil('/corrections', () => getJSON<CorrectionStats>('/corrections'))
}

/** Unggah foto muatan -> Model 1 + 2 + 4. */
export function gradeImage(file: File, opsi?: {
  gross_weight_kg?: number
  batch_id?: number
}): Promise<Loaded<GradingResult | null>> {
  const body = new FormData()
  body.append('image', file)
  if (opsi?.gross_weight_kg) body.append('gross_weight_kg', String(opsi.gross_weight_kg))
  // batch_id membuat hasilnya TERSIMPAN dan punya sertifikat sungguhan.
  // Tanpa itu, model tetap berjalan tetapi hasilnya hilang begitu layar
  // ditutup — dan tautan sertifikatnya menunjuk ke ketiadaan.
  if (opsi?.batch_id) body.append('batch_id', String(opsi.batch_id))
  return ambil('/grading', () =>
    getJSON<GradingResult>('/grading', { method: 'POST', body }))
}

/** Keputusan grader: setuju, atau koreksi beserta alasannya.
 *
 *  Layar menjanjikan "koreksi grader disimpan sebagai data latih".
 *  Selama fungsi ini tidak dipanggil, janji itu tidak ditepati kode --
 *  dan janji yang tidak ditepati kode adalah yang paling mudah
 *  ditemukan juri. */
export async function submitDecision(
  batchId: number,
  decision: GraderDecision,
): Promise<{ ok: boolean; error?: string }> {
  const path = `/grading/${batchId}/decision`
  try {
    await getJSON<{ status: string }>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: pesan(e, path) }
  }
}
