/* Berkas ini SENGAJA KOSONG.
 *
 * Isinya dulu: 24 deteksi karangan, komposisi karangan, neraca karangan,
 * peringkat pemasok karangan, dan kurva koreksi yang dilabeli "bukti
 * sistem benar-benar mempelajari pabrik ini".
 *
 * Semua sudah diganti data nyata dari basis data. Yang membuat data
 * contoh berbahaya bukan keberadaannya, melainkan jalur mundur di
 * lib/api.ts yang dulu menampilkannya SETIAP KALI request gagal —
 * termasuk saat id tidak ada. Akibatnya sertifikat sortasi untuk muatan
 * yang tidak pernah tercatat tetap tampil lengkap dengan "4.280 kg",
 * ditandai hanya oleh badge kecil di pojok.
 *
 * Sekarang kegagalan menghasilkan `data: null`, dan layar menampilkan
 * keadaan kosong atau pesan error — bukan angka.
 *
 * Kalau suatu saat butuh fixture untuk pengujian, letakkan di berkas
 * uji, bukan di sini: apa pun yang ada di lib/ cepat atau lambat akan
 * di-import oleh halaman.
 */
export {}
