import type { RipenessClass } from '@/types'
import { RIPENESS_FILL, RIPENESS_LABEL, RIPENESS_ORDER } from '@/lib/format'
import { Legend } from '@/components/ui/Bits'

/** Kunci baca untuk kotak berwarna di atas foto muatan.
 *
 *  Tanpa ini, orang yang baru pertama melihat layar hanya melihat kotak
 *  berwarna-warni tanpa tahu artinya -- termasuk juri di detik pertama.
 *  Karena palet dikunci ke satu keluarga hue, warna saja memang tidak
 *  cukup memikul makna; legenda adalah kanal penggantinya.
 *
 *  Kelas yang tidak muncul di muatan ini sengaja tetap ditampilkan
 *  dengan `only`, supaya legenda mencerminkan gambar, bukan daftar
 *  teoretis yang membingungkan. */
export function RipenessLegend({ only }: { only?: RipenessClass[] }) {
  const kelas = only?.length
    ? RIPENESS_ORDER.filter((r) => only.includes(r))
    : RIPENESS_ORDER

  return (
    <Legend
      items={kelas.map((r) => ({ label: RIPENESS_LABEL[r], fill: RIPENESS_FILL[r] }))}
    />
  )
}
