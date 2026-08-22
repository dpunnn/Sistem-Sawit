import type { StationLoss } from '@/types'
import { SIDE_FILL, fmtPoint } from '@/lib/format'

/** Kehilangan minyak terukur per stasiun -- bagian neraca yang paling
 *  membosankan, dan justru karena itu paling penting.
 *
 *  Di sini tidak ada model sama sekali: ini fisika dan akuntansi, angka
 *  lab harian yang sudah jadi pekerjaan rutin pabrik. Menampilkannya
 *  utuh adalah cara membuktikan bahwa Lapis 2 berdiri di atas dasar yang
 *  bisa dicek orang luar, bukan di atas kotak hitam.
 *
 *  PANJANG BATANG MENGIKUTI POIN, BUKAN KADAR.
 *
 *  Ini bukan detail gaya. Kadar adalah persen minyak DI DALAM aliran
 *  itu; poin adalah dampaknya terhadap rendemen, yaitu kadar dikali
 *  nisbah massa aliran terhadap TBS. Dua besaran yang berbeda, dan
 *  memeringkatnya dengan kadar membalik kesimpulan:
 *
 *      underflow CST   7,04% terhadap contoh  ->  hanya 0,211 poin
 *      janjang kosong  4,51% terhadap contoh  ->      1,038 poin
 *
 *  Diurut menurut kadar, underflow CST terlihat sebagai masalah terbesar
 *  pabrik ini. Diurut menurut poin, ia nomor empat -- dan yang benar
 *  perlu diperbaiki adalah perebusannya. Kesalahan yang sama pernah
 *  terjadi di sisi AI dan menghasilkan rendemen mustahil ~3%. */
export function StationLosses({ rows }: { rows: StationLoss[] }) {
  const urut = [...rows].sort((a, b) => b.points - a.points)
  const max = Math.max(...urut.map((r) => r.points), 0.01)
  const total = urut.reduce((n, r) => n + r.points, 0)

  return (
    <>
      <table className="w-full text-[13px]">
        <caption className="sr-only">
          Kehilangan minyak per stasiun pabrik, diurutkan menurut dampaknya pada
          rendemen
        </caption>
        <thead>
          <tr className="text-left text-[12px] text-ink-soft">
            <th scope="col" className="pb-2 font-normal">Aliran yang diukur</th>
            <th scope="col" className="pb-2 text-right font-normal">Kadar</th>
            <th scope="col" className="pb-2 text-right font-normal">× nisbah</th>
            <th scope="col" className="pb-2 font-normal">Dampak rendemen</th>
            <th scope="col" className="pb-2 text-right font-normal">Poin</th>
          </tr>
        </thead>
        <tbody>
          {urut.map((r) => {
            const lewat = r.standard_pct != null && r.oil_content_pct > r.standard_pct
            return (
              <tr key={r.station} className="border-t border-line">
                <th
                  scope="row"
                  className="py-2 pr-4 text-left align-baseline font-normal text-ink"
                >
                  {r.station}
                </th>
                <td className="tnum py-2 pr-3 text-right align-baseline text-ink-soft">
                  {r.oil_content_pct.toFixed(2).replace('.', ',')}%
                  {r.standard_pct != null && (
                    <span className={lewat ? 'text-mill' : 'text-ink-muted'}>
                      {' '}
                      / {r.standard_pct.toFixed(1).replace('.', ',')}
                    </span>
                  )}
                </td>
                <td className="tnum py-2 pr-4 text-right align-baseline text-ink-muted">
                  {r.mass_ratio.toFixed(2).replace('.', ',')}
                </td>
                <td className="w-2/5 py-2 pr-4 align-middle">
                  <div className="h-2.5 w-full rounded-sm bg-plane">
                    <div
                      className="h-full rounded-r-[3px]"
                      style={{
                        width: `${(r.points / max) * 100}%`,
                        background: SIDE_FILL.mill,
                      }}
                    />
                  </div>
                </td>
                <td className="tnum py-2 text-right align-baseline text-ink">
                  {fmtPoint(r.points)}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr className="border-t border-line">
            <th scope="row" colSpan={4} className="py-2 pr-4 text-left font-medium text-ink">
              Total kehilangan proses
            </th>
            <td className="tnum py-2 text-right font-medium text-ink">{fmtPoint(total)}</td>
          </tr>
        </tfoot>
      </table>

      <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
        Kolom <strong>kadar</strong> adalah persen minyak di dalam aliran itu sendiri,
        bukan persen terhadap TBS — kolom itu <strong>tidak boleh dijumlahkan</strong>.
        Yang menjumlah adalah kolom poin, yaitu kadar dikali nisbah massa aliran
        terhadap TBS. Nisbah itu masih taksiran teknik dan belum tertelusur ke sumber
        terbit; totalnya mendarat di norma industri 1,5–1,75 poin untuk pabrik tanpa
        gangguan.
      </p>
    </>
  )
}
