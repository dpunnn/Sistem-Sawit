import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Palet semantik neraca.
        // supplier vs mill WAJIB beda warna -- "menunjuk dua arah"
        // harus terbaca sekali lihat, tanpa membaca label.
        supplier: { DEFAULT: '#d97706', soft: '#fef3c7' },
        mill:     { DEFAULT: '#dc2626', soft: '#fee2e2' },
        unknown:  { DEFAULT: '#6b7280', soft: '#f3f4f6' },
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
export default config
