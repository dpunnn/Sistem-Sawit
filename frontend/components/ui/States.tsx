import { Warn } from '@/components/ui/Bits'

/** Layar gagal yang MENGAKU gagal.
 *
 *  Sebelumnya setiap kegagalan jaringan diam-diam berubah jadi data
 *  contoh, sehingga backend mati dan backend sehat terlihat sama persis.
 *  Saat demo, itu berarti tidak ada yang tahu sistemnya sedang tidak
 *  terhubung sampai ada yang bertanya. */
export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-dashed border-mill bg-mill-soft px-4 py-3"
    >
      <p className="text-[13px] leading-relaxed text-ink">
        <Warn>Gagal mengambil data dari backend.</Warn>
      </p>
      <p className="tnum mt-1.5 text-[12px] leading-relaxed text-ink-soft">{message}</p>
      <p className="mt-1.5 text-[12px] leading-relaxed text-ink-soft">
        Yang tampil di bawah ini data contoh, bukan hasil model.
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2.5 text-[13px] font-medium text-mill underline underline-offset-4"
        >
          Coba lagi
        </button>
      )}
    </div>
  )
}

/** Belum ada apa-apa -- dan itu bukan kerusakan.
 *
 *  Layar kosong tanpa penjelasan membuat orang mengira sistem rusak.
 *  Bedanya dengan ErrorState: di sini tidak ada yang salah, hanya belum
 *  ada masukan. */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string
  hint?: string
  action?: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-plane px-4 py-8 text-center">
      <p className="text-[14px] font-medium text-ink">{title}</p>
      {hint && (
        <p className="mx-auto mt-1.5 max-w-sm text-[12px] leading-relaxed text-ink-soft">
          {hint}
        </p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

/** Penanda untuk bagian layar yang datanya BELUM punya jalur ke backend.
 *
 *  Berbeda dari SourceBadge: badge itu menandai data yang endpoint-nya
 *  ada tapi sedang gagal dihubungi. Penanda ini untuk yang memang belum
 *  ada endpoint-nya sama sekali, sehingga tidak akan pernah berubah jadi
 *  'live' tanpa pekerjaan tambahan. Membedakan keduanya penting supaya
 *  tidak ada yang mengira grafik ini akan hidup sendiri nanti. */
export function DemoOnly({ note }: { note?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-ink-muted bg-plane px-2.5 py-1 text-[11px] text-ink-soft"
      title={note ?? 'Belum ada endpoint backend untuk data ini'}
    >
      <span className="hatch-unknown h-1.5 w-1.5 rounded-full" aria-hidden />
      Angka karangan
    </span>
  )
}

/** Fitur yang direncanakan tapi belum dibangun sama sekali. */
export function Planned() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-ink-muted bg-plane px-2.5 py-1 text-[11px] text-ink-soft">
      Belum dibangun
    </span>
  )
}
