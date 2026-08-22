// Sertifikat sortasi digital untuk petani/pemasok.
//
// Ini layar yang menjawab keluhan yang terdokumentasi: "pengukuran
// rendemen tidak pernah dilakukan terbuka". Karena itu setiap angka di
// sini harus bisa dihitung ulang oleh yang membacanya -- dasar potongan
// ditulis sebagai aritmetika, bukan sebagai vonis.

import Link from 'next/link'
import { fetchBatch } from '@/lib/api'
import {
  RIPENESS_FILL,
  RIPENESS_LABEL,
  RIPENESS_ORDER,
  fmtInt,
  fmtPct,
  fmtPoint,
  margin,
} from '@/lib/format'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Swatch, SourceBadge, StatTile, Warn } from '@/components/ui/Bits'
import { ErrorState, Planned } from '@/components/ui/States'
import { RipenessLegend } from '@/components/grading/RipenessLegend'
import { CompositionTable } from '@/components/grading/Composition'

export default async function BatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const { data: batch, source, error } = await fetchBatch(id)

  const oil = batch.potential_oil_kg
  const unripe = batch.composition.find((c) => c.ripeness === 'unripe')
  const scanned = new Date(batch.processed_at).toLocaleString('id-ID', {
    dateStyle: 'long',
    timeStyle: 'short',
  })

  // Dasar potongan datang UTUH dari backend, termasuk koefisien dan
  // sitasinya.
  //
  // Sebelumnya angka 0,13 disalin ke berkas ini dan bahkan dicetak
  // sebagai teks. Artinya kalau koefisiennya berubah — atau statusnya
  // turun jadi belum terverifikasi — layar tetap memamerkan angka lama
  // sambil terlihat sangat meyakinkan, dan yang dirugikan petani yang
  // membaca sertifikatnya.
  const dasar = batch.deduction_basis
  const unripePct = dasar?.unripe_pct ?? unripe?.percent.value ?? 0

  return (
    <main className="mx-auto max-w-4xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight text-ink">
            Sertifikat Sortasi
          </h1>
          <p className="mt-1 text-[14px] text-ink-soft">
            Muatan #{batch.batch_id ?? id}
            {batch.supplier && ` · ${batch.supplier.name}`}
            {batch.supplier && ` · ${batch.supplier.truck_plate}`} · {scanned}
          </p>
        </div>
        <SourceBadge source={source} />
      </div>

      {error && (
        <div className="mt-5">
          <ErrorState message={error} />
        </div>
      )}

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <StatTile
          label="Potensi minyak muatan"
          value={`${fmtInt(oil.value)} kg`}
          note={`± ${fmtInt(margin(oil))} kg`}
        />
        <StatTile label="Buah mentah" value={fmtPct(unripePct)} note="Dasar potongan" />
        <StatTile
          label="Tandan diperiksa ulang"
          value={fmtInt(batch.low_confidence_count)}
          note="Oleh grader, bukan oleh mesin"
        />
      </div>

      <Card className="mt-5">
        <CardHeader
          title="Rincian per kategori"
          subtitle="Setiap kategori disertai selang keyakinan. Angka tanpa selang tidak pernah diterbitkan."
        />
        <CardBody>
          <CompositionTable items={batch.composition} />
        </CardBody>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Dasar potongan — bisa dihitung ulang"
          subtitle="Koefisien terbit, bukan angka internal pabrik."
        />
        <CardBody>
          <ol className="space-y-3 text-[13px] leading-relaxed text-ink">
            <li className="flex gap-3">
              <Step n={1} />
              <span>
                Buah mentah pada muatan ini{' '}
                <strong className="tnum">{fmtPct(unripePct)}</strong>
                <span className="text-ink-soft">
                  {' '}
                  (selang {fmtPct(unripe?.percent.lo ?? 0)}–{fmtPct(unripe?.percent.hi ?? 0)})
                </span>
              </span>
            </li>
            <li className="flex gap-3">
              <Step n={2} />
              <span>
                Koefisien terbit: setiap 1% buah mentah menurunkan rendemen{' '}
                <strong className="tnum">
                  {dasar ? fmtPoint(dasar.coefficient_per_pct) : '—'}
                </strong>{' '}
                poin
                {dasar && (
                  <span className="text-ink-soft">
                    {' '}
                    — status {dasar.coefficient_status}
                  </span>
                )}
                {dasar?.citation?.judul && (
                  <span className="mt-1 block text-[12px] leading-relaxed text-ink-soft">
                    Sumber:{' '}
                    {dasar.citation.url ? (
                      <a
                        href={dasar.citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-mill underline underline-offset-2"
                      >
                        {dasar.citation.judul}
                      </a>
                    ) : (
                      dasar.citation.judul
                    )}
                    {dasar.citation.penerbit && ` · ${dasar.citation.penerbit}`}
                  </span>
                )}
              </span>
            </li>
            <li className="flex gap-3">
              <Step n={3} />
              <span>
                Dampak rendemen ={' '}
                <span className="tnum">
                  {dasar ? dasar.formula : '—'}
                </span>
              </span>
            </li>
          </ol>

          {dasar?.coefficient_status !== 'terverifikasi' && dasar && (
            <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
              <Warn>
                Koefisien ini berstatus <strong>{dasar.coefficient_status}</strong>.
                Selama belum tertelusur ke sumber terbit, angka di atas bahan
                diskusi — bukan dasar potongan.
              </Warn>
            </p>
          )}

          <p className="mt-4 rounded-lg border border-line bg-plane px-4 py-3 text-[13px] leading-relaxed text-ink-soft">
            <Warn>
              Potongan ini boleh dibantah. Bila Anda tidak setuju, selang keyakinan di
              atas adalah dasar diskusinya — sistem menyajikan bukti, bukan keputusan
              final.
            </Warn>
          </p>
        </CardBody>
      </Card>

      {/* Rencana lanjutan, BUKAN keluaran model.
       *
       *  Sebelumnya kartu ini berlabel "Model 8". Sistem ini hanya punya
       *  Model 1-6; tidak ada Model 7 maupun 8 di ai/, di README, maupun
       *  di pipeline. Menyebut nomor model yang tidak ada membuat seluruh
       *  penomoran lain ikut diragukan -- persis kredibilitas yang jadi
       *  satu-satunya modal sistem forensik. */}
      <Card className="mt-5">
        <CardHeader
          title="Rekomendasi agronomi"
          subtitle="Rencana lanjutan — belum dibangun. Teks di bawah contoh bentuk keluaran, bukan hasil model."
          aside={<Planned />}
        />
        <CardBody>
          <p className="text-[13px] leading-relaxed text-ink-soft">
            &ldquo;Buah mentah Anda naik tiga minggu berturut-turut. Interval panen
            kemungkinan terlalu rapat. Rekomendasi: perpanjang dari 7 ke 10
            hari.&rdquo;
          </p>
          <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
            Arah yang dituju: mengubah interaksi dari menghukum menjadi membantu.
            Untuk sampai ke sana dibutuhkan riwayat panen per pemasok yang saat ini
            belum dikumpulkan, jadi kartu ini sengaja dibiarkan kosong isinya
            daripada diisi tebakan yang terlihat meyakinkan.
          </p>
        </CardBody>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Legenda kelas & jejak audit"
          subtitle="Warna yang dipakai di seluruh sistem, beserta arsip muatan saat ditimbang."
        />
        <CardBody>
          <RipenessLegend />
          <p className="mt-3 text-[12px] text-ink-soft">
            Foto asli muatan tersimpan sebagai jejak audit dan dapat dibuka kembali bila
            ada sengketa.
          </p>
        </CardBody>
      </Card>

      <Link
        href="/neraca"
        className="mt-6 inline-block text-[13px] font-medium text-mill underline underline-offset-4"
      >
        Lihat neraca minyak harian →
      </Link>
    </main>
  )
}

function Step({ n }: { n: number }) {
  return (
    <span
      className="tnum grid h-5 w-5 shrink-0 place-items-center rounded-full bg-mill text-[11px] font-semibold text-white"
      aria-hidden
    >
      {n}
    </span>
  )
}
