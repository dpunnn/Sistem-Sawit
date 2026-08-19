import { cn } from '@/lib/utils'

/** Penanda titik pindai pada foto muatan.
 *
 *  Bentuknya sengaja meniru penanda pusat gempa: lingkaran solid di
 *  tengah sebagai titik acuan, lalu lingkaran solid menyebar keluar
 *  5 kali per detik. Ia MURNI penanda posisi kamera -- tidak membawa
 *  angka apa pun, jadi disembunyikan dari pembaca layar. */
export function ScanPulse({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn('quake', className)}>
      {[0, 1, 2, 3, 4].map((i) => (
        // 5 gelombang x geser 200 ms = satu lingkaran baru tiap 1/5 detik.
        <span key={i} className="quake-wave" style={{ animationDelay: `${i * 200}ms` }} />
      ))}
      <span className="quake-core" />
    </span>
  )
}
