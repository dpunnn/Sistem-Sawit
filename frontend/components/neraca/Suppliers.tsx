import type { CorrectionStats, SupplierRank } from '@/types'
import { fmtInt, fmtPct } from '@/lib/format'
import { EmptyState } from '@/components/ui/States'

/** Peringkat pemasok berdasarkan persen buah mentah.
 *
 *  Ini kategori NOMINAL (nama pemasok), jadi semua batang memakai satu
 *  warna yang sama -- mewarnai per nilai akan menduplikasi apa yang
 *  sudah dikatakan panjang batang, dan membuang kanal identitas.
 *  Karena satu seri, tidak perlu kotak legenda: judulnya sudah menyebut
 *  apa yang diplot.
 *
 *  KOLOM TREN DIBUANG. Versi sebelumnya menampilkan sparkline empat
 *  minggu berikut label "memburuk / stabil", padahal angkanya ditulis
 *  tangan di berkas demo -- sistem ini belum pernah berjalan empat
 *  minggu di pabrik mana pun. Menyebut satu pemasok "memburuk"
 *  berdasarkan data yang tidak ada adalah tuduhan, bukan analisis.
 *
 *  Yang tersisa hanyalah yang benar-benar bisa dihitung dari basis
 *  data: proporsi buah mentah, jumlah muatan, dan rata-rata restan. */
export function SupplierRanking({ rows }: { rows: SupplierRank[] }) {
  const sorted = [...rows]
    .filter((r) => r.unripe_pct !== null)
    .sort((a, b) => (b.unripe_pct ?? 0) - (a.unripe_pct ?? 0))

  if (!sorted.length) {
    return (
      <EmptyState
        title="Belum ada hasil grading yang tersimpan"
        hint="Peringkat muncul setelah ada muatan yang dinilai dan dikaitkan ke pemasok."
      />
    )
  }

  const max = Math.max(...sorted.map((r) => r.unripe_pct ?? 0), 1)

  return (
    <>
      <table className="w-full text-[13px]">
        <caption className="sr-only">
          Persen buah mentah per pemasok, dihitung dari hasil grading tersimpan
        </caption>
        <thead>
          <tr className="text-left text-[12px] text-ink-soft">
            <th scope="col" className="pb-2 font-normal">Pemasok</th>
            <th scope="col" className="pb-2 font-normal">Buah mentah</th>
            <th scope="col" className="pb-2 text-right font-normal">%</th>
            <th scope="col" className="pb-2 text-right font-normal">Restan rata-rata</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.name} className="border-t border-line">
              <th scope="row" className="py-2.5 pr-3 text-left font-normal text-ink">
                {r.name}
                <span className="block text-[11px] text-ink-soft">
                  {r.kind} · {fmtInt(r.n_muatan)} muatan
                </span>
              </th>
              <td className="w-1/2 py-2.5 pr-4">
                <div className="h-3 w-full rounded-sm bg-plane">
                  <div
                    className="h-3 rounded-r-[4px] bg-supplier"
                    style={{ width: `${((r.unripe_pct ?? 0) / max) * 100}%` }}
                  />
                </div>
              </td>
              <td className="tnum py-2.5 pr-3 text-right text-ink">
                {fmtPct(r.unripe_pct ?? 0)}
              </td>
              <td className="tnum py-2.5 text-right text-ink-soft">
                {r.queue_hours_avg.toFixed(1).replace('.', ',')} jam
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
        Peringkat ini <strong>bahan pembinaan, bukan dasar potongan</strong>.
        Komponen kematangan berakurasi 0,6346 pada muatan campuran, dan
        jumlah muatan per pemasok masih kecil — cukup untuk menunjukkan siapa
        yang perlu didampingi, belum cukup untuk menentukan siapa dibayar
        berapa.
      </p>
    </>
  )
}

/** Koreksi grader per 100 muatan.
 *
 *  Versi sebelumnya menggambar kurva menurun mulus dari M1 ke M6 dan
 *  melabelinya "bukti sistem benar-benar mempelajari pabrik ini".
 *  Angkanya karangan, endpoint-nya tidak ada, dan sistemnya belum
 *  pernah berjalan enam minggu di mana pun.
 *
 *  Sekarang datanya nyata. Konsekuensinya kartu ini akan kosong pada
 *  pemasangan baru — dan memang itu keadaan yang sebenarnya. */
export function CorrectionCurve({ data }: { data: CorrectionStats }) {
  if (!data.cukup_data) {
    return (
      <div>
        <EmptyState
          title={`Baru ${data.n_keputusan} keputusan grader tercatat`}
          hint={`Butuh minimal ${data.ambang_cukup_data} keputusan sebelum angkanya boleh dibaca sebagai tren. Setiap kali grader menekan Setuju atau Koreksi di halaman gerbang, satu baris masuk ke sini.`}
        />
        <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">{data.catatan}</p>
      </div>
    )
  }

  const max = Math.max(...data.per_minggu.map((d) => d.per_100_muatan), 1)
  const W = 320
  const H = 90
  const titik = data.per_minggu.map((d, i) => {
    const x = (i / Math.max(data.per_minggu.length - 1, 1)) * (W - 24) + 12
    const y = H - 16 - (d.per_100_muatan / max) * (H - 34)
    return `${x},${y}`
  })

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
           aria-label="Koreksi grader per 100 muatan, per minggu">
        <polyline points={titik.join(' ')} fill="none" stroke="#7d3f14" strokeWidth="2" />
        {titik.map((t, i) => {
          const [x, y] = t.split(',')
          return <circle key={i} cx={x} cy={y} r="3" fill="#7d3f14" />
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[11px] text-ink-soft">
        {data.per_minggu.map((d) => (
          <span key={d.week}>{d.week.slice(5)}</span>
        ))}
      </div>
      <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
        {fmtInt(data.n_koreksi)} koreksi dari {fmtInt(data.n_keputusan)} keputusan
        {data.rasio_koreksi !== null && ` (${(data.rasio_koreksi * 100).toFixed(1)}%)`}.
      </p>
    </div>
  )
}
