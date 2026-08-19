import type { Confidence } from '@/types'
import { CONFIDENCE_ACTION, CONFIDENCE_LABEL } from '@/lib/format'
import { CONFIDENCE_DOT } from '@/components/ui/Estimate'
import { cn } from '@/lib/utils'

const LEVELS: Confidence[] = ['low', 'medium', 'high']

/** Ambang tindakan, dieja terbuka di layar.
 *
 *  Tanpa tabel ini, "keyakinan sedang" cuma label yang enak dibaca.
 *  Dengan tabel ini ia jadi janji yang bisa ditagih: angka yang sama
 *  TIDAK BOLEH memicu konsekuensi yang sama bila keyakinannya berbeda.
 *  Ini bentuk konkret learning to defer -- model tahu kapan dirinya
 *  belum cukup yakin untuk mengambil alih keputusan manusia. */
export function ActionThresholds() {
  return (
    <table className="w-full text-[13px]">
      <caption className="sr-only">
        Tingkat keyakinan dan tindakan yang boleh didasarkan padanya
      </caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">
            Keyakinan
          </th>
          <th scope="col" className="pb-2 font-normal">
            Boleh dipakai untuk
          </th>
        </tr>
      </thead>
      <tbody>
        {LEVELS.map((level) => (
          <tr key={level} className="border-t border-line align-baseline">
            <th scope="row" className="whitespace-nowrap py-2.5 pr-4 text-left font-normal text-ink">
              <span className="flex items-center gap-1.5">
                <span
                  className={cn('h-2 w-2 shrink-0 rounded-full', CONFIDENCE_DOT[level])}
                  aria-hidden
                />
                {CONFIDENCE_LABEL[level]}
              </span>
            </th>
            <td className="py-2.5 text-ink-soft">{CONFIDENCE_ACTION[level]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
