'use client'

import { useId, useState } from 'react'
import type { BalanceCard, LossAttribution } from '@/types'
import { SIDE_FILL, SIDE_LABEL, fmtPoint, margin } from '@/lib/format'

/** Waterfall dari potensi teoretis turun ke rendemen aktual.
 *
 *  Keputusan encoding:
 *  - Satu sumbu saja (poin OER). Tidak pernah dua skala.
 *  - Warna mengikuti SISI (pemasok / pabrik / tak terjelaskan), bukan
 *    besar-kecilnya batang. Menyaring satu penyebab tidak mengecat ulang
 *    yang lain.
 *  - Karamel (pemasok) berada di bawah 3:1 terhadap permukaan, jadi tiap
 *    batang WAJIB berlabel langsung dan punya kembaran tabel.
 *  - Batang "tidak terjelaskan" memakai arsiran 45derajat + garis putus:
 *    ia netral dan kontras rendah, jadi hue tidak boleh memikul maknanya.
 *  - Pita galat memakai selang asli tiap penyebab, bukan hiasan. */

const W = 760
const H = 300
const PAD = { top: 24, right: 16, bottom: 56, left: 52 }
const BAR = 24 // batang tipis; sisa slot dibiarkan jadi udara
const GAP = 2 // celah permukaan antar batang

type Step = {
  key: string
  label: string
  kind: 'anchor' | 'loss'
  side?: LossAttribution['side']
  from: number
  to: number
  loss?: LossAttribution
}

/** `floor` = dasar sumbu, bukan nol.
 *  Sumbu sengaja dipotong (18–22%) karena seluruh cerita terjadi di
 *  rentang dua poin; memaksa mulai dari nol akan meratakan justru
 *  perbedaan yang jadi inti halaman ini. Batang jangkar karena itu
 *  harus tumbuh dari dasar sumbu -- kalau dibiarkan mulai dari 0 ia
 *  akan menjulur jauh ke bawah bidang gambar. */
function buildSteps(b: BalanceCard, floor: number): Step[] {
  const steps: Step[] = []
  let cursor = b.potential_theoretical

  steps.push({
    key: 'potensi',
    label: 'Potensi teoretis',
    kind: 'anchor',
    from: floor,
    to: cursor,
  })

  for (const l of [...b.supplier_losses, ...b.mill_losses, b.unexplained]) {
    const next = cursor - l.points.value
    steps.push({
      key: l.cause,
      label: l.cause,
      kind: 'loss',
      side: l.side,
      from: next,
      to: cursor,
      loss: l,
    })
    cursor = next
  }

  steps.push({
    key: 'aktual',
    label: 'Rendemen aktual',
    kind: 'anchor',
    from: floor,
    to: b.actual_oer,
  })

  return steps
}

