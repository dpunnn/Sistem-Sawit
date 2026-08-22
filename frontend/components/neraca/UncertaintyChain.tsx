import type { BalanceCard, GradingResult } from '@/types'
import { RIPENESS_LABEL, SIDE_FILL, fmtInt, fmtPct, fmtPoint, margin } from '@/lib/format'
import { spread } from '@/components/ui/Estimate'

/** Rantai perambatan ketidakpastian, Model 1 sampai Model 6.
 *
 *  Alasan layar ini ada: keluaran sistem dipakai untuk menyalahkan orang
 *  dan memotong uang. Sistem yang mengaku pasti padahal tidak adalah
 *  sistem berbahaya. Jadi ketidakpastian tidak boleh cuma muncul di
 *  angka terakhir -- pembaca harus bisa melihat dari mana ia menumpuk.
 *
 *  Satu aturan yang menentukan bentuk komponen ini: BATANG HANYA
 *  DIGAMBAR untuk tahap yang benar-benar menerbitkan selang. Tahap yang
 *  ukurannya lain (Model 1 memakai keyakinan per tandan) atau yang
 *  selangnya memang belum ada (Model 5) ditulis sebagai teks. Menyamakan
 *  besaran yang tidak sebanding di satu sumbu justru bentuk lain dari
 *  ketidakjujuran yang hendak dilawan sistem ini. */
export function UncertaintyChain({
  grading,
  balance,
}: {
  grading: GradingResult
  balance: BalanceCard
}) {
  const stages = buildStages(grading, balance)
  const scale = Math.max(...stages.map((s) => s.rel ?? 0)) * 1.12 || 1

  return (
    <div>
      <ol className="divide-y divide-line">
        {stages.map((s) => (
          <li key={s.model} className="py-3.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <div className="min-w-0">
                <span className="text-[13px] font-medium text-ink">{s.model}</span>
                <span className="text-[13px] text-ink-soft"> — {s.what}</span>
              </div>
              <div className="tnum shrink-0 text-[13px] text-ink">{s.measure}</div>
            </div>

            <div className="mt-2 h-2.5 w-full rounded-sm bg-plane">
              {s.rel === undefined ? (
                // Selang belum ada di kontrak: ditandai arsiran, bukan
                // batang nol. Nol berarti "pasti" -- itu klaim yang salah.
                <div
                  className="hatch-unknown h-full w-full rounded-sm border border-dashed border-ink-muted"
                  aria-hidden
                />
              ) : (
                <div
                  className="h-full rounded-r-[3px]"
                  style={{
                    width: `${Math.max(2, (s.rel / scale) * 100)}%`,
                    background: s.fill,
                  }}
                />
              )}
            </div>

            <p className="mt-1.5 text-[12px] leading-relaxed text-ink-soft">
              {s.rel !== undefined && (
                <span className="tnum text-ink">selang ±{fmtPct(s.rel * 100)} dari nilainya · </span>
              )}
              {s.why}
            </p>
          </li>
        ))}
      </ol>

      <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
        Panjang batang adalah lebar selang relatif terhadap nilai tahap itu
        sendiri, jadi tahap yang satuannya berbeda tetap bisa dibandingkan.
        Dua tahap sengaja tidak diberi batang karena ukurannya bukan selang —
        menyamakannya di satu sumbu akan menyesatkan.
      </p>
    </div>
  )
}

type Stage = {
  model: string
  what: string
  measure: string
  /** Lebar selang relatif (fraksi). undefined = tahap ini tidak menerbitkan selang. */
  rel?: number
  why: string
  fill: string
}

function buildStages(g: GradingResult, b: BalanceCard): Stage[] {
  const total = g.detections.length
  const low = g.detections.filter((d) => d.low_confidence).length
  const meanConf =
    total === 0 ? 0 : g.detections.reduce((a, d) => a + d.confidence, 0) / total

  // Kelas dengan selang terlebar -- biasanya pasangan yang paling sering
  // tertukar, dan itu memang yang ingin ditunjukkan.
  const widestClass = [...g.composition].sort((a, b2) => spread(b2.percent) - spread(a.percent))[0]

  const attributions = [...b.supplier_losses, ...b.mill_losses, b.unexplained]
  const widestCause = [...attributions].sort((a, b2) => spread(b2.points) - spread(a.points))[0]

  return [
    {
      model: 'Model 1',
      what: 'klasifikasi ordinal per tandan',
      measure: `${fmtInt(low)}/${fmtInt(total)} di bawah ambang`,
      why: `Ukurannya keyakinan per tandan, bukan selang. Rata-rata ${fmtPct(
        meanConf * 100,
      )} — yang di bawah ambang diteruskan ke grader, bukan ditebak diam-diam.`,
      fill: SIDE_FILL.supplier,
    },
    {
      model: 'Model 2',
      what: 'komposisi seluruh muatan',
      measure: `${fmtPct(widestClass.percent.value)} ± ${fmtPoint(margin(widestClass.percent))}`,
      rel: spread(widestClass.percent),
      why: `Melebar di sini karena oklusi: kamera hanya melihat lapisan atas. Kelas paling goyah — ${RIPENESS_LABEL[
        widestClass.ripeness
      ].toLowerCase()}.`,
      fill: SIDE_FILL.supplier,
    },
    {
      model: 'Model 4',
      what: 'potensi minyak muatan',
      measure: `${fmtInt(g.potential_oil_kg.value)} ± ${fmtInt(margin(g.potential_oil_kg))} kg`,
      rel: spread(g.potential_oil_kg),
      why: 'Selang komposisi dibawa masuk ke regresi kilogram. Sebagian kesalahan antar-kelas saling meniadakan saat dijumlahkan, jadi lebar relatifnya tidak otomatis mewarisi lebar Model 2.',
      fill: SIDE_FILL.supplier,
    },
    {
      model: 'Model 5',
      what: 'selisih neraca massa',
      measure: `${fmtPoint(b.unexplained.points.value)} ± ${fmtPoint(
        margin(b.unexplained.points),
      )} poin`,
      rel: spread(b.unexplained.points),
      why: 'Ini selisih beberapa angka yang semuanya tidak pasti, jadi ragamnya menjumlah dan selangnya MELEBAR — bukan menyempit. Baris tak terjelaskan memang yang paling lebar di seluruh rantai, dan begitulah seharusnya.',
      fill: SIDE_FILL.mill,
    },
    {
      model: 'Model 6',
      what: 'atribusi per penyebab',
      measure: `${fmtPoint(widestCause.points.value)} ± ${fmtPoint(margin(widestCause.points))} poin`,
      rel: spread(widestCause.points),
      why: `Melebar karena penyebabnya saling berkorelasi — buah mentah dan sterilisasi buruk sama-sama menaikkan loss ampas kempa. Baris paling goyah: ${widestCause.cause.toLowerCase()}, dan justru itu yang tidak boleh jadi dasar potongan pembayaran.`,
      fill: widestCause.side === 'unknown' ? SIDE_FILL.unknown : SIDE_FILL.mill,
    },
  ]
}
