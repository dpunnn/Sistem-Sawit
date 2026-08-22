/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone: image production hanya berisi file yang benar-benar
  // dipakai, bukan seluruh node_modules. Ukuran image turun drastis.
  output: 'standalone',

  async rewrites() {
    // Browser SELALU memanggil origin yang sama (localhost:3000/api/...),
    // lalu Next.js meneruskannya ke container backend.
    //
    // Ini menyelesaikan jebakan klasik docker: browser tidak mengenal
    // hostname `backend`, karena nama itu hanya ada di dalam jaringan
    // docker. Dengan rewrites, tidak ada CORS dan tidak ada perbedaan
    // URL antara mode dev dan mode docker.
    // PENTING: nilai ini dibekukan saat `next build`, bukan dibaca
    // ulang saat server menyala. Karena itu docker-compose mengirim
    // API_URL sebagai build ARG, bukan hanya sebagai environment.
    // Kalau hanya environment, yang terpakai adalah nilai cadangan di
    // bawah — dan di dalam container, localhost adalah container
    // frontend sendiri.
    //
    // Nilai cadangan tetap localhost:8000 supaya `npm run dev` di host
    // bekerja tanpa konfigurasi tambahan.
    const apiUrl = process.env.API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      {
        // Gambar overlay hasil inferensi disajikan backend sebagai
        // berkas statis. Tanpa aturan ini, <img src="/static/..."> di
        // browser menjawab 404 — dan gagalnya senyap, karena halaman
        // tetap render dengan benar sementara satu-satunya bukti visual
        // yang dilihat juri justru kosong.
        source: '/static/:path*',
        destination: `${apiUrl}/static/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
