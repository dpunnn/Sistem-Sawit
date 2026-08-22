'use client'

// Layar gerbang grader: unggah foto muatan -> hasil grading.
// Alur yang ditiru: truk berhenti -> kamera memindai -> Model 1-4
// berjalan -> grader menyetujui atau mengoreksi.

import { useRef, useState } from 'react'
import Link from 'next/link'
import type { GradingResult } from '@/types'
import { gradeImage, submitDecision } from '@/lib/api'
import type { DataSource } from '@/lib/api'
import { demoGrading, demoGradingUnripe } from '@/lib/demo'
import { fmtInt, margin } from '@/lib/format'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Hero, SourceBadge, StatTile, Warn } from '@/components/ui/Bits'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { DetectionOverlay, ToggleLowConfidence } from '@/components/grading/DetectionOverlay'
import { CompositionTable } from '@/components/grading/Composition'
import { DetectionCounts } from '@/components/grading/DetectionCounts'
import { RipenessLegend } from '@/components/grading/RipenessLegend'
import { Dropzone, bukaDialogBerkas } from '@/components/grading/Dropzone'

type Status = 'idle' | 'scanning' | 'done'

/** Dua muatan contoh dari skenario demo. Ada supaya perbedaan yang
 *  paling penting bisa ditunjukkan dalam satu klik, tanpa bergantung
 *  pada berkas foto yang belum tentu ada di mesin penguji.
 *
 *  Yang harus terlihat saat berpindah: potensi minyak turun, DAN
 *  selangnya melebar. Angka yang turun itu dugaan siapa pun; selang
 *  yang ikut melebar adalah bagian yang membedakan sistem ini. */
const SCENARIOS = {
  bagus: { label: 'Muatan bagus', data: demoGrading },
  mentah: { label: 'Muatan mentah', data: demoGradingUnripe },
} as const

type ScenarioKey = keyof typeof SCENARIOS

