# ---- deps ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---- build ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# API_URL WAJIB ada saat BUILD, bukan cuma saat runtime.
#
# Next.js mengevaluasi `rewrites()` sekali saat `next build` lalu
# membekukan hasilnya ke .next/routes-manifest.json. Menyetel API_URL
# hanya lewat `environment:` di compose TIDAK berpengaruh: nilai yang
# terpakai sudah terlanjur dibekukan sebagai nilai cadangan
# `http://localhost:8000` -- dan di dalam container, localhost itu
# container frontend sendiri, bukan backend.
#
# Gejalanya menyesatkan: halaman tetap render 200 karena komponen server
# memanggil backend lewat jalur lain, sementara setiap /api/* dari
# browser menjawab 500 ECONNREFUSED.
ARG API_URL=http://backend:8000
ENV API_URL=$API_URL

RUN npm run build

# ---- runtime ----
# output: 'standalone' di next.config.js membuat folder .next/standalone
# berisi HANYA file yang dipakai. Image runtime jadi jauh lebih kecil
# daripada menyalin seluruh node_modules.
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
