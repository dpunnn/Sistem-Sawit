// Klien fetch ke backend. Selalu lewat path relatif /api/* supaya
// ditangani rewrites di next.config.js -- jangan pernah hardcode
// http://backend:8000 di sini, itu tidak dikenal browser.
import type {
  BalanceCard,
  CorrectionStats,
  GraderDecision,
  GradingResult,
  SupplierRank,
} from '@/types'
import { demoBalance, demoGrading } from './demo'

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

/** Router backend belum terpasang (lihat TODO di backend/app/main.py),
 *  jadi setiap pemanggilan wajib punya jalur mundur ke data contoh.
 *  Ini disengaja: kontrak tipe sudah disepakati di awal supaya frontend
 *  bisa dibangun penuh sementara model masih dilatih.
 *
 *  Yang TIDAK boleh: menelan sebab kegagalannya. Sebelumnya `catch {}`
 *  kosong membuat backend mati dan backend sehat terlihat sama persis
 *  di layar. Saat demo, itu berarti tidak ada yang tahu sistemnya
 *  sedang tidak terhubung sampai ada yang bertanya. */
async function withFallback<T>(
  path: string,
  fn: () => Promise<T>,
  fallback: T,
): Promise<Loaded<T>> {
  try {
    return { data: await fn(), source: 'live' }
  } catch (e) {
    return { data: fallback, source: 'demo', error: pesan(e, path) }
  }
}

export function fetchBalance(shift?: string): Promise<Loaded<BalanceCard>> {
  const q = shift ? `?shift_date=${encodeURIComponent(shift)}` : ''
  const path = `/balance${q}`
  return withFallback(path, () => getJSON<BalanceCard>(path), demoBalance)
}

export function fetchBatch(id: string): Promise<Loaded<GradingResult>> {
  const path = `/grading/${id}`
  return withFallback(path, () => getJSON<GradingResult>(path), {
    ...demoGrading,
    batch_id: Number(id) || demoGrading.batch_id,
  })
}

/** Peringkat pemasok, dihitung backend dari hasil grading tersimpan.
 *  Jalur mundurnya daftar KOSONG, bukan daftar karangan: kartu yang
 *  tidak punya data harus mengaku kosong, bukan menampilkan nama
 *  pemasok yang tidak pernah ada. */
export function fetchSuppliers(shift?: string): Promise<Loaded<SupplierRank[]>> {
  const q = shift ? `?shift_date=${encodeURIComponent(shift)}` : ''
  const path = `/suppliers${q}`
  return withFallback(path, () => getJSON<SupplierRank[]>(path), [])
}

/** Statistik koreksi grader. Jalur mundurnya `cukup_data: false`,
 *  supaya layar menampilkan keadaan kosong alih-alih tren palsu. */
export function fetchCorrections(): Promise<Loaded<CorrectionStats>> {
  const path = '/corrections'
  return withFallback(path, () => getJSON<CorrectionStats>(path), {
    n_keputusan: 0, n_koreksi: 0, rasio_koreksi: null,
    cukup_data: false, ambang_cukup_data: 20, per_minggu: [],
    catatan: 'Backend belum terhubung, jadi belum ada koreksi yang bisa dibaca.',
  })
}

/** Unggah foto muatan -> Model 1 + 2 + 4. */
export function gradeImage(file: File): Promise<Loaded<GradingResult>> {
  const body = new FormData()
  body.append('image', file)
  return withFallback(
    '/grading',
    () => getJSON<GradingResult>('/grading', { method: 'POST', body }),
    demoGrading,
  )
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
