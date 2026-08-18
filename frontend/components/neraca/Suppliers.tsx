import type { SupplierRow } from '@/lib/demo'
import { fmtPct } from '@/lib/format'

/** Peringkat pemasok berdasarkan persen buah mentah.
 *
 *  Ini kategori NOMINAL (nama pemasok), jadi semua batang memakai satu
 *  warna yang sama -- mewarnai per nilai akan menduplikasi apa yang
 *  sudah dikatakan panjang batang, dan membuang kanal identitas.
 *  Karena satu seri, tidak perlu kotak legenda: judulnya sudah menyebut
 *  apa yang diplot. */
export function SupplierRanking({ rows }: { rows: SupplierRow[] }) {
  const sorted = [...rows].sort((a, b) => b.unripePct - a.unripePct)
  const max = Math.max(...sorted.map((r) => r.unripePct))

  return (
    <table className="w-full text-[13px]">
      <caption className="sr-only">Persen buah mentah per pemasok, minggu ini</caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">Pemasok</th>
          <th scope="col" className="pb-2 font-normal">Buah mentah</th>
          <th scope="col" className="pb-2 text-right font-normal">%</th>
          <th scope="col" className="pb-2 text-right font-normal">Arah 4 minggu</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => {
          const rising = r.trend[r.trend.length - 1] > r.trend[0] + 0.5
          return (
            <tr key={r.name} className="border-t border-line">
              <th scope="row" className="py-2.5 pr-3 text-left font-normal text-ink">
                {r.name}
                <span className="block text-[11px] text-ink-soft">{r.loads} muatan</span>
              </th>
              <td className="w-1/2 py-2.5 pr-4">
                <div className="h-3 w-full rounded-sm bg-plane">
                  <div
                    className="h-3 rounded-r-[4px] bg-supplier"
                    style={{ width: `${(r.unripePct / max) * 100}%` }}
                  />
                </div>
              </td>
              <td className="py-2.5 pr-3 text-right text-ink">{fmtPct(r.unripePct)}</td>
              <td className="py-2.5 text-right">
                <Spark values={r.trend} />
                <span className="ml-1.5 align-middle text-[11px] text-ink-soft">
                  {rising ? 'memburuk' : 'stabil / membaik'}
                </span>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Spark({ values }: { values: number[] }) {
  const w = 52
  const h = 16
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w
      const y = h - ((v - min) / span) * h
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <svg width={w} height={h} className="inline-block align-middle" aria-hidden>
      <polyline
        points={pts}
        fill="none"
        stroke="#cf8c2a"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/** Kurva andalan: koreksi grader turun dari minggu ke minggu.
 *  Satu seri -> satu warna, tanpa kotak legenda, hanya titik akhir yang
 *  diberi label. */
export function CorrectionCurve({
  data,
}: {
  data: { week: string; corrections: number }[]
}) {
  const W = 520
  const H = 150
  const PAD = { top: 16, right: 44, bottom: 26, left: 34 }
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  const max = Math.ceil(Math.max(...data.map((d) => d.corrections)) / 10) * 10
  const x = (i: number) => PAD.left + (i / (data.length - 1)) * plotW
  const y = (v: number) => PAD.top + plotH * (1 - v / max)

  const line = data.map((d, i) => `${x(i)},${y(d.corrections)}`).join(' ')
  const last = data[data.length - 1]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label="Koreksi grader per 100 muatan, menurun dari minggu ke minggu"
    >
      {[0, max / 2, max].map((t) => (
        <g key={t}>
          <line x1={PAD.left} y1={y(t)} x2={W - PAD.right} y2={y(t)} stroke="#e5dbc9" strokeWidth="1" />
          <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#6b5844" className="tnum">
            {t}
          </text>
        </g>
      ))}

      <polyline points={line} fill="none" stroke="#7d3f14" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

      {data.map((d, i) => (
        <g key={d.week}>
          <circle cx={x(i)} cy={y(d.corrections)} r="4" fill="#7d3f14" stroke="#ffffff" strokeWidth="2" />
          <text x={x(i)} y={H - 8} textAnchor="middle" fontSize="10" fill="#6b5844">
            {d.week}
          </text>
        </g>
      ))}

      {/* hanya titik akhir yang diberi label langsung */}
      <text
        x={x(data.length - 1) + 10}
        y={y(last.corrections) + 4}
        fontSize="11"
        fontWeight="600"
        fill="#2a1c10"
        className="tnum"
      >
        {last.corrections}
      </text>
    </svg>
  )
}
