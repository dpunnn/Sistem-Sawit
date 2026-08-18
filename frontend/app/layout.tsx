import type { Metadata } from 'next'
import './globals.css'
import { Nav } from '@/components/shell/Nav'

export const metadata: Metadata = {
  title: 'Neraca Minyak',
  description:
    'Sistem forensik kehilangan rendemen kelapa sawit — menutup neraca dari gerbang sampai tangki.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>
        <Nav />
        {children}
        <footer className="mx-auto max-w-6xl px-5 py-10 text-[12px] leading-relaxed text-ink-soft">
          <p className="max-w-3xl">
            Setiap angka hasil model ditampilkan bersama selang keyakinannya. Sistem
            memberi bukti dan menyatakan seberapa yakin; keputusan finansial tetap di
            tangan manusia.
          </p>

          {/* Batasan disebut di muka, bukan disembunyikan. Ditaruh di
              footer setiap halaman supaya tidak ada layar yang bisa
              dibaca tanpa aksesnya. */}
          <details className="mt-4 max-w-3xl border-t border-line pt-4">
            <summary className="cursor-pointer font-medium text-ink">
              Batasan sistem ini
            </summary>
            <ul className="mt-3 space-y-2">
              <li>
                <strong className="font-medium text-ink">
                  Kalibrasi ke hasil lab OER aktual belum tervalidasi lapangan.
                </strong>{' '}
                Loop kalibrasi baru dapat disimulasikan, karena data operasional
                pabrik nyata tidak tersedia publik.
              </li>
              <li>
                <strong className="font-medium text-ink">
                  Parameter proses pabrik nyata tidak tersedia.
                </strong>{' '}
                Usulan setelan proses otomatis berstatus tahap lanjutan, bukan
                klaim saat ini.
              </li>
              <li>
                <strong className="font-medium text-ink">
                  Dampak terhadap keadilan bagi petani dapat diargumentasikan,
                  belum dibuktikan
                </strong>{' '}
                dengan angka lapangan.
              </li>
              <li>
                <strong className="font-medium text-ink">
                  Sistem ini menyentuh satu penyebab rendemen rendah
                </strong>{' '}
                — buah mentah yang masuk dan proses yang tidak optimal. Selisih
                menuju potensi 25–27% sebagian besar soal bibit dan manajemen
                kebun, di luar jangkauan sistem ini.
              </li>
              <li>
                <strong className="font-medium text-ink">
                  Angka potensi kerugian nasional bersifat teoretis.
                </strong>{' '}
                Yang realistis direbut adalah sebagian kecilnya.
              </li>
            </ul>
          </details>
        </footer>
      </body>
    </html>
  )
}
