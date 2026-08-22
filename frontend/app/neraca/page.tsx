// Halaman neraca harian -- KLIMAKS produk.
// "2,2 poin hilang. Ini rinciannya. Ini yang bisa diperbaiki."

import { fetchBalance, fetchBatch } from '@/lib/api'
import { demoCorrectionCurve, demoSuppliers } from '@/lib/demo'
import { SIDE_FILL, fmtIDR, fmtPoint } from '@/lib/format'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Hero, Legend, SourceBadge, StatTile } from '@/components/ui/Bits'
import { ActionThresholds } from '@/components/ui/ActionThresholds'
import { Waterfall } from '@/components/neraca/Waterfall'
import { AttributionTable, BalanceRows } from '@/components/neraca/BalanceRows'
import { StationLosses } from '@/components/neraca/StationLosses'
import { UncertaintyChain } from '@/components/neraca/UncertaintyChain'
import { CorrectionCurve, SupplierRanking } from '@/components/neraca/Suppliers'
import { DemoOnly, ErrorState } from '@/components/ui/States'

export default async function NeracaPage() {
  const { data: balance, source, error } = await fetchBalance()

  // Rantai perambatan membentang dari Lapis 1 ke Lapis 2, jadi halaman ini
  // butuh satu muatan sebagai wakil hulunya. Sumbernya digabung ke yang
  // paling lemah -- kalau salah satu masih data contoh, kartunya mengaku
  // data contoh.
  const { data: grading, source: gradingSource } = await fetchBatch('4821')
  const chainSource = source === 'live' && gradingSource === 'live' ? 'live' : 'demo'

  const supplierPoints = balance.supplier_losses.reduce((a, l) => a + l.points.value, 0)
  const millPoints = balance.mill_losses.reduce((a, l) => a + l.points.value, 0)

  const shift = new Date(balance.shift_date).toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight text-ink">
            Neraca Minyak Harian
          </h1>
          <p className="mt-1 text-[14px] text-ink-soft">
            Lapis 2 — Penalaran. &ldquo;Ke mana perginya?&rdquo; · {shift}
          </p>
        </div>
        <SourceBadge source={source} />
      </div>

      {error && (
        <div className="mt-5">
          <ErrorState message={error} />
        </div>
      )}

      {/* ---- Angka pahlawan + ringkasan dua arah ---- */}
      <Card className="mt-6">
        <CardBody className="grid gap-6 md:grid-cols-[auto_1fr] md:items-center">
          <Hero
            label="Kehilangan hari ini"
            value={
              <>
                {fmtPoint(balance.total_loss_points)}
                <span className="ml-2 text-[22px] font-normal text-ink-soft">poin</span>
              </>
            }
            note={
              <>
                Potensi {fmtPoint(balance.potential_theoretical)}% → aktual{' '}
                {fmtPoint(balance.actual_oer)}%
              </>
            }
          />

          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile
              label="Sisi pemasok"
              value={`${fmtPoint(supplierPoints)} poin`}
              note="Mutu buah yang masuk"
            />
            <StatTile
              label="Sisi pabrik"
              value={`${fmtPoint(millPoints)} poin`}
              note="Perebusan, kempa, klarifikasi"
            />
            <StatTile
              label="Nilai kehilangan"
              value={fmtIDR(balance.loss_value_idr)}
              note="Shift ini"
            />
          </div>
        </CardBody>
      </Card>

      {/* ---- Waterfall + kembaran tabelnya ---- */}
      <Card className="mt-5">
        <CardHeader
          title={`Ke mana ${fmtPoint(balance.total_loss_points)} poin itu pergi`}
          subtitle="Setiap batang adalah satu penyebab, dengan pita selang keyakinannya. Garis putus & arsiran menandai sisa yang sistem menolak untuk dijelaskan."
          aside={
            <Legend
              items={[
                { label: 'Sisi pemasok', fill: SIDE_FILL.supplier },
                { label: 'Sisi pabrik', fill: SIDE_FILL.mill },
                { label: 'Tidak terjelaskan', fill: SIDE_FILL.unknown, hatched: true },
              ]}
            />
          }
        />
        <CardBody>
          <Waterfall balance={balance} />

          <details className="mt-5 border-t border-line pt-4">
            <summary className="cursor-pointer text-[13px] font-medium text-ink">
              Lihat sebagai tabel
            </summary>
            <div className="mt-3">
              <AttributionTable balance={balance} />
            </div>
          </details>
        </CardBody>
      </Card>

      {/* ---- Kartu tiga baris ---- */}
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_1fr]">
        <Card>
          <CardHeader
            title="Kartu neraca"
            subtitle="Masuk = keluar + loss + sisa. Bagian ini sebagian besar deterministik — siapa pun bisa mengauditnya."
          />
          <CardBody>
            <BalanceRows balance={balance} />
          </CardBody>
        </Card>

        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader
              title="Peringkat pemasok"
              subtitle="Persen buah mentah minggu ini, per pemasok."
              aside={<DemoOnly note="Belum ada endpoint /api/suppliers" />}
            />
            <CardBody>
              <SupplierRanking rows={demoSuppliers} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Koreksi grader per 100 muatan"
              subtitle="Bentuk laporan yang dituju: koreksi menurun berarti model makin cocok dengan pabrik ini."
              aside={<DemoOnly note="Belum ada endpoint, dan sistem belum pernah berjalan enam minggu" />}
            />
            <CardBody>
              <CorrectionCurve data={demoCorrectionCurve} />
            </CardBody>
          </Card>
        </div>
      </div>

      {/* ---- Dasar yang bisa diaudit orang luar ---- */}
      <Card className="mt-5">
        <CardHeader
          title="Kehilangan terukur per stasiun"
          subtitle="Bagian neraca yang tidak melibatkan model sama sekali — fisika dan akuntansi, dari pekerjaan lab harian yang sudah rutin di pabrik."
        />
        <CardBody>
          <StationLosses rows={balance.station_losses} />
          <p className="mt-4 text-[12px] leading-relaxed text-ink-soft">
            Kadar minyak di atas adalah nilai kalibrasi dari studi kasus
            terpublikasi, sama persis dengan yang dipakai simulator neraca massa.
            Nisbah massanya masih taksiran teknik berstatus{' '}
            <code className="rounded bg-plane px-1 py-0.5 text-[11px] text-ink">
              perlu_verifikasi
            </code>
            . Seluruh koefisien beserta sitasi dan statusnya ada di satu berkas —{' '}
            <code className="rounded bg-plane px-1 py-0.5 text-[11px] text-ink">
              ai/config/coefficients.yaml
            </code>{' '}
            — supaya dasar ilmiah sistem bisa diperiksa tanpa membongkar bobot
            model.
          </p>
        </CardBody>
      </Card>

      {/* ---- Rantai ketidakpastian + ambang tindakan ---- */}
      <Card className="mt-5">
        <CardHeader
          title="Dari mana ketidakpastian ini menumpuk"
          subtitle="Selang di angka terakhir tidak muncul begitu saja. Ia dirambatkan dari Model 1 sampai Model 6, dan tiap tahap punya alasannya sendiri."
          aside={<SourceBadge source={chainSource} />}
        />
        <CardBody className="grid gap-6 lg:grid-cols-[1.5fr_1fr] lg:items-start">
          <UncertaintyChain grading={grading} balance={balance} />

          <div className="rounded-lg border border-line bg-plane px-4 py-3">
            <h3 className="text-[13px] font-medium text-ink">Ambang tindakan</h3>
            <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
              Angka yang sama tidak boleh memicu konsekuensi yang sama bila
              keyakinannya berbeda.
            </p>
            <div className="mt-3">
              <ActionThresholds />
            </div>
            <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
              Inilah bentuk konkret <em>learning to defer</em>: model tahu kapan
              dirinya belum cukup yakin untuk mengambil alih keputusan manusia.
            </p>
          </div>
        </CardBody>
      </Card>

      <p className="mt-6 max-w-3xl text-[13px] leading-relaxed text-ink-soft">
        Neraca yang jujur menunjuk ke dua arah. {fmtPoint(supplierPoints)} poin ada di
        sisi buah yang masuk, {fmtPoint(millPoints)} poin ada di sisi proses pabrik
        sendiri, dan {fmtPoint(balance.unexplained.points.value)} poin tidak
        diatribusikan ke siapa pun karena buktinya belum cukup.
      </p>
    </main>
  )
}
