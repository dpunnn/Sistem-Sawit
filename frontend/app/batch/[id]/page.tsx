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
import { CompositionTable } from '@/components/grading/Composition'

export default async function BatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const { data: batch, source } = await fetchBatch(id)

  const oil = batch.potential_oil_kg
  const unripe = batch.composition.find((c) => c.ripeness === 'unripe')
  const scanned = new Date(batch.processed_at).toLocaleString('id-ID', {
    dateStyle: 'long',
    timeStyle: 'short',
  })

  // Dasar potongan, ditulis terbuka: koefisien terbit -0,13 poin OER
  // per 1% buah mentah.
  const OER_PER_UNRIPE_PCT = 0.13
  const unripePct = unripe?.percent.value ?? 0
  const oerPenalty = unripePct * OER_PER_UNRIPE_PCT

  return (
    <main className="mx-auto max-w-4xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight text-ink">
            Sertifikat Sortasi
          </h1>
          <p className="mt-1 text-[14px] text-ink-soft">
            Muatan #{batch.batch_id ?? id} · KUD Jaya Makmur · {scanned}
          </p>
        </div>
        <SourceBadge source={source} />
      </div>

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
                <strong className="tnum">0,13</strong> poin
              </span>
            </li>
            <li className="flex gap-3">
              <Step n={3} />
              <span>
                Dampak rendemen ={' '}
                <span className="tnum">
                  {fmtPct(unripePct)} × 0,13 = <strong>{fmtPoint(oerPenalty)} poin</strong>
                </span>
              </span>
            </li>
          </ol>

          <p className="mt-4 rounded-lg border border-line bg-plane px-4 py-3 text-[13px] leading-relaxed text-ink-soft">
            <Warn>
              Potongan ini boleh dibantah. Bila Anda tidak setuju, selang keyakinan di
              atas adalah dasar diskusinya — sistem menyajikan bukti, bukan keputusan
              final.
            </Warn>
          </p>
        </CardBody>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Rekomendasi"
          subtitle="Model 8 — status tahap lanjutan, disebut jujur sebagai simulasi."
        />
        <CardBody>
          <p className="text-[13px] leading-relaxed text-ink">
            Buah mentah Anda naik tiga minggu berturut-turut. Interval panen kemungkinan
            terlalu rapat. Rekomendasi: perpanjang dari 7 ke 10 hari.
          </p>
          <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
            Tujuan layar ini mengubah interaksi dari menghukum menjadi membantu —
            rendemen yang naik menguntungkan kedua pihak.
          </p>
        </CardBody>
      </Card>

      <Card className="mt-5">
        <CardHeader title="Foto bukti" subtitle="Arsip muatan saat ditimbang." />
        <CardBody>
          <div className="flex flex-wrap gap-2">
            {RIPENESS_ORDER.slice(0, 5).map((r) => (
              <span
                key={r}
                className="inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[12px] text-ink-soft"
              >
                <Swatch fill={RIPENESS_FILL[r]} />
                {RIPENESS_LABEL[r]}
              </span>
            ))}
          </div>
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
