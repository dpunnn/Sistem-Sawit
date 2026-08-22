// Halaman neraca harian -- KLIMAKS produk.
//
// force-dynamic: neraca dihitung ulang dari basis data tiap permintaan.
// Tanpa ini, halaman bisa disajikan dari cache dan terlihat beku persis
// saat orang baru selesai memindai muatan -- kesan paling buruk yang
// bisa diberikan sistem yang justru berjanji menghitung ulang.
export const dynamic = 'force-dynamic'
export const revalidate = 0

// "2,2 poin hilang. Ini rinciannya. Ini yang bisa diperbaiki."

import { fetchBalance, fetchBatch, fetchCorrections, fetchSuppliers } from '@/lib/api'
import { SIDE_FILL, fmtIDR, fmtPoint } from '@/lib/format'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Hero, Legend, SourceBadge, StatTile } from '@/components/ui/Bits'
import { ActionThresholds } from '@/components/ui/ActionThresholds'
import { Waterfall } from '@/components/neraca/Waterfall'
import { AttributionTable, BalanceRows } from '@/components/neraca/BalanceRows'
import { StationLosses } from '@/components/neraca/StationLosses'
import { UncertaintyChain } from '@/components/neraca/UncertaintyChain'
import { CorrectionCurve, SupplierRanking } from '@/components/neraca/Suppliers'
import { EmptyState, ErrorState } from '@/components/ui/States'

export default async function NeracaPage() {
  const { data: balance, source, error } = await fetchBalance()

  // Tanpa neraca tidak ada yang bisa ditampilkan. Halaman ini BERHENTI
  // di sini alih-alih menggambar kartu berisi angka contoh — kartu
  // neraca palsu jauh lebih berbahaya daripada layar yang mengaku
  // gagal, karena semua isinya terlihat seperti hasil pengukuran.
  if (!balance) {
    return (
      <main className="mx-auto max-w-3xl px-5 py-16">
        <h1 className="text-[26px] font-semibold tracking-tight text-ink">
          Neraca Minyak Harian
        </h1>
        <div className="mt-6">
          <ErrorState message={error ?? 'Backend tidak menjawab.'} />
        </div>
        <p className="mt-4 text-[13px] leading-relaxed text-ink-soft">
          Tidak ada angka yang ditampilkan di sini selama neraca belum bisa
          dihitung. Jalankan <code>docker compose up</code>, lalu isi data shift
          dengan <code>python scripts/seed_shift.py</code>.
        </p>
      </main>
    )
  }

  // Rantai perambatan membentang dari Lapis 1 ke Lapis 2, jadi halaman ini
  // butuh satu muatan sebagai wakil hulunya. Sumbernya digabung ke yang
  // paling lemah -- kalau salah satu masih data contoh, kartunya mengaku
  // data contoh.
  const { data: grading, source: gradingSource } = await fetchBatch(1)

  // Dua kartu ini dulunya memakai angka yang ditulis tangan di
  // lib/demo.ts. Datanya sebenarnya sudah ada di basis data — tinggal
  // ditanyakan. Angka karangan di layar yang dilihat juri bukan sekadar
  // tidak rapi; ia klaim yang tidak dimiliki sistem.
  const { data: pemasok, source: pemasokSource } = await fetchSuppliers()
  const { data: koreksi } = await fetchCorrections()
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
          <p className="mt-1 text-[12px] text-ink-muted">
            Dihitung ulang dari {balance.n_muatan} muatan yang sudah dinilai
            {balance.computed_at &&
              ` · ${new Date(balance.computed_at).toLocaleTimeString('id-ID', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}`}
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
      {/* Kolom kiri memakai lebar `auto`, jadi apa pun yang panjang di
       *  dalam Hero akan MENGHIMPIT tiga kartu di kanan sampai teksnya
       *  saling menumpuk. Penjelasan panjang karena itu diletakkan di
       *  bawah grid, selebar kartu — bukan di dalam kolomnya. */}
      <Card className="mt-6">
        <CardBody>
          <div className="grid gap-6 md:grid-cols-[auto_1fr] md:items-center">
            <Hero
              label="Kehilangan hari ini"
              value={
                <>
                  {fmtPoint(balance.total_loss_points)}
                  <span className="ml-2 text-[22px] font-normal text-ink-soft">
                    poin
                  </span>
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
          </div>

          <p className="mt-5 border-t border-line pt-4 text-[12px] leading-relaxed text-ink-soft">
            Angka <strong>{fmtPoint(balance.total_loss_points)} poin</strong> tetap
            sepanjang shift: potensi teoretis datang dari koefisien terbit dan
            rendemen aktual dari jembatan timbang — keduanya bukan keluaran model.
            Yang bergerak setiap kali muatan dipindai adalah{' '}
            <strong>pembagiannya</strong> antara sisi pemasok, sisi pabrik, dan
            bagian yang tidak diatribusikan ke siapa pun.
          </p>
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
              aside={<SourceBadge source={pemasokSource} />}
            />
            <CardBody>
              <SupplierRanking rows={pemasok ?? []} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Koreksi grader per 100 muatan"
              subtitle="Seberapa sering grader membantah model. Turun dari minggu ke minggu berarti model makin cocok dengan pabrik ini."
            />
            <CardBody>
              {koreksi ? (
                <CorrectionCurve data={koreksi} />
              ) : (
                <EmptyState title="Statistik koreksi belum bisa diambil" />
              )}
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
          {grading ? (
            <UncertaintyChain grading={grading} balance={balance} />
          ) : (
            <EmptyState
              title="Rantai ketidakpastian belum bisa digambar"
              hint="Butuh satu hasil grading tersimpan sebagai wakil hulunya."
            />
          )}

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