export default function GatePage() {
  const [result, setResult] = useState<GradingResult | null>(demoGrading)
  const [source, setSource] = useState<DataSource>('demo')
  const [gagal, setGagal] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [status, setStatus] = useState<Status>('done')
  const [onlyLow, setOnlyLow] = useState(false)
  const [decision, setDecision] = useState<'agree' | 'correct' | null>(null)
  const [kirim, setKirim] = useState<string | null>(null)
  const [scenario, setScenario] = useState<ScenarioKey | null>('bagus')
  const rootRef = useRef<HTMLElement>(null)

  const memindai = status === 'scanning'

  async function onPick(file: File) {
    // Penjaga klik-dobel. Tanpa ini, layar yang tampak diam selama
    // inferensi membuat orang mengklik lagi dan mengirim request kedua.
    if (memindai) return

    setImageUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(file)
    })
    setStatus('scanning')
    setDecision(null)
    setKirim(null)
    setScenario(null)
    const { data, source, error } = await gradeImage(file)
    setResult(data)
    setSource(source)
    setGagal(error ?? null)
    setStatus('done')
  }

  function pickScenario(key: ScenarioKey) {
    if (memindai) return
    setImageUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
    setResult(SCENARIOS[key].data)
    setSource('demo')
    setGagal(null)
    setScenario(key)
    setDecision(null)
    setKirim(null)
    setStatus('done')
  }

  async function putuskan(pilihan: 'agree' | 'correct') {
    if (!result) return
    setDecision(pilihan)
    setKirim(null)
    const r = await submitDecision(result.batch_id ?? 0, { decision: pilihan })
    setKirim(
      r.ok
        ? pilihan === 'agree'
          ? 'Tersimpan. Sertifikat sortasi diterbitkan dan muatan di-tag ke batch.'
          : 'Koreksi tersimpan sebagai data latih untuk kalibrasi ulang mingguan.'
        : `Belum tersimpan — ${r.error}. Keputusan ini baru tercatat di layar.`,
    )
  }

  const oil = result?.potential_oil_kg
  const kelasTerlihat = result
    ? Array.from(new Set(result.detections.map((d) => d.ripeness)))
    : []

  return (
    <main ref={rootRef} className="mx-auto max-w-6xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight text-ink">
            Gerbang PKS
          </h1>
          <p className="mt-1 text-[14px] text-ink-soft">
            Lapis 1 — Persepsi. &ldquo;Apa yang masuk?&rdquo;
          </p>
        </div>
        <SourceBadge source={source} />
      </div>

      {gagal && (
        <div className="mt-5">
          <ErrorState message={gagal} onRetry={() => bukaDialogBerkas(rootRef.current)} />
        </div>
      )}

      <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        {/* ---- Kiri: bukti visual ---- */}
        <Card>
          <CardHeader
            title="Pindaian muatan"
            subtitle="Kotak menandai tiap tandan. Garis putus-putus = keyakinan rendah."
            aside={
              result ? (
                <ToggleLowConfidence
                  value={onlyLow}
                  onChange={setOnlyLow}
                  count={result.low_confidence_count}
                />
              ) : null
            }
          />
          <CardBody>
            <Dropzone onPick={onPick} disabled={memindai}>
              {result ? (
                <div className={memindai ? 'opacity-60 transition' : 'transition'}>
                  <DetectionOverlay
                    detections={result.detections}
                    imageUrl={imageUrl}
                    onlyLowConfidence={onlyLow}
                  />
                </div>
              ) : (
                <EmptyState
                  title="Belum ada muatan yang dipindai"
                  hint="Seret foto muatan ke area ini, atau pilih berkas lewat tombol di bawah. Sistem tidak menebak sebelum ada yang dilihat."
                />
              )}
            </Dropzone>

            {memindai && (
              <div
                role="status"
                aria-live="polite"
                className="mt-3 flex items-center gap-2 text-[13px] text-ink-soft"
              >
                <span
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-mill"
                  aria-hidden
                />
                Model sedang berjalan — mohon tunggu, jangan mengunggah ulang.
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="primary"
                disabled={memindai}
                onClick={() => bukaDialogBerkas(rootRef.current)}
              >
                {memindai ? 'Memindai…' : 'Unggah foto muatan'}
              </Button>
              <Button disabled={memindai} onClick={() => bukaDialogBerkas(rootRef.current)}>
                Pindai ulang
              </Button>
            </div>
            <p className="mt-2 text-[12px] text-ink-soft">
              Bisa juga dengan menyeret berkas ke area gambar. JPG, PNG, atau WebP,
              maksimum 12 MB.
            </p>

            <div className="mt-4 border-t border-line pt-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[12px] text-ink-soft">Muatan contoh:</span>
                {(Object.keys(SCENARIOS) as ScenarioKey[]).map((key) => (
                  <Button
                    key={key}
                    variant={scenario === key ? 'primary' : 'secondary'}
                    className="min-h-[32px] px-3 text-[13px]"
                    aria-pressed={scenario === key}
                    disabled={memindai}
                    onClick={() => pickScenario(key)}
                  >
                    {SCENARIOS[key].label}
                  </Button>
                ))}
              </div>
              <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">
                Bandingkan keduanya: potensi minyak turun, dan selangnya ikut melebar.
                Muatan yang komposisinya timpang memang lebih sulit ditaksir dari
                lapisan permukaan — sistem mengakuinya, bukan menutupinya.
              </p>
            </div>

            {result && (
              <div className="mt-4 border-t border-line pt-3">
                <p className="mb-2 text-[12px] text-ink-soft">
                  Arti warna kotak pada gambar:
                </p>
                <RipenessLegend only={kelasTerlihat} />
                <p className="mt-3 text-[12px] text-ink-soft">
                  Model {result.model_version} · {result.detections.length} tandan
                  terdeteksi
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        {/* ---- Kanan: vonis + tindakan ---- */}
        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader
              title="Potensi minyak muatan ini"
              subtitle="Keluaran Model 4 — regresi kilogram, bukan label kelas."
            />
            <CardBody>
              {oil && result ? (
                <>
                  <Hero
                    label="Potensi minyak"
                    value={
                      <>
                        {fmtInt(oil.value)}
                        <span className="ml-2 text-[22px] font-normal text-ink-soft">kg</span>
                      </>
                    }
                    note={
                      <>
                        Selang keyakinan {fmtInt(oil.lo)}–{fmtInt(oil.hi)} kg
                        <span className="text-ink-muted"> (± {fmtInt(margin(oil))} kg)</span>
                      </>
                    }
                  />

                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <StatTile
                      label="Tandan terdeteksi"
                      value={fmtInt(result.detections.length)}
                    />
                    <StatTile
                      label="Perlu diperiksa"
                      value={fmtInt(result.low_confidence_count)}
                      note="Sistem menunjuk, bukan menyuruh periksa semua"
                    />
                  </div>

                  {result.low_confidence_count > 0 && (
                    <p className="mt-4 text-[13px] leading-relaxed text-ink-soft">
                      <Warn>
                        {result.low_confidence_count} tandan berkeyakinan rendah. Sistem
                        menurunkan keyakinannya dan meminta pemeriksaan, bukan menebak
                        diam-diam.
                      </Warn>
                    </p>
                  )}
                </>
              ) : (
                <EmptyState
                  title="Belum ada angka untuk ditampilkan"
                  hint="Potensi minyak baru bisa dihitung setelah ada muatan yang dipindai."
                />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Keputusan grader" />
            <CardBody>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={decision === 'agree' ? 'primary' : 'secondary'}
                  disabled={memindai || !result}
                  onClick={() => putuskan('agree')}
                >
                  Setuju
                </Button>
                <Button
                  variant={decision === 'correct' ? 'primary' : 'secondary'}
                  disabled={memindai || !result}
                  onClick={() => putuskan('correct')}
                >
                  Koreksi
                </Button>
                <Button
                  variant="ghost"
                  disabled={memindai}
                  onClick={() => bukaDialogBerkas(rootRef.current)}
                >
                  Pindai ulang
                </Button>
              </div>

              {kirim && (
                <p className="mt-3 text-[13px] leading-relaxed text-ink-soft">{kirim}</p>
              )}

              {result && (
                <Link
                  href={`/batch/${result.batch_id ?? 4821}`}
                  className="mt-4 inline-block text-[13px] font-medium text-mill underline underline-offset-4"
                >
                  Lihat sertifikat sortasi muatan ini →
                </Link>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      {/* ---- Hitungan Model 1 berdampingan dengan taksiran Model 2 ---- */}
      {result && (
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Hitungan tandan yang terlihat"
              subtitle="Keluaran Model 1 — apa yang benar-benar tertangkap kamera di lapisan permukaan."
            />
            <CardBody>
              <DetectionCounts detections={result.detections} />
              <p className="mt-4 text-[12px] leading-relaxed text-ink-soft">
                Ini bukan komposisi muatan. Ini hanya lapisan yang terlihat, dan lapisan
                itu bisa ditata. Bandingkan dengan kartu di sebelahnya: selisih keduanya
                adalah seberapa jauh permukaan menipu.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Komposisi seluruh muatan"
              subtitle="Model 2 menaksir SELURUH muatan dari lapisan yang terlihat — karena itu hasilnya selang, bukan angka telanjang."
            />
            <CardBody>
              <CompositionTable items={result.composition} />
              <p className="mt-4 text-[12px] leading-relaxed text-ink-soft">
                Kamera hanya melihat lapisan atas. Selang di tiap baris adalah ukuran
                seberapa jauh permukaan bisa menipu — melebar pada kelas yang paling
                sering tertukar.
              </p>
            </CardBody>
          </Card>
        </div>
      )}
    </main>
  )
}
