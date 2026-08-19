import type { CompositionItem } from '@/types'
import {
  RIPENESS_FILL,
  RIPENESS_LABEL,
  RIPENESS_ORDER,
  fmtPct,
  margin,
} from '@/lib/format'
import { EstimateBar } from '@/components/ui/Estimate'
import { Swatch } from '@/components/ui/Bits'

/** Komposisi muatan (Model 2), diurutkan mengikuti sumbu kematangan --
 *  bukan abjad, bukan besar-kecil. Urutan itu bagian dari maknanya.
 *
 *  Setiap baris diberi label langsung, sehingga nilai tidak pernah
 *  bergantung pada warna saja (isian karamel di bawah 3:1 terhadap
 *  permukaan -- label adalah kanal penggantinya). */
export function CompositionTable({ items }: { items: CompositionItem[] }) {
  const sorted = [...items].sort(
    (a, b) => RIPENESS_ORDER.indexOf(a.ripeness) - RIPENESS_ORDER.indexOf(b.ripeness),
  )
  const max = Math.max(...sorted.map((i) => i.percent.hi), 10)

  return (
    <table className="w-full">
      <caption className="sr-only">
        Komposisi muatan per kelas kematangan, dengan selang keyakinan
      </caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">Kelas</th>
          <th scope="col" className="pb-2 font-normal">Bagian muatan</th>
          <th scope="col" className="pb-2 text-right font-normal">Persen ± selang</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((it) => (
          <tr key={it.ripeness} className="border-t border-line">
            <th scope="row" className="py-2.5 pr-3 text-left text-[13px] font-normal text-ink">
              <span className="flex items-center gap-2">
                <Swatch fill={RIPENESS_FILL[it.ripeness]} />
                {RIPENESS_LABEL[it.ripeness]}
              </span>
            </th>
            <td className="w-1/2 py-2.5 pr-4">
              <EstimateBar
                estimate={it.percent}
                max={max}
                fill={RIPENESS_FILL[it.ripeness]}
              />
            </td>
            <td className="py-2.5 text-right text-[13px] text-ink">
              {fmtPct(it.percent.value)}
              <span className="text-ink-soft"> ± {margin(it.percent).toFixed(1)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
