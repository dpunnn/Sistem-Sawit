import type { Config } from 'tailwindcss'

// PALET: HANYA COKLAT & PUTIH.
//
// Seluruh nilai di bawah bukan pilihan selera -- setiap warna sudah
// diuji dengan validator palet (jarak OKLab, simulasi buta warna
// protan/deutan, kontras terhadap permukaan). Ringkasan hasilnya
// dicatat di komentar masing-masing supaya bisa diaudit ulang.
//
// Kendala desain yang harus dipenuhi bersamaan:
//   (a) hanya coklat & putih,
//   (b) sisi PEMASOK vs sisi PABRIK tetap terbaca sekali lihat.
// Karena hue dikunci ke satu keluarga, pembeda dipikul oleh TERANG-GELAP,
// bukan oleh perbedaan hue.

const config: Config = {
  darkMode: ['class'],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // --- Permukaan & garis -------------------------------------
        plane: '#faf7f2', // latar halaman (putih hangat)
        surface: '#ffffff', // permukaan kartu & grafik
        line: '#e5dbc9', // hairline 1px, selalu solid (tidak pernah putus-putus)

        // --- Tinta ---------------------------------------------------
        // Teks TIDAK PERNAH memakai warna data; identitas dibawa oleh
        // kotak warna di sebelah teks, bukan oleh teks berwarna.
        ink: {
          DEFAULT: '#2a1c10', // 16,5:1 di atas putih
          soft: '#6b5844', //  6,8:1 -- teks sekunder
          muted: '#94806a', //  3,8:1 -- hanya label besar / dekoratif
        },

        // --- Palet semantik neraca ----------------------------------
        // Diuji berpasangan (--pairs all, mode terang, permukaan #fdfcfa):
        //   pemasok <-> pabrik  ΔE 25,8 normal · 25,9 deutan
        //   pemasok <-> sisa    ΔE 18,5 normal · 17,5 deutan
        // Semua di atas ambang (>=15 normal, >=8 CVD).
        supplier: {
          DEFAULT: '#cf8c2a', // karamel terang -- sisi kebun/petani
          soft: '#f7ecd8',
        },
        mill: {
          DEFAULT: '#7d3f14', // coklat tua -- sisi pabrik
          soft: '#efe1d5',
        },
        // "Tidak terjelaskan" sengaja NETRAL: ia bukan identitas ketiga,
        // melainkan ketiadaan atribusi. Kontrasnya rendah (1,6:1), jadi
        // WAJIB didampingi arsiran 45derajat + garis putus + label langsung.
        unknown: {
          DEFAULT: '#cfc8bc',
          soft: '#f2efe9',
        },

        // --- Ramp ordinal kematangan --------------------------------
        // Kematangan itu BERURUTAN, jadi warnanya wajib satu hue dengan
        // terang menurun -- pembaca melihat urutannya di warna itu sendiri.
        // Lolos --ordinal: monoton, jarak ΔL >= 0,06, ujung terang 2,24:1.
        ripe: {
          unripe: '#cba871',
          underripe: '#b98a44',
          ripe: '#a06c22',
          overripe: '#7d4d18',
          rotten: '#54300e',
          // Di luar sumbu kematangan -- netral, bukan bagian ramp.
          empty: '#d8d2c8',
          abnormal: '#b3aa9c',
        },
      },
      fontFamily: {
        // Satu sans untuk semuanya, termasuk angka pahlawan.
        // Tidak ada display/serif -- itu terbaca sebagai dekorasi.
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(42,28,16,0.05), 0 1px 12px rgba(42,28,16,0.04)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
export default config
