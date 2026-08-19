// Klien fetch ke backend. Selalu lewat path relatif /api/* supaya
// ditangani rewrites di next.config.js -- jangan pernah hardcode
// http://backend:8000 di sini, itu tidak dikenal browser.
import type { BalanceCard, GradingResult } from '@/types'
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

export type Loaded<T> = { data: T; source: DataSource }

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(resolve(path), {
    cache: 'no-store',
    ...init,
  })
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`)
  return (await res.json()) as T
}

/** Router backend belum terpasang (lihat TODO di backend/app/main.py),
 *  jadi setiap pemanggilan wajib punya jalur mundur ke data contoh.
 *  Ini disengaja: kontrak tipe sudah disepakati di awal supaya frontend
 *  bisa dibangun penuh sementara model masih dilatih. */
async function withFallback<T>(fn: () => Promise<T>, fallback: T): Promise<Loaded<T>> {
  try {
    return { data: await fn(), source: 'live' }
  } catch {
    return { data: fallback, source: 'demo' }
  }
}

export function fetchBalance(shift?: string): Promise<Loaded<BalanceCard>> {
  const q = shift ? `?shift_date=${encodeURIComponent(shift)}` : ''
  return withFallback(() => getJSON<BalanceCard>(`/balance${q}`), demoBalance)
}

export function fetchBatch(id: string): Promise<Loaded<GradingResult>> {
  return withFallback(() => getJSON<GradingResult>(`/grading/${id}`), {
    ...demoGrading,
    batch_id: Number(id) || demoGrading.batch_id,
  })
}

/** Unggah foto muatan -> Model 1 + 2 + 4. */
export function gradeImage(file: File): Promise<Loaded<GradingResult>> {
  const body = new FormData()
  body.append('image', file)
  return withFallback(
    () => getJSON<GradingResult>('/grading', { method: 'POST', body }),
    demoGrading,
  )
}
