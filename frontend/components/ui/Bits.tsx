import type { DataSource } from '@/lib/api'
import { cn } from '@/lib/utils'

/** Kotak warna kecil yang memikul identitas seri.
 *  Teks di sebelahnya tetap memakai tinta, tidak pernah warna data. */
export function Swatch({
  fill,
  hatched = false,
  className,
}: {
  fill: string
  hatched?: boolean
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-block h-3 w-3 shrink-0 rounded-[3px]',
        hatched && 'hatch-unknown border border-dashed border-ink-muted',
        className,
      )}
      style={hatched ? undefined : { background: fill }}
      aria-hidden
    />
  )
}

export function Legend({
  items,
}: {
  items: { label: string; fill: string; hatched?: boolean }[]
}) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {items.map((it) => (
        <li key={it.label} className="flex items-center gap-1.5">
          <Swatch fill={it.fill} hatched={it.hatched} />
          <span className="text-[12px] text-ink-soft">{it.label}</span>
        </li>
      ))}
    </ul>
  )
}

/** Pengakuan jujur dari mana angka di layar ini berasal.
 *  Wajib ada selama router backend & bobot model belum terpasang. */
export function SourceBadge({ source }: { source: DataSource }) {
  if (source === 'live') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-plane px-2.5 py-1 text-[11px] text-ink-soft">
        <span className="h-1.5 w-1.5 rounded-full bg-mill" aria-hidden />
        Data langsung dari model
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-ink-muted bg-plane px-2.5 py-1 text-[11px] text-ink-soft">
      <span className="hatch-unknown h-1.5 w-1.5 rounded-full" aria-hidden />
      Data contoh — model belum terpasang
    </span>
  )
}

export function Warn({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="grid h-4 w-4 shrink-0 place-items-center rounded-full border border-mill text-[10px] font-bold leading-none text-mill"
        aria-hidden
      >
        !
      </span>
      <span>{children}</span>
    </span>
  )
}

/** Angka pahlawan: satu per tampilan, sans yang sama dengan lainnya,
 *  figur proporsional (bukan tabular -- angka besar jadi renggang). */
export function Hero({
  label,
  value,
  note,
}: {
  label: string
  value: React.ReactNode
  note?: React.ReactNode
}) {
  return (
    <div>
      <div className="text-[12px] uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="mt-1 text-[52px] font-semibold leading-none text-ink">{value}</div>
      {note && <div className="mt-2 text-[13px] text-ink-soft">{note}</div>}
    </div>
  )
}

export function StatTile({
  label,
  value,
  note,
}: {
  label: string
  value: React.ReactNode
  note?: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <div className="text-[12px] text-ink-soft">{label}</div>
      <div className="mt-1 text-[24px] font-semibold leading-tight text-ink">{value}</div>
      {note && <div className="mt-1 text-[12px] text-ink-soft">{note}</div>}
    </div>
  )
}