export function Waterfall({ balance }: { balance: BalanceCard }) {
  const [active, setActive] = useState<string | null>(null)
  const hatchId = useId()

  const yMax = Math.ceil(balance.potential_theoretical + 0.6)
  const yMin = Math.floor(balance.actual_oer - 1.2)
  const steps = buildSteps(balance, yMin)

  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const slot = plotW / steps.length

  const y = (v: number) => PAD.top + plotH * (1 - (v - yMin) / (yMax - yMin))
  const xCenter = (i: number) => PAD.left + slot * i + slot / 2

  const ticks = Array.from({ length: yMax - yMin + 1 }, (_, i) => yMin + i)

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full min-w-[680px]"
        role="img"
        aria-label="Waterfall kehilangan rendemen dari potensi teoretis ke rendemen aktual"
      >
        <defs>
          {/* Kanal cadangan untuk baris tak terjelaskan. */}
          <pattern
            id={hatchId}
            width="7"
            height="7"
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
          >
            <rect width="7" height="7" fill="#e6e2da" />
            <line x1="0" y1="0" x2="0" y2="7" stroke="#a89e8d" strokeWidth="2.5" />
          </pattern>
        </defs>

        {/* Grid: hairline solid, tidak pernah putus-putus. */}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              y1={y(t)}
              x2={W - PAD.right}
              y2={y(t)}
              stroke="#e5dbc9"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 10}
              y={y(t) + 4}
              textAnchor="end"
              className="tnum"
              fontSize="11"
              fill="#6b5844"
            >
              {t}%
            </text>
          </g>
        ))}

        {steps.map((s, i) => {
          const cx = xCenter(i)
          const top = y(s.to)
          const bottom = y(s.from)
          const h = Math.max(bottom - top - GAP, 2)
          const isAnchor = s.kind === 'anchor'
          const fill = isAnchor
            ? '#7d3f14'
            : s.side === 'unknown'
              ? `url(#${hatchId})`
              : SIDE_FILL[s.side!]
          const dim = active !== null && active !== s.key

          return (
            <g
              key={s.key}
              opacity={dim ? 0.35 : 1}
              onMouseEnter={() => setActive(s.key)}
              onMouseLeave={() => setActive(null)}
              style={{ transition: 'opacity 120ms' }}
            >
              {/* target hover lebih besar dari batangnya */}
              <rect
                x={cx - slot / 2}
                y={PAD.top}
                width={slot}
                height={plotH}
                fill="transparent"
              />

              {/* garis penghubung ke langkah berikutnya */}
              {!isAnchor && i < steps.length - 1 && (
                <line
                  x1={cx - BAR / 2}
                  y1={top}
                  x2={cx - slot + BAR / 2}
                  y2={top}
                  stroke="#cbbfa8"
                  strokeWidth="1"
                />
              )}

              <rect
                x={cx - BAR / 2}
                y={top}
                width={BAR}
                height={h}
                rx="4"
                fill={fill}
                stroke={s.side === 'unknown' ? '#a89e8d' : 'none'}
                strokeWidth={s.side === 'unknown' ? 1 : 0}
                strokeDasharray={s.side === 'unknown' ? '3 2' : undefined}
              />

              {/* pita selang -- ketidakpastian penyebab ini, bukan hiasan */}
              {s.loss && margin(s.loss.points) > 0 && (
                <g stroke="#2a1c10" strokeWidth="1.25" opacity="0.65">
                  <line
                    x1={cx}
                    y1={y(s.from + margin(s.loss.points))}
                    x2={cx}
                    y2={y(s.from - margin(s.loss.points))}
                  />
                  <line
                    x1={cx - 5}
                    y1={y(s.from + margin(s.loss.points))}
                    x2={cx + 5}
                    y2={y(s.from + margin(s.loss.points))}
                  />
                  <line
                    x1={cx - 5}
                    y1={y(s.from - margin(s.loss.points))}
                    x2={cx + 5}
                    y2={y(s.from - margin(s.loss.points))}
                  />
                </g>
              )}

              {/* label langsung -- wajib, karena isian karamel di bawah 3:1 */}
              <text
                x={cx}
                y={top - 8}
                textAnchor="middle"
                className="tnum"
                fontSize="11.5"
                fontWeight="600"
                fill="#2a1c10"
              >
                {isAnchor ? `${fmtPoint(s.to)}%` : `−${fmtPoint(s.to - s.from)}`}
              </text>

              {/* nama langkah, dipotong dua baris supaya tidak bertabrakan */}
              {wrap(s.label).map((line, li) => (
                <text
                  key={li}
                  x={cx}
                  y={PAD.top + plotH + 16 + li * 12}
                  textAnchor="middle"
                  fontSize="10.5"
                  fill="#6b5844"
                >
                  {line}
                </text>
              ))}
            </g>
          )
        })}

        {/* garis dasar */}
        <line
          x1={PAD.left}
          y1={PAD.top + plotH}
          x2={W - PAD.right}
          y2={PAD.top + plotH}
          stroke="#cbbfa8"
          strokeWidth="1"
        />
      </svg>

      <p className="mt-2 text-[11px] text-ink-soft">
        Sumbu tegak dipotong, mulai dari {yMin}% — seluruh selisih yang dibahas
        halaman ini terjadi dalam rentang beberapa poin saja.
      </p>

      {active && <ActiveNote steps={steps} active={active} />}
    </div>
  )
}

function ActiveNote({ steps, active }: { steps: Step[]; active: string }) {
  const s = steps.find((x) => x.key === active)
  if (!s?.loss) return null
  const l = s.loss
  return (
    <div className="mt-3 rounded-lg border border-line bg-plane px-4 py-3 text-[13px]">
      <div className="font-medium text-ink">
        {l.cause} · {SIDE_LABEL[l.side]}
      </div>
      <div className="tnum mt-1 text-ink-soft">
        {fmtPoint(l.points.value)} ± {fmtPoint(margin(l.points))} poin OER
      </div>
      {l.detail && <div className="mt-1 text-ink-soft">{l.detail}</div>}
    </div>
  )
}

/** Pemenggal label sederhana: dua baris, supaya teks sumbu tidak
 *  saling tabrak dan tidak pernah terpotong oleh mark-nya sendiri. */
function wrap(label: string): string[] {
  const words = label.split(' ')
  if (words.length < 2) return [label]
  const mid = Math.ceil(words.length / 2)
  return [words.slice(0, mid).join(' '), words.slice(mid).join(' ')]
}
