// Tipe ini WAJIB cerminan dari backend/app/schemas/models.py.
// Kalau salah satu berubah, ubah keduanya.

/** Taksiran dengan selang. Jangan pernah pakai number polos untuk
 *  nilai hasil model -- seluruh sistem berjanji jujur soal
 *  ketidakpastian, termasuk di frontend. */
export type Estimate = { value: number; lo: number; hi: number }

export type Confidence = 'low' | 'medium' | 'high'
export type Side = 'supplier' | 'mill' | 'unknown'
