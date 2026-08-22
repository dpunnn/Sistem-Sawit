import type { Detection, RipenessClass } from '@/types'
import { RIPENESS_FILL, RIPENESS_LABEL, RIPENESS_ORDER, fmtInt } from '@/lib/format'
import { Swatch } from '@/components/ui/Bits'

/** Hitungan tandan per kelas -- jembatan dari gambar ke angka.
 *
 *  Ini keluaran Model 1 (apa yang benar-benar TERLIHAT), bukan Model 2.
 *  Perbedaannya penting dan sengaja ditulis di layar: hitungan ini
 *  hanya mewakili lapisan permukaan, sementara persen di kartu
 *  komposisi adalah taksiran untuk SELURUH muatan. Menyamakan keduanya
 *  persis kesalahan yang dilawan sistem ini. */
export function DetectionCounts({ detections }: { detections: Detection[] }) {
  const hitung = new Map<RipenessClass, { n: number; ragu: number }>()
  for (const d of detections) {
    const cur = hitung.get(d.ripeness) ?? { n: 0, ragu: 0 }
    cur.n += 1
    if (d.low_confidence) cur.ragu += 1
    hitung.set(d.ripeness, cur)
  }

  const baris = RIPENESS_ORDER.filter((r) => hitung.has(r))
  const total = detections.length
  if (!total) return null

  return (
    <table className="w-full">
      <caption className="sr-only">
        Jumlah tandan terdeteksi per kelas kematangan pada lapisan permukaan
      </caption>
      <thead>
        <tr className="text-left text-[12px] text-ink-soft">
          <th scope="col" className="pb-2 font-normal">Kelas</th>
          <th scope="col" className="pb-2 text-right font-normal">Tandan</th>
          <th scope="col" className="pb-2 text-right font-normal">Bagian terlihat</th>
          <th scope="col" className="pb-2 text-right font-normal">Perlu diperiksa</th>
        </tr>
      </thead>
      <tbody>
        {baris.map((r) => {
          const { n, ragu } = hitung.get(r)!
          return (
            <tr key={r} className="border-t border-line">
              <th
                scope="row"
                className="py-2 pr-3 text-left text-[13px] font-normal text-ink"
              >
                <span className="flex items-center gap-2">
                  <Swatch fill={RIPENESS_FILL[r]} />
                  {RIPENESS_LABEL[r]}
                </span>
              </th>
              <td className="tnum py-2 text-right text-[13px] text-ink">{fmtInt(n)}</td>
              <td className="tnum py-2 text-right text-[13px] text-ink-soft">
                {((n / total) * 100).toFixed(1)}%
              </td>
              <td className="tnum py-2 text-right text-[13px] text-ink-soft">
                {ragu > 0 ? fmtInt(ragu) : '—'}
              </td>
            </tr>
          )
        })}
      </tbody>
      <tfoot>
        <tr className="border-t border-line">
          <th scope="row" className="py-2 pr-3 text-left text-[13px] font-medium text-ink">
            Total terlihat
          </th>
          <td className="tnum py-2 text-right text-[13px] font-medium text-ink">
            {fmtInt(total)}
          </td>
          <td className="py-2 text-right text-[13px] text-ink-soft">100%</td>
          <td className="tnum py-2 text-right text-[13px] text-ink-soft">
            {fmtInt(detections.filter((d) => d.low_confidence).length)}
          </td>
        </tr>
      </tfoot>
    </table>
  )
}
