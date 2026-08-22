import type { BalanceCard, LossAttribution } from '@/types'
import { SIDE_FILL, SIDE_LABEL, fmtPoint, margin } from '@/lib/format'
import { ConfidenceChip } from '@/components/ui/Estimate'
import { Swatch, Warn } from '@/components/ui/Bits'

/** Kartu neraca tiga baris: potensi teoretis -> potensi realistis ->
 *  rendemen aktual, dengan kehilangan tiap sisi di antaranya.
 *
 *  Struktur ini yang membuat sistem "menunjuk ke dua arah" terbaca
 *  sebagai bentuk, bukan sebagai klaim. */
export function BalanceRows({ balance }: { balance: BalanceCard }) {
  const supplierTotal = sum(balance.supplier_losses)
  const millTotal = sum(balance.mill_losses)

  return (
    <div className="divide-y divide-line">
      {/* Asal-usul tiap baris ditulis terbuka.
       *
       *  Tanpa ini, orang wajar mengira SEMUA angka di kartu ini keluaran
       *  model — lalu bingung kenapa rendemen aktual tidak bergerak
       *  setelah memindai foto yang berbeda.
       *
       *  Catatan lama pada baris ini bahkan keliru: ia menulis "ditaksir
       *  Lapis 1 dari komposisi muatan", padahal potensi teoretis justru
       *  BUTA terhadap komposisi. Kebutaan itu bukan kekurangan — itu
       *  yang membuat baris kedua bisa berdiri sendiri sebagai kerugian
       *  akibat mutu, dan yang mencegah buah mentah dihitung dua kali. */}
      <Anchor
        label="Potensi rendemen muatan hari ini"
        value={balance.potential_theoretical}
        note="Dari koefisien terbit (rendemen tandan matang). Sengaja BUTA terhadap komposisi — tidak berubah saat memindai."
        asal="koefisien"
      />

      <LossGroup
        title="Kehilangan sisi pemasok"
        total={supplierTotal}
        items={balance.supplier_losses}
      />

      <Anchor
        label="Potensi realistis"
        value={balance.potential_realistic}
        note="Keluaran Model 2 + 4. Inilah satu-satunya baris yang BERUBAH setiap kali muatan dipindai."
        asal="model"
      />

      <LossGroup
        title="Kehilangan sisi pabrik"
        total={millTotal}
        items={balance.mill_losses}
      />

      <LossGroup
        title="Tidak terjelaskan"
        total={balance.unexplained.points.value}
        items={[balance.unexplained]}
        warn
      />

      <Anchor
        label="Rendemen aktual tercapai"
        value={balance.actual_oer}
        note="Dari jembatan timbang pabrik di akhir shift. Tidak tersentuh model — memindai foto tidak mengubah berapa CPO yang benar-benar keluar dari tangki."
        asal="timbangan"
        strong
      />
    </div>
  )
}

const ASAL: Record<string, string> = {
  koefisien: 'koefisien terbit',
  model: 'keluaran model',
  timbangan: 'jembatan timbang',
}

function Anchor({
  label,
  value,
  note,
  asal,
  strong,
}: {
  label: string
  value: number
  note?: string
  asal?: keyof typeof ASAL
  strong?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3">
      <div>
        <div
          className={
            strong
              ? 'flex flex-wrap items-baseline gap-2 text-[15px] font-semibold text-ink'
              : 'flex flex-wrap items-baseline gap-2 text-[14px] text-ink'
          }
        >
          {label}
          {asal && (
            <span className="rounded-full border border-line bg-plane px-2 py-0.5 text-[11px] font-normal text-ink-soft">
              {ASAL[asal]}
            </span>
          )}
        </div>
        {note && (
          <div className="mt-0.5 max-w-xl text-[12px] leading-relaxed text-ink-soft">
            {note}
          </div>
        )}
      </div>
      <div
        className={
          strong
            ? 'tnum text-[22px] font-semibold text-ink'
            : 'tnum text-[18px] font-medium text-ink'
        }
      >
        {fmtPoint(value)}%
      </div>
    </div>
  )
}

function LossGroup({
  title,
  total,
  items,
  warn,
}: {
  title: string
  total: number
  items: LossAttribution[]
  warn?: boolean
}) {
  const side = items[0]?.side ?? 'unknown'
  return (
    <div className="py-3 pl-4">
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-center gap-2 text-[13px] font-medium text-ink">
          <Swatch fill={SIDE_FILL[side]} hatched={side === 'unknown'} />
          {warn ? <Warn>{title}</Warn> : title}
        </div>
        <div className="tnum text-[14px] font-medium text-ink">−{fmtPoint(total)} poin</div>
      </div>

      <ul className="mt-2 space-y-2">
        {items.map((l) => (
          <li key={l.cause} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <div className="min-w-0">
              <div className="text-[13px] text-ink">{l.cause}</div>
              {l.detail && <div className="text-[12px] text-ink-soft">{l.detail}</div>}
              <div className="mt-0.5">
                <ConfidenceChip level={l.confidence} showAction />
              </div>
            </div>
            <div className="tnum shrink-0 text-[13px] text-ink-soft">
              {fmtPoint(l.points.value)} ± {fmtPoint(margin(l.points))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function sum(items: LossAttribution[]) {
  return items.reduce((a, l) => a + l.points.value, 0)
}

/** Kembaran tabel untuk waterfall.
 *  Tooltip tidak pernah jadi satu-satunya cara membaca nilai. */
export function AttributionTable({ balance }: { balance: BalanceCard }) {
  const rows = [...balance.supplier_losses, ...balance.mill_losses, balance.unexplained]

  return (
    <table className="w-full text-[13px]">
      <caption className="sr-only">
        Dekomposisi kehilangan rendemen per penyebab, dengan selang dan tingkat keyakinan
      </caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">Penyebab</th>
          <th scope="col" className="pb-2 font-normal">Sisi</th>
          <th scope="col" className="pb-2 text-right font-normal">Poin OER</th>
          <th scope="col" className="pb-2 text-right font-normal">Selang</th>
          <th scope="col" className="pb-2 font-normal">Boleh dipakai untuk</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((l) => (
          <tr key={l.cause} className="border-t border-line align-top">
            <th scope="row" className="py-2.5 pr-3 text-left font-normal text-ink">
              {l.cause}
            </th>
            <td className="py-2.5 pr-3">
              <span className="flex items-center gap-1.5 text-ink-soft">
                <Swatch fill={SIDE_FILL[l.side]} hatched={l.side === 'unknown'} />
                {SIDE_LABEL[l.side]}
              </span>
            </td>
            <td className="py-2.5 pr-3 text-right text-ink">{fmtPoint(l.points.value)}</td>
            <td className="py-2.5 pr-3 text-right text-ink-soft">
              {fmtPoint(l.points.lo)} – {fmtPoint(l.points.hi)}
            </td>
            <td className="py-2.5 text-ink-soft">
              <ConfidenceChip level={l.confidence} showAction />
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr className="border-t-2 border-line">
          <th scope="row" className="py-2.5 text-left font-medium text-ink">
            Total kehilangan
          </th>
          <td />
          <td className="py-2.5 pr-3 text-right font-medium text-ink">
            {fmtPoint(balance.total_loss_points)}
          </td>
          <td colSpan={2} />
        </tr>
      </tfoot>
    </table>
  )
}
