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
    const apiUrl = process.env.API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
