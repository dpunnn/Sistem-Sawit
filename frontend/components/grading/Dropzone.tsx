'use client'

import { useRef, useState } from 'react'
import { cn } from '@/lib/utils'

const DITERIMA = ['image/jpeg', 'image/png', 'image/webp']
const MAKS_MB = 12

/** Area unggah: seret-lepas DAN klik.
 *
 *  Dua jalur karena dua kebiasaan yang sama nyata. Grader di gerbang
 *  memakai layar sentuh dan akan mengetuk; siapa pun yang menyeret foto
 *  dari folder akan menyeret. Menyediakan satu saja membuat separuh
 *  orang mengira layarnya rusak.
 *
 *  Validasi dilakukan di sini, sebelum request dikirim: menolak berkas
 *  10 detik kemudian setelah unggahan selesai jauh lebih menyebalkan
 *  daripada menolaknya seketika. */
export function Dropzone({
  onPick,
  disabled = false,
  children,
}: {
  onPick: (file: File) => void
  disabled?: boolean
  children: React.ReactNode
}) {
  const [seret, setSeret] = useState(false)
  const [tolak, setTolak] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function terima(file: File | undefined) {
    if (!file) return
    if (!DITERIMA.includes(file.type)) {
      setTolak(`Format ${file.type || 'tidak dikenal'} tidak didukung. Pakai JPG, PNG, atau WebP.`)
      return
    }
    if (file.size > MAKS_MB * 1024 * 1024) {
      setTolak(`Berkas ${(file.size / 1024 / 1024).toFixed(1)} MB melebihi batas ${MAKS_MB} MB.`)
      return
    }
    setTolak(null)
    onPick(file)
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          if (disabled) return
          e.preventDefault()
          setSeret(true)
        }}
        onDragLeave={() => setSeret(false)}
        onDrop={(e) => {
          if (disabled) return
          e.preventDefault()
          setSeret(false)
          terima(e.dataTransfer.files?.[0])
        }}
        className={cn(
          'rounded-lg transition',
          seret && 'outline outline-2 outline-offset-4 outline-mill',
          disabled && 'pointer-events-none',
        )}
      >
        {children}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={DITERIMA.join(',')}
        className="hidden"
        onChange={(e) => {
          terima(e.target.files?.[0])
          // dikosongkan supaya memilih berkas yang SAMA dua kali tetap
          // memicu onChange
          e.target.value = ''
        }}
      />

      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        data-dropzone-trigger
      />

      {seret && !disabled && (
        <p className="mt-2 text-[12px] text-mill">Lepaskan untuk memindai muatan ini.</p>
      )}
      {tolak && (
        <p role="alert" className="mt-2 text-[12px] leading-relaxed text-mill">
          {tolak}
        </p>
      )}
    </div>
  )
}

/** Buka dialog berkas milik Dropzone dari tombol mana pun di halaman.
 *  Dipakai supaya tombol utama tetap berada di tempat yang masuk akal
 *  secara tata letak, bukan terpaksa di dalam area seret. */
export function bukaDialogBerkas(root: HTMLElement | null) {
  const t = root?.querySelector<HTMLButtonElement>('[data-dropzone-trigger]')
  t?.click()
}
