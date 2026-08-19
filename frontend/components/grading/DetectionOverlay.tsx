'use client'

import { useState } from 'react'
import type { Detection } from '@/types'
import { RIPENESS_FILL, RIPENESS_LABEL } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ScanPulse } from '@/components/grading/ScanPulse'

/** Foto muatan + kotak tiap tandan.
 *
 *  Prinsip layar ini: sistem MENUNJUK apa yang perlu diperiksa manusia,
 *  bukan menyuruh memeriksa semuanya. Karena itu tandan berkeyakinan
 *  rendah punya perlakuan visual sendiri (garis putus + arsiran), dan
 *  bisa disaring supaya hanya belasan yang tersisa di layar. */
export function DetectionOverlay({
  detections,
  imageUrl,
  onlyLowConfidence,
}: {
  detections: Detection[]
  imageUrl?: string | null
  onlyLowConfidence: boolean
}) {
  const [hover, setHover] = useState<number | null>(null)
  const shown = onlyLowConfidence
    ? detections.filter((d) => d.low_confidence)
    : detections

  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-lg border border-line bg-plane">
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt="Muatan truk" className="h-full w-full object-cover" />
      ) : (
        <Placeholder />
      )}

      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {shown.map((d, i) => {
          const [x1, y1, x2, y2] = d.bbox
          const isHover = hover === i
          return (
            <rect
              key={i}
              x={x1 * 100}
              y={y1 * 100}
              width={(x2 - x1) * 100}
              height={(y2 - y1) * 100}
              vectorEffect="non-scaling-stroke"
              fill={RIPENESS_FILL[d.ripeness]}
              fillOpacity={isHover ? 0.42 : 0.2}
              stroke={d.low_confidence ? '#2a1c10' : RIPENESS_FILL[d.ripeness]}
              strokeWidth={isHover ? 2.5 : 1.5}
              strokeDasharray={d.low_confidence ? '4 3' : undefined}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              className="cursor-pointer"
            />
          )
        })}
      </svg>

      {/* Titik pindai kamera -- di tengah muatan, di bawah tooltip. */}
      <ScanPulse className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />

      {hover !== null && shown[hover] && <Tip d={shown[hover]} />}

      <div className="absolute bottom-2 left-2 rounded-md bg-surface/95 px-2.5 py-1 text-[12px] text-ink-soft shadow-card">
        {shown.length} tandan ditampilkan
        {onlyLowConfidence && ' (hanya yang ragu)'}
      </div>
    </div>
  )
}

function Tip({ d }: { d: Detection }) {
  return (
    <div className="pointer-events-none absolute right-2 top-2 rounded-md border border-line bg-surface px-3 py-2 text-[12px] shadow-card">
      <div className="font-medium text-ink">{RIPENESS_LABEL[d.ripeness]}</div>
      <div className="tnum mt-0.5 text-ink-soft">
        Keyakinan {(d.confidence * 100).toFixed(0)}%
      </div>
      {d.low_confidence && (
        <div className="mt-1 text-ink-soft">Disarankan diperiksa grader</div>
      )}
    </div>
  )
}

/** Belum ada foto: gambarkan tumpukan tandan supaya tata letak layar
 *  tetap terbaca saat demo tanpa berkas. */
function Placeholder() {
  const dots = Array.from({ length: 26 }, (_, i) => ({
    cx: 8 + ((i * 37) % 84),
    cy: 12 + ((i * 53) % 76),
    r: 5 + ((i * 7) % 4),
    f: [
      '#cba871',
      '#b98a44',
      '#a06c22',
      '#7d4d18',
      '#54300e',
    ][i % 5],
  }))
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
      <rect width="100" height="100" fill="#f2ebdf" />
      {dots.map((d, i) => (
        <circle key={i} cx={d.cx} cy={d.cy} r={d.r} fill={d.f} opacity={0.55} />
      ))}
    </svg>
  )
}

export function ToggleLowConfidence({
  value,
  onChange,
  count,
}: {
  value: boolean
  onChange: (v: boolean) => void
  count: number
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={cn(
        'inline-flex min-h-[36px] items-center gap-2 rounded-lg border px-3 text-[13px] transition',
        value
          ? 'border-mill bg-mill text-white'
          : 'border-line bg-surface text-ink-soft hover:bg-plane',
      )}
    >
      Sorot {count} tandan yang ragu
    </button>
  )
}
