import type { StationLossRow } from '@/lib/demo'
import { SIDE_FILL } from '@/lib/format'

/** Kehilangan minyak terukur per stasiun -- bagian neraca yang paling
 *  membosankan, dan justru karena itu paling penting.
 *
 *  Di sini tidak ada model sama sekali: ini fisika dan akuntansi, angka
 *  lab harian yang sudah jadi pekerjaan rutin pabrik. Menampilkannya
 *  utuh adalah cara membuktikan bahwa Lapis 2 berdiri di atas dasar yang
 *  bisa dicek orang luar, bukan di atas kotak hitam. */
export function StationLosses({ rows }: { rows: StationLossRow[] }) {
  const max = Math.max(...rows.map((r) => r.pct))

  return (
    <table className="w-full text-[13px]">
      <caption className="sr-only">
        Kehilangan minyak per stasiun pabrik, dalam persen terhadap aliran yang diukur
      </caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">
            Stasiun
          </th>
          <th scope="col" className="pb-2 font-normal">
            Aliran yang diukur
          </th>
          <th scope="col" className="pb-2 font-normal">
            Kehilangan
          </th>
          <th scope="col" className="pb-2 text-right font-normal">
            Persen
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          // Nama stasiun ditulis sekali per kelompok: urutan sterilizer ->
          // thresher -> press -> klarifikasi adalah urutan proses, dan
          // pengulangan label mengaburkannya.
          const first = i === 0 || rows[i - 1].station !== r.station
          return (
            <tr key={`${r.station}-${r.stream}`} className={first ? 'border-t border-line' : ''}>
              <th
                scope="row"
                className="whitespace-nowrap py-2 pr-4 text-left align-baseline font-normal text-ink"
              >
                {first ? r.station : ''}
              </th>
              <td className="py-2 pr-4 align-baseline text-ink-soft">{r.stream}</td>
              <td className="w-1/2 py-2 pr-4 align-middle">
                <div className="h-2.5 w-full rounded-sm bg-plane">
                  <div
                    className="h-full rounded-r-[3px]"
                    style={{ width: `${(r.pct / max) * 100}%`, background: SIDE_FILL.mill }}
                  />
                </div>
              </td>
              <td className="tnum py-2 text-right align-baseline text-ink">
                {r.pct.toFixed(2).replace('.', ',')}%
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
