import type { Confidence, Estimate } from '@/types'
import { CONFIDENCE_ACTION, CONFIDENCE_LABEL, fmtEstimate, margin } from '@/lib/format'
import { cn } from '@/lib/utils'

/** Angka hasil model + selangnya, sebagai satu satuan yang tak terpisah.
 *  Sengaja tidak ada varian "tanpa selang": begitu selang boleh
 *  dimatikan, ia akan dimatikan. */
export function EstimateValue({
  estimate,
  unit,
  digits = 1,
  className,
}: {
  estimate: Estimate
  unit?: string
  digits?: 0 | 1 | 2
  className?: string
}) {
  return (
    <span className={cn('tnum whitespace-nowrap', className)}>
      {fmtEstimate(estimate, unit, digits)}
    </span>
  )
}

/** Batang nilai dengan pita selang di atasnya.
 *  Pita itu yang membuat "68% ± 5" terlihat, bukan cuma terbaca. */
export function EstimateBar({
  estimate,
  max,
  fill,
  label,
}: {
  estimate: Estimate
  max: number
  fill: string
  label?: string
}) {
  const pct = (n: number) => `${Math.max(0, Math.min(100, (n / max) * 100))}%`

  return (
    <div className="w-full">
      <div className="relative h-3 w-full rounded-sm bg-plane">
        {/* isian utama: ujung data membulat 4px, pangkal siku di garis dasar */}
        <div
          className="absolute inset-y-0 left-0 rounded-r-[4px]"
          style={{ width: pct(estimate.value), background: fill }}
        />
        {/* pita selang: putih menembus isian supaya terbaca di atas warna */}
        <div
          className="absolute inset-y-0 border-x-2 border-white/85 bg-white/25"
          style={{
            left: pct(estimate.lo),
            width: pct(estimate.hi - estimate.lo),
          }}
          aria-hidden
        />
      </div>
      {label && <div className="mt-1 text-[12px] text-ink-soft">{label}</div>}
    </div>
  )
}

export const CONFIDENCE_DOT: Record<Confidence, string> = {
  low: 'bg-unknown',
  medium: 'bg-supplier',
  high: 'bg-mill',
}

/** Keyakinan selalu tampil sebagai IKON + TEKS, tidak pernah warna saja --
 *  palet ini satu keluarga hue, jadi warna tidak boleh memikul makna
 *  sendirian. */
export function ConfidenceChip({
  level,
  showAction = false,
}: {
  level: Confidence
  showAction?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5" title={CONFIDENCE_ACTION[level]}>
      <span className={cn('h-2 w-2 shrink-0 rounded-full', CONFIDENCE_DOT[level])} aria-hidden />
      <span className="text-[12px] text-ink-soft">
        {CONFIDENCE_LABEL[level]}
        {showAction && <> · {CONFIDENCE_ACTION[level]}</>}
      </span>
    </span>
  )
}

/** Lebar selang relatif terhadap nilainya -- pembaca butuh tahu bukan
 *  cuma "berapa", tapi "seberapa goyah". */
export function spread(e: Estimate): number {
  return e.value === 0 ? 0 : margin(e) / Math.abs(e.value)
}
