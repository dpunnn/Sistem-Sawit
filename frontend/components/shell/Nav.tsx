'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

// Sertifikat sortasi menunjuk hasil grading PERTAMA yang tersimpan.
//
// Sebelumnya id-nya 4821 — angka karangan yang tidak pernah ada di
// basis data. Mengkliknya menampilkan sertifikat lengkap berisi
// "4.280 kg" karena request gagal lalu jatuh ke data contoh. Sertifikat
// dipakai dalam sengketa harga; mengarangnya jauh lebih buruk daripada
// mengaku tidak punya.
//
// Id 1 dipilih karena seed selalu membuatnya. Kalau ternyata tidak ada,
// halamannya sekarang mengatakan "tidak ditemukan", bukan mengarang.
const LINKS = [
  { href: '/', label: 'Gerbang', hint: 'Apa yang masuk?' },
  { href: '/neraca', label: 'Neraca Minyak', hint: 'Ke mana perginya?' },
  { href: '/batch/1', label: 'Sertifikat Sortasi', hint: 'Bukti untuk petani' },
]

export function Nav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-5 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <Mark />
          <span className="text-[15px] font-semibold tracking-tight text-ink">
            Neraca Minyak
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {LINKS.map((l) => {
            const active =
              l.href === '/' ? pathname === '/' : pathname.startsWith(l.href.split('/').slice(0, 2).join('/'))
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-[14px] transition',
                  active
                    ? 'bg-mill text-white'
                    : 'text-ink-soft hover:bg-plane hover:text-ink',
                )}
              >
                {l.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

/** Lambang: tandan sawit disederhanakan jadi tiga lapis brondolan. */
function Mark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden>
      <circle cx="13" cy="13" r="12.5" fill="#7d3f14" />
      <circle cx="13" cy="8.5" r="2.6" fill="#cf8c2a" />
      <circle cx="8.8" cy="14" r="2.6" fill="#cf8c2a" />
      <circle cx="17.2" cy="14" r="2.6" fill="#cf8c2a" />
      <circle cx="13" cy="18.6" r="2.6" fill="#f2e2c6" />
    </svg>
  )
}
