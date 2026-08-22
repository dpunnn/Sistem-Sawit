import type { LossCause } from '@/types'
import { SIDE_FILL, SIDE_LABEL, fmtPoint, margin } from '@/lib/format'
import { ConfidenceChip } from '@/components/ui/Estimate'
import { Swatch, Warn } from '@/components/ui/Bits'

/** "TERURAI MENJADI" — bentuk yang diminta nyawit.txt bagian 8.3.
 *
 *  Perbedaannya dengan tabel kehilangan per stasiun bukan kosmetik.
 *  Tabel stasiun menjawab "berapa yang hilang di mana" — pabrik sudah
 *  tahu itu, mereka mengukurnya tiap hari. Kartu ini menjawab
 *  "SIAPA atau KEPUTUSAN APA yang bisa mengubahnya besok pagi".
 *
 *  Karena itu kolom kanan berisi pemilik masalah, bukan nama alat.
 *  "cst underflow 0,21 poin" tidak bisa ditindaklanjuti siapa pun;
 *  "Stasiun klarifikasi → suhu & waktu pengendapan" bisa.
 *
 *  Pengelompokannya sendiri bukan karangan: bentuknya persis pola yang
 *  ditemukan sendiri Model 6 dari riwayat giling, kosinus 0,93–0,9995
 *  terhadap tanda tangan gangguan yang ditanam. */
export function CausesTable({ causes }: { causes: LossCause[] }) {
  const maks = Math.max(...causes.map((c) => Math.abs(c.points.value)), 0.01)

  return (
    <div>
      <ul className="space-y-3">
        {causes.map((c) => {
          const negatif = c.points.value < 0
          return (
            <li key={c.cause} className="border-t border-line pt-3 first:border-0 first:pt-0">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="flex items-center gap-2 text-[14px] text-ink">
                  <Swatch
                    fill={SIDE_FILL[c.side]}
                    hatched={c.side === 'unknown'}
                  />
                  <strong className="font-medium">{c.cause}</strong>
                  <span className="text-[12px] text-ink-muted">
                    → {c.owner ?? SIDE_LABEL[c.side]}
                  </span>
                </span>
                <span className="tnum whitespace-nowrap text-[14px] text-ink">
                  {fmtPoint(c.points.value)}
                  <span className="text-ink-soft">
                    {' '}
                    ± {fmtPoint(margin(c.points))} poin
                  </span>
                </span>
              </div>

              {/* Batang memakai NILAI MUTLAK supaya sisa bertanda negatif
                  tetap terlihat panjangnya; tandanya sudah dibaca dari
                  angkanya, dan bar negatif hanya membingungkan. */}
              <div className="mt-1.5 h-2 w-full rounded-sm bg-plane">
                <div
                  className="h-2 rounded-r-[3px]"
                  style={{
                    width: `${(Math.abs(c.points.value) / maks) * 100}%`,
                    background: SIDE_FILL[c.side],
                    opacity: negatif ? 0.45 : 1,
                  }}
                />
              </div>

              <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                <ConfidenceChip level={c.confidence} showAction />
                {c.may_deduct_payment && (
                  <span className="text-[12px] text-ink-soft">
                    Boleh jadi dasar potongan
                  </span>
                )}
                {c.counted_in_balance === false && (
                  <span className="text-[12px] text-mill">
                    Tidak dibebankan di neraca
                  </span>
                )}
              </div>

              {c.detail && (
                <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
                  {c.detail}
                </p>
              )}
              {c.action && (
                <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
                  <strong className="font-medium text-ink">Tindakan:</strong>{' '}
                  {c.action}
                </p>
              )}
              {c.streams.length > 0 && (
                <p className="mt-1 text-[12px] text-ink-muted">
                  Dari{' '}
                  {c.streams
                    .map((s) => `${s.name} ${fmtPoint(s.points)}`)
                    .join(' · ')}
                </p>
              )}
              {negatif && (
                <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
                  <Warn>
                    Bertanda negatif: pabrik menghasilkan lebih banyak daripada
                    yang bisa dijelaskan neraca. Itu tanda koefisien terlalu
                    berhati-hati, bukan dasar untuk menuntut siapa pun.
                  </Warn>
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
