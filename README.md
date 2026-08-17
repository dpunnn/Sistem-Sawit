# Neraca Minyak

> **Sistem forensik kehilangan rendemen kelapa sawit.**
> Sistem lain menilai buah di gerbang. Kami menutup neracanya dari kebun
> sampai tangki — dan menunjukkan, dengan bukti, ke mana setiap poin
> rendemen pergi.

AI Innovation Challenge 2026 · COMPFEST 18 · Tema: **Smart Manufacturing**

---

## Daftar Isi

- [Masalah](#masalah)
- [Solusi](#solusi)
- [Alur Sistem](#alur-sistem)
- [Rincian Model](#rincian-model)
- [Arsitektur](#arsitektur)
- [Stack Teknologi](#stack-teknologi)
- [Menjalankan Secara Lokal](#menjalankan-secara-lokal)
- [Setup untuk Anggota Tim](#setup-untuk-anggota-tim)
- [Skenario Demo](#skenario-demo)
- [Struktur Repo](#struktur-repo)
- [Dataset](#dataset)
- [Status Pengembangan](#status-pengembangan)
- [Batasan](#batasan)
- [Roadmap](#roadmap)
- [Lisensi](#lisensi)

---

## Masalah

Rendemen minyak sawit Indonesia hanya **18–20%**, padahal Tandan Buah
Segar (TBS) matang seharusnya menghasilkan **≥21%**. Dengan produksi CPO
nasional 51,66 juta ton, selisih dua poin itu bernilai puluhan triliun
rupiah per tahun.

Yang lebih parah: **tidak ada yang tahu ke mana perginya.**

Pabrik sudah mengukur kehilangan minyak di tiap stasiun setiap hari —
itu pekerjaan lab standar. Tapi tidak ada yang menghubungkan angka itu
dengan kualitas buah yang masuk. Pabrik tahu "rendemen hari ini 19,2%",
tapi tidak ada yang bisa menjawab **"kenapa bukan 21%?"**

Akibatnya setiap hari terjadi saling tuding tanpa bukti:

| Pihak  | Klaim                   |
| ------ | ----------------------- |
| Pabrik | "buah petani jelek"     |
| Petani | "sortasi pabrik curang" |

Dua-duanya menebak. Tidak ada yang bisa membuktikan. Sementara itu
sortasi di gerbang masih dilakukan **dengan mata telanjang**, dan
penilaian subjektif itu menentukan dua hal sekaligus: berapa petani
dibayar, dan bagaimana pabrik menyetel prosesnya.

---

## Solusi

Sistem dua lapis yang menutup neraca massa minyak, lalu mengatribusikan
selisihnya ke penyebab — **dengan selang keyakinan, dan menunjuk ke dua
arah**.

### Keluaran inti

```
Potensi rendemen muatan hari ini ............. 21,4%
Rendemen aktual tercapai ..................... 19,2%
                                              --------
KEHILANGAN ................................... 2,2 poin

TERURAI MENJADI:
  0,7 ± 0,25   buah mentah        → pemasok A, C, F      [PEMASOK]
  0,5 ± 0,15   restan 9 jam       → keputusan antrian    [PABRIK]
  0,6 ± 0,20   sterilisasi        → setelan tidak sesuai [PABRIK]
  0,2 ± 0,10   ampas kempa        → di atas standar      [PABRIK]
  0,2 ± 0,30   TIDAK TERJELASKAN  → perlu diperiksa      [?]

NILAI KEHILANGAN HARI INI: Rp 47,3 juta
```

Tiga hal yang membedakan keluaran ini:

**1. Menyebut penyebab, bukan cuma angka.**
"Rendemen 19,2%" tidak bisa ditindaklanjuti. "0,5 poin dari restan
9 jam" bisa diperbaiki besok pagi oleh orang tertentu.

**2. Menunjuk ke dua arah.**
Sebagian kehilangan adalah tanggung jawab pemasok (buah mentah),
sebagian tanggung jawab pabrik (restan, sterilisasi, ampas). Tidak ada
pihak yang dilindungi. Vendor yang dibayar pabrik tidak bisa menjual
produk yang menyalahkan pembelinya — ini pembeda struktural, bukan
sekadar fitur.

**3. Jujur soal yang tidak diketahui.**
Baris "TIDAK TERJELASKAN" sengaja ada. Sistem mengakui batas
pengetahuannya alih-alih memaksakan penjelasan. Kehilangan yang tidak
cocok dengan penyebab manapun bisa berarti kebocoran alat, timbangan
tidak terkalibrasi, atau hal lain yang perlu investigasi.

---

## Alur Sistem

```mermaid
flowchart TD

  subgraph GATE["  GERBANG PKS — muatan masuk "]
    direction TB
    TRUK["Truk TBS tiba<br/><small>pemasok swadaya / KUD / inti</small>"]
    TIMBANG["Jembatan Timbang<br/><small>berat bruto kg</small>"]
    KAM["Kamera<br/><small>foto tumpukan, beberapa sudut</small>"]
    TRUK --> TIMBANG
    TRUK --> KAM
  end

  subgraph L1[" 👁 LAPIS 1 — PERSEPSI · Apa yang masuk? "]
    direction TB
    M1["<b>Model 1</b> · Detektor tandan<br/>3 kelas struktural · YOLOv8s<br/><small>mAP@50 0,955 pada 14 tumpukan baru</small>"]
    MO["<b>Head Kematangan</b><br/>4 tingkat, dinilai per crop<br/><small>akurasi 0,635 pada muatan campuran</small>"]
    M2["<b>Model 2</b> · Permukaan → seluruh muatan<br/>inferensi di bawah observasi parsial<br/><small>output: selang terkalibrasi</small>"]
    M4["<b>Model 4</b> · Potensi minyak<br/>regresi, koefisien terbit + koreksi<br/><small>output: kg ± selang</small>"]
    M1 -->|"crop tiap tandan"| MO
    MO -->|"komposisi terlihat ±e1"| M2
    M2 -->|"komposisi muatan ±e2"| M4
  end

  GRADER{"Keyakinan<br/>tinggi?"}
  MANUSIA["Grader periksa<br/><small>hanya tandan ragu, bukan semua</small>"]

  DB1[("grading_result<br/><small>composition JSONB · potensi ± selang</small>")]

  subgraph MILL["  PROSES PABRIK — oil loss diukur lab tiap hari "]
    direction LR
    ST["Sterilizer<br/><small>kondensat 1,83%</small>"]
    TH["Thresher<br/><small>janjang kosong 2,44%</small>"]
    PR["Press<br/><small>ampas kempa 4,17%</small>"]
    KL["Klarifikasi<br/><small>CST underflow 7,04%</small>"]
    ST --> TH --> PR --> KL
  end

  DB2[("station_loss")]
  DB3[("shift_output<br/><small>CPO aktual kg</small>")]

  subgraph L2["  LAPIS 2 — PENALARAN · Ke mana perginya? "]
    direction TB
    M5["<b>Model 5</b> · Rekonsiliasi neraca massa<br/>struktur 3 baris, deterministik<br/><small>teoretis → realistis → aktual</small>"]
    M6["<b>Model 6</b> · Atribusi kehilangan<br/>dekomposisi + optimasi berkendala<br/><small>tiap penyebab ± selang + ambang tindakan</small>"]
    M5 -->|"selisih ±e4"| M6
  end

  DB4[("balance<br/><small>attribution JSONB</small>")]
  KARTU["<b>KARTU NERACA HARIAN</b><br/>2,2 poin hilang · Rp 47,3 juta"]

  SUP["➜ SISI PEMASOK<br/>0,7 ± 0,25 buah mentah<br/><small>pemasok A, C, F</small>"]
  MIL["➜ SISI PABRIK<br/>1,3 ± 0,30 restan + sterilisasi + ampas<br/><small>bisa diperbaiki besok pagi</small>"]
  UNK["➜ TIDAK TERJELASKAN<br/>0,2 ± 0,30<br/><small>perlu diperiksa manusia</small>"]

  TIMBANG --> M4
  KAM --> M1
  M4 -->|"4.280 kg ± 190"| GRADER
  GRADER -->|"ya"| DB1
  GRADER -->|"tidak"| MANUSIA
  MANUSIA -->|"koreksi jadi data latih"| DB1

  DB1 -->|"buah masuk proses"| MILL
  MILL --> DB2
  MILL --> DB3

  DB1 -->|"potensi"| M5
  DB2 -->|"loss terukur"| M5
  DB3 -->|"CPO aktual"| M5

  M6 --> DB4 --> KARTU
  KARTU --> SUP
  KARTU --> MIL
  KARTU --> UNK

  classDef supplier fill:#78350f,stroke:#d97706,color:#fde68a
  classDef mill fill:#7f1d1d,stroke:#dc2626,color:#fecaca
  classDef unknown fill:#374151,stroke:#6b7280,color:#e5e7eb
  classDef hero fill:#064e3b,stroke:#10b981,color:#d1fae5
  class SUP supplier
  class MIL mill
  class UNK unknown
  class KARTU hero
```

### Struktur neraca tiga baris

Ini keputusan desain terpenting sistem. Neraca **tidak boleh** langsung
membandingkan potensi dengan aktual, karena buah mentah akan terhitung
dua kali — sekali sebagai pengurang potensi, sekali lagi sebagai
penyebab kehilangan.

```
Potensi TEORETIS   (andai seluruh muatan matang)      21,4%
  (−) rugi komposisi buah masuk         0,7  ────────► PEMASOK
─────────────────────────────────────────────────────────────
Potensi REALISTIS  (muatan ini apa adanya)            20,7%
  (−) kehilangan proses pabrik          1,3  ────────► PABRIK
  (−) tidak terjelaskan                 0,2
─────────────────────────────────────────────────────────────
Rendemen AKTUAL                                       19,2%
```

Struktur ini sekaligus membuat "menunjuk dua arah" menjadi **struktur
matematis**, bukan slogan: tanggung jawab pemasok dan pabrik terpisah
secara aritmetika dan terbaca dalam satu layar.

---

## Rincian Model

### Lapis 1 — Persepsi (`ai/perception/`)

**Model 1 — Detektor tandan (tiga kelas struktural)**

Dari foto tumpukan TBS, tiap objek dikotaki dan digolongkan ke tiga kelas
**struktural** — bukan tingkat kematangan:

| Kelas | Isi | Kotak |
|---|---|---|
| `tandan` | empat tingkat kematangan, dilebur | 11.102 |
| `janjang_kosong` | tandan sisa setelah dirontokkan | 857 |
| `abnormal` | tandan cacat | 2.599 |

Peleburan empat tingkat kematangan menjadi satu kelas `tandan` disengaja.
Dengan hanya 62 tumpukan di sisi latih, memusatkan sinyal pada satu konsep
jauh lebih baik daripada memecahnya jadi empat konsep setengah matang —
kelas `tandan` naik dari ~2.400 menjadi 7.838 kotak latih.

Hasil pada 14 tumpukan yang belum pernah dilihat: **mAP@50 0,955 ·
mAP@50-95 0,789**.

**Head Ordinal — menilai kematangan pada crop**

Tingkat kematangan ditangani model terpisah yang bekerja pada crop hasil
deteksi. Kematangan bersifat **berurutan**, jadi loss-nya CORAL, bukan
cross-entropy. Alasannya bisnis, bukan estetika: cross-entropy menganggap
semua kesalahan sama beratnya, padahal salah menebak "matang" jadi "lewat
matang" jauh lebih murah daripada "mentah" jadi "terlalu masak" — yang
mengubah potongan pembayaran petani secara drastis.

CORAL menjawab tiga pertanyaan biner berjenjang alih-alih memilih satu dari
empat kelas. Bobot lapisan akhirnya **dibagi bersama**, hanya biasnya berbeda
per ambang — sehingga model secara struktural tidak mungkin mengatakan "lebih
dari masak" tanpa juga "lebih dari mentah". Urutan dijamin arsitektur, bukan
harapan.

Metrik utamanya **MAE indeks kelas**, bukan akurasi: klaimnya bukan "lebih
sering benar", melainkan "kalau salah, salahnya lebih dekat".

**Model 2 — Dari permukaan ke seluruh muatan**

Kamera hanya melihat lapisan atas tumpukan. Apakah permukaan mewakili
keseluruhan? Hampir pasti tidak: tandan berat cenderung tenggelam, dan
buah bagus kadang sengaja ditaruh di atas.

Jadi ini bukan klasifikasi gambar, melainkan **inferensi statistik di
bawah observasi parsial** — menaksir distribusi populasi dari sampel
yang bias. Keluarannya wajib berupa selang, bukan angka telanjang.

**Model 4 — Potensi minyak per muatan**

Regresi, bukan klasifikasi. Sistem lain berhenti di "68% matang"; angka
itu tidak bisa dimasukkan ke neraca. Yang dibutuhkan adalah **berapa
kilogram** minyak ada di truk ini.

Basisnya koefisien terbit (−0,13 poin OER per 1% buah mentah; rendemen
per varietas dan tingkat kematangan) ditambah koreksi terpelajar **di
atas** formula, bukan menggantikannya. Formula dasarnya wajib transparan
dan bisa ditelusuri — keluarannya menyangkut uang orang.

### Lapis 2 — Penalaran (`ai/reasoning/`)

**Model 5 — Rekonsiliasi neraca massa**

```
POTENSI = CPO_aktual
        + loss_kondensat + loss_janjang_kosong + loss_ampas
        + loss_sludge + loss_CST + ...
        + SISA_YANG_HARUS_DIJELASKAN
```

Sebagian besar deterministik — fisika dan akuntansi. Justru itu
kekuatannya: bagian ini bisa diaudit siapa pun, tidak ada kotak hitam.

**Model 6 — Atribusi kehilangan**

Memecah selisih menjadi penyebab, masing-masing dengan selang
keyakinan. Sulit karena penyebabnya saling berkorelasi: buah mentah dan
sterilisasi buruk sama-sama menaikkan loss ampas kempa.

Aturan emas sistem ini:

> ❌ "0,7 poin hilang karena buah mentah pemasok A"
> ✅ "0,7 ± 0,25 poin — keyakinan sedang. Cukup untuk bahan diskusi,
> belum cukup untuk memotong pembayaran."

### Perambatan ketidakpastian

Keluaran sistem ini dipakai untuk menyalahkan orang dan memotong uang.
Sistem yang mengaku pasti padahal tidak adalah sistem berbahaya. Karena
itu ketidakpastian dirambatkan di sepanjang rantai:

```
Model 1 (klasifikasi per tandan)  ±e1
   ↓
Model 2 (komposisi muatan)        ±e2   (e2 > e1, karena oklusi)
   ↓
Model 4 (potensi minyak kg)       ±e3
   ↓
Model 5 (selisih neraca)          ±e4   (membesar: selisih dua taksiran)
   ↓
Model 6 (atribusi per penyebab)   ±e5
```

Dan setiap keluaran punya **ambang tindakan**:

| Keyakinan | Boleh dipakai untuk                     |
| --------- | --------------------------------------- |
| Rendah    | hanya ditampilkan, tidak memicu apa pun |
| Sedang    | bahan diskusi / pemeriksaan manual      |
| Tinggi    | boleh jadi dasar keputusan finansial    |

Ini bentuk konkret prinsip *learning to defer*: model tahu kapan dirinya
tidak cukup yakin untuk mengambil alih keputusan manusia.

---

## Arsitektur

Tiga komponen terpisah bersih, masing-masing dengan tanggung jawab
tunggal:

```mermaid
flowchart LR

  subgraph FE[" frontend/ · Next.js 15 "]
    direction TB
    PAGE["app/<br/><small>page · neraca · batch/[id]</small>"]
    COMP["components/<br/><small>grading · neraca · ui</small>"]
    TYPE["types/<br/><small>cerminan schema backend</small>"]
  end

  subgraph BE[" backend/ · FastAPI "]
    direction TB
    ROUTER["routers/<br/><small>URL, validasi, kode status</small>"]
    SERVICE["services/<br/><small>orkestrasi + jembatan ke ai/</small>"]
    SCHEMA["schemas/<br/><small>kontrak data Pydantic</small>"]
    CORE["core/<br/><small>koneksi database</small>"]
    ROUTER --> SERVICE
    SERVICE --> SCHEMA
    SERVICE --> CORE
  end

  subgraph AI[" ai/ · tidak tahu HTTP maupun database "]
    direction TB
    PERC["perception/<br/><small>Model 1 · 2 · 4 · overlay</small>"]
    REAS["reasoning/<br/><small>Model 5 · 6</small>"]
    SIM["simulator/<br/><small>neraca massa pabrik</small>"]
    CFG["config/<br/><small>coefficients.yaml + sitasi</small>"]
    PERC -.->|"pakai koefisien"| CFG
    REAS -.->|"pakai koefisien"| CFG
  end

  DB[("PostgreSQL 16<br/><small>JSONB untuk komposisi & atribusi</small>")]

  PAGE -->|"fetch /api/*<br/>lewat rewrites"| ROUTER
  ROUTER -->|"JSON"| PAGE
  SERVICE -->|"import langsung"| PERC
  SERVICE -->|"import langsung"| REAS
  CORE <--> DB
  SIM -.->|"data uji"| REAS

  classDef fe fill:#1e3a8a,stroke:#3b82f6,color:#dbeafe
  classDef be fill:#064e3b,stroke:#10b981,color:#d1fae5
  classDef ai fill:#581c87,stroke:#a855f7,color:#f3e8ff
  class PAGE,COMP,TYPE fe
  class ROUTER,SERVICE,SCHEMA,CORE be
  class PERC,REAS,SIM,CFG ai
```

**Aturan lapisan:**

- `frontend/` tidak pernah tahu tentang model. Ia hanya bicara HTTP.
- `backend/` adalah **jembatan**, bukan pemilik logika. Ia memanggil
  modul di `ai/`, tidak menulis ulang rumusnya. Kalau ada rumus rendemen
  menyelinap ke `backend/`, lapisannya bocor.
- `ai/` tidak tahu apa-apa tentang HTTP maupun database. Ia bisa dipakai
  dari skrip, notebook, atau CLI tanpa menyalakan server.

Konsekuensinya: mengganti detektor dari satu arsitektur ke arsitektur
lain hanya menyentuh `ai/perception/detector.py` dan satu baris di
`backend/app/services/`. Frontend tidak tahu apa-apa.

### Alur satu request

```
POST /api/grade (upload foto)
   │
   ├─► backend/app/routers/grading.py     validasi file, kode status
   │
   ├─► backend/app/services/grading.py    orkestrasi langkah:
   │       │
   │       ├─► ai/perception/detector.py      Model 1
   │       ├─► ai/perception/composition.py   Model 2
   │       ├─► ai/perception/potential.py     Model 4
   │       ├─► ai/perception/overlay.py       render bbox
   │       └─► backend/app/core/db.py         simpan hasil
   │
   └─► backend/app/schemas/models.py      bentuk response
                                          (semua taksiran = Estimate)
```

---

## Stack Teknologi

| Lapisan        | Teknologi                                      | Alasan pemilihan                                                                                              |
| -------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Frontend       | **Next.js 15** (App Router) + TypeScript | Pemisahan frontend–backend yang bersih; ekosistem matang                                                     |
| Styling        | **Tailwind CSS**                         | Warna semantik: sisi pemasok vs pabrik wajib beda warna agar terbaca sekali lihat                             |
| Backend        | **FastAPI** + Uvicorn                    | Validasi otomatis + dokumentasi OpenAPI di`/docs` tanpa menulis apa pun                                     |
| Kontrak data   | **Pydantic v2**                          | Tipe`Estimate(value, lo, hi)` membuat selang ketidakpastian jadi kontrak resmi sistem, bukan tambahan di UI |
| Database       | **PostgreSQL 16** + psycopg 3            | `JSONB` untuk komposisi & atribusi yang strukturnya berubah-ubah dan tiap nilainya butuh selang             |
| Model          | **PyTorch** (wheel CPU)                  | Inferensi harus jalan tanpa GPU di mesin penguji                                                              |
| Ketidakpastian | quantile regression / ensemble                 | Cara termurah menghasilkan selang yang bisa dikalibrasi                                                       |
| Penalaran      | **NumPy + SciPy**                        | Deterministik, bisa diaudit baris per baris                                                                   |
| Kontainer      | **Docker Compose**                       | Tiga service:`db`, `backend`, `frontend`                                                                |

### Keputusan teknis yang perlu dijelaskan

**Kenapa `Estimate` sebagai tipe, bukan konvensi.**
Dengan menjadikannya tipe Pydantic resmi, mustahil ada angka telanjang
tanpa selang menyelinap ke frontend. Janji "jujur soal ketidakyakinan"
ditegakkan oleh sistem tipe, bukan oleh niat baik programmer.

**Kenapa `rewrites`, bukan panggilan langsung ke backend.**
Browser tidak mengenal hostname `backend` — nama itu hanya ada di dalam
jaringan Docker. Dengan `rewrites` di `next.config.js`, browser selalu
memanggil origin yang sama (`/api/*`), lalu Next.js meneruskannya. Hasil:
tidak ada CORS, dan tidak ada perbedaan URL antara mode pengembangan dan
mode Docker.

**Kenapa `condition: service_healthy`, bukan `depends_on` biasa.**
`depends_on` biasa hanya menunggu container *start*, bukan *ready*.
Tanpa healthcheck, backend menyala sebelum Postgres siap menerima
koneksi lalu crash — dan bug ini justru muncul di mesin yang lebih
lambat, alias mesin penguji.

**Kenapa torch wheel CPU.**
`pip install torch` biasa menarik seluruh CUDA runtime dan membuat image
membengkak sampai ~5 GB. Wheel CPU menurunkannya ke ratusan MB. Training
dilakukan di luar Docker; yang masuk container hanya inferensi.

---

## Menjalankan Secara Lokal

### Prasyarat

- Docker Desktop / Docker Engine + Docker Compose v2
- Ruang disk ~3 GB
- Tidak perlu GPU, tidak perlu Python atau Node terpasang di host

### Langkah

```bash
git clone https://github.com/dpunnn/Sistem-Sawit.git
cd Sistem-Sawit
docker compose up --build
```

Buka **http://localhost:3000**

| Alamat                           | Isi                                  |
| -------------------------------- | ------------------------------------ |
| http://localhost:3000            | Antarmuka utama                      |
| http://localhost:3000/neraca     | Kartu neraca harian                  |
| http://localhost:8000/docs       | Dokumentasi API interaktif (OpenAPI) |
| http://localhost:8000/api/health | Cek koneksi backend ↔ database      |

> **Estimasi waktu build pertama: 8–12 menit.** Sebagian besar dipakai
> mengunduh PyTorch dan menjalankan `next build`. Build berikutnya jauh
> lebih cepat karena layer caching. Kalau terlihat diam lama di tahap
> `pip install torch`, itu normal.

### Data awal

Database terisi otomatis saat pertama kali dijalankan. Skrip di
`backend/db/init/` dieksekusi Postgres secara otomatis ketika volume
masih kosong — tidak ada langkah migrasi manual.

### Mengulang dari nol

```bash
docker compose down -v
docker compose up --build
```

Flag `-v` menghapus volume database sehingga skrip inisialisasi berjalan
lagi. **Ini penting:** skrip di `docker-entrypoint-initdb.d` hanya
dijalankan saat volume kosong, jadi tanpa `-v` perubahan skema tidak
akan terlihat.

### Menjalankan tanpa Docker (untuk pengembangan)

```bash
# Backend
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql://neraca:neraca@localhost:5432/neraca
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Menjalankan test

```bash
# uji lapis penalaran (Model 5 & 6) — 35 uji
pytest tests/ -v

# uji backend
cd backend && pytest
```

Selain itu tiap modul AI punya swauji yang bisa dijalankan langsung:

```bash
python ai/simulator/mill.py            # 6 swauji neraca massa
python ai/reasoning/balance.py         # peragaan kartu neraca dua mode
python ai/reasoning/attribution.py     # pola yang ditemukan sendiri
python ai/evaluation/rule_recovery.py  # pemulihan aturan + 4 uji ketahanan
```

---

## Setup untuk Anggota Tim

### Onboarding pertama kali

```bash
git clone https://github.com/dpunnn/Sistem-Sawit.git
cd Sistem-Sawit
cp .env.example .env
docker compose up --build
```

Empat baris, selesai. Tidak perlu memasang Python atau Node di komputer —
semuanya dibangun di dalam container.

### Kenapa beberapa file tidak ada di repo

Sebagian berkas sengaja tidak di-commit. Penanganannya berbeda-beda:

| Berkas                         | Kenapa diabaikan                | Cara mendapatkannya                                   |
| ------------------------------ | ------------------------------- | ----------------------------------------------------- |
| `node_modules/`              | ratusan MB, isinya beda per OS  | `npm install`                                       |
| `.venv/`, `__pycache__/`   | artefak lokal                   | `pip install -r requirements.txt`                   |
| `.next/`, `.pytest_cache/` | hasil build                     | dibuat otomatis                                       |
| `.env`                       | tempat nilai rahasia            | `cp .env.example .env`                              |
| `data/raw/`                  | dataset publik, ribuan berkas   | unduh sendiri dari sumber di bagian[Dataset](#dataset) |
| `ai/weights/`                | bobot model, berkas biner besar | lihat catatan di bawah                                |

Prinsipnya: **apa pun yang bisa dibangun ulang dari berkas yang sudah ada
di repo, tidak ikut di-commit.** Yang di-commit hanya sumber kebenarannya
(`package.json`, `requirements.txt`, `.env.example`).

### Mendapatkan dataset

Jangan saling mengirim berkas dataset antar-anggota. Semuanya bersumber
publik, jadi setiap orang mengunduh sendiri dari tautan di bagian
[Dataset](#dataset). Ini menjaga reprodusibilitas dan mematuhi ketentuan
lisensi CC-BY.

Letakkan hasil unduhan di:

```
data/raw/<nama-dataset>/
```

Struktur folder ini diabaikan Git, tetapi wajib sama di semua mesin agar
skrip pelatihan di `ai/training/` berjalan tanpa penyesuaian path.

### Bobot model

Bobot hasil pelatihan **tidak diabaikan selamanya**. Begitu Model 1
selesai dilatih, bobotnya wajib masuk repo — tanpa itu tidak ada yang
bisa menjalankan sistem, termasuk penguji.

Jika ukurannya melebihi ~100 MB, gunakan Git LFS:

```bash
git lfs install
git lfs track "ai/weights/*.pt"
git add .gitattributes
```

Lalu hapus baris `ai/weights/*` dari `.gitignore`.

### Alur pengembangan harian

Untuk iterasi cepat (terutama frontend), jalankan di luar Docker:

```bash
# Terminal 1 — database saja
docker compose up db

# Terminal 2 — backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 3 — frontend
cd frontend
npm install
npm run dev
```

Pastikan menjalankan `docker compose up --build` penuh sebelum push
perubahan besar, untuk memastikan sistem tetap utuh di lingkungan bersih.

### Konvensi commit

Setiap commit mengikuti [Conventional Commits](https://www.conventionalcommits.org):

```
feat: <deskripsi>       fitur atau fungsionalitas baru
fix: <deskripsi>        perbaikan bug
refactor: <deskripsi>   perubahan struktur tanpa mengubah perilaku
chore: <deskripsi>      konfigurasi, dependensi, berkas pendukung
docs: <deskripsi>       dokumentasi
```

Boleh ditambah cakupan agar lebih jelas:

```bash
git commit -m "feat(ai): tambah head ordinal CORAL pada detektor"
git commit -m "fix(backend): perbaiki propagasi selang pada potensi minyak"
git commit -m "chore(frontend): tambah package-lock untuk build reprodusibel"
```

Commit dan push setiap menyelesaikan satu perubahan bermakna, bukan
menumpuk di akhir — riwayat yang menunjukkan pengembangan bertahap
adalah bagian dari yang dinilai.

### Kontrak data antara backend dan frontend

`backend/app/schemas/models.py` dan `frontend/types/index.ts` adalah
cerminan satu sama lain. **Jika salah satu berubah, keduanya harus
diubah dalam commit yang sama.**

Kontrak ini disepakati di awal justru agar frontend dapat membangun
seluruh tampilan memakai data contoh sementara model masih dilatih —
tidak ada bagian yang menunggu bagian lain.

---

## Skenario Demo

Foto contoh tersedia di `data/samples/`. Urutan yang menunjukkan
perbedaan paling jelas:

1. **Unggah `muatan-bagus.jpg`** — komposisi didominasi buah matang,
   potensi minyak tinggi, sedikit tandan berkeyakinan rendah.
2. **Unggah `muatan-mentah.jpg`** — perhatikan potensi minyak turun
   drastis, dan selang keyakinan melebar karena komposisinya lebih sulit
   ditaksir.
3. **Buka `/neraca`** — kartu tiga baris muncul beserta grafik waterfall.
   Perhatikan warna berbeda untuk kehilangan sisi pemasok dan sisi
   pabrik.
4. **Perhatikan baris "TIDAK TERJELASKAN"** — sistem tidak memaksakan
   penjelasan untuk semua hal.

---

## Struktur Repo

```
Sistem-Sawit/
│
├── frontend/                 Next.js 15 + TypeScript + Tailwind
│   ├── app/                  page.tsx · neraca/ · batch/[id]/
│   ├── components/           ui/ · grading/ · neraca/
│   ├── lib/                  klien API & utilitas
│   ├── types/                cerminan schema backend
│   └── Dockerfile            multi-stage, output standalone
│
├── backend/                  FastAPI
│   ├── app/
│   │   ├── routers/          lapisan HTTP (URL, validasi, status)
│   │   ├── services/         orkestrasi langkah + jembatan ke ai/
│   │   ├── schemas/          kontrak data Pydantic
│   │   └── core/             infrastruktur (koneksi database)
│   ├── db/init/              skema + data awal (auto-run)
│   ├── tests/
│   └── Dockerfile
│
├── ai/                       seluruh kecerdasan, lepas dari web
│   ├── perception/           LAPIS 1 — Model 1, 2, 4 + overlay
│   ├── reasoning/            LAPIS 2 — Model 5, 6
│   ├── simulator/            simulator neraca massa pabrik
│   ├── training/             skrip pelatihan (tidak masuk image)
│   ├── evaluation/           rule recovery · kalibrasi selang
│   ├── config/               coefficients.yaml + sitasinya
│   └── weights/              bobot model terlatih
│
├── data/samples/             foto contoh untuk pengujian
├── docs/                     catatan eksperimen & analisis kompetitor
├── scripts/                  utilitas CLI
└── docker-compose.yml
```

Pemisahan `ai/` dari `backend/` disengaja: arsitektur dua lapis dan
pemisahan AI–backend–frontend harus terbaca langsung dari struktur
folder, bukan hanya dari diagram.

---

## Dataset

Seluruh data citra berasal dari sumber publik berlisensi terbuka.

| Dataset                                             | Isi                                                                                    | Penggunaan                                                  |
| --------------------------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Oil Palm Fruit Bunch Piles (Nature Scientific Data) | Tumpukan TBS di bagian grading PKS Kalimantan Selatan, 6 kelas, format YOLO, CC-BY 4.0 | Pelatihan utama Model 1                                     |
| Ordinal Ripeness Dataset (Mendeley)                 | 4.728 citra, 5 tingkat kematangan, Kalimantan Tengah, beragam perangkat                | Pelatihan head ordinal & ketahanan lintas-kamera            |
| Outdoor FFB Ripeness (Data in Brief)                | Johor, Negeri Sembilan, Perak — Malaysia                                              | Uji domain adaptation (latih di Indonesia, uji di Malaysia) |
| Trase — Indonesia Palm Oil Mills                   | Lokasi, kepemilikan, kapasitas seluruh PKS Indonesia                                   | Analisis dampak & kelayakan adopsi (bukan pelatihan)        |

**Catatan metodologis.** Split train/val/test dilakukan **per tumpukan**,
bukan per gambar. Dataset utama dibangun dari video rotasi 360° sehingga
banyak frame nyaris identik; split per gambar akan menempatkan frame dari
tumpukan yang sama di train dan test sekaligus, membuat metrik melambung
secara palsu.

**Dataset yang sengaja tidak dipakai.** Dataset komunitas dari platform
anotasi terbuka dievaluasi tetapi tidak digunakan untuk pelatihan utama:
kualitas anotasinya bervariasi, banyak yang merupakan unggahan ulang
dataset akademik yang sama (risiko kebocoran), dan status lisensinya
sering tidak jelas.

**Data proses pabrik.** Data operasional harian PKS (hasil lab OER per
truk, parameter sterilisasi, catatan sengketa) tidak tersedia publik.
Lapis 2 karena itu diuji terhadap **simulator neraca massa** yang
dikalibrasi dengan koefisien terpublikasi — seluruh koefisien beserta
sitasinya ada di `ai/config/coefficients.yaml` sehingga dasar ilmiahnya
bisa diaudit dari satu berkas.

---

## Status Pengembangan

Repositori ini dalam pengembangan aktif. Status jujur per commit terakhir:

| Komponen | Status |
|---|---|
| Struktur proyek & Docker Compose | ✅ Selesai |
| Kerangka backend + koneksi database | ✅ Selesai |
| Kerangka frontend + proxy API | ✅ Selesai |
| Analisis dataset & pembangunan split sah | ✅ Selesai |
| Model 1 — detektor tandan (3 kelas struktural) | ✅ mAP@50 **0,955** |
| Head kematangan — penilaian per crop | ⚠️ akurasi **0,635** pada muatan campuran |
| Model 2 — komposisi seluruh muatan | ✅ cakupan **0,905**, selang di lantai teoretis |
| Model 4 — potensi minyak | ✅ 3 uji akal sehat LULUS |
| Simulator pabrik (6 swauji) | ✅ Selesai |
| Model 5 — neraca tiga baris | ✅ **19/19** uji lulus, galat penutupan 0,00e+00 |
| Model 6 — atribusi tanpa label | ✅ **4/5** aturan pulih, kosinus 0,93–0,9995 |
| Tata kelola koefisien (34 angka, 0 tanpa sumber) | ✅ audit SEHAT |
| Skema & data awal database | ⏳ Belum |
| Integrasi model ke backend | ⏳ Belum |
| Kartu neraca di antarmuka | ⏳ Belum |

### Temuan metodologis

**1. Split resmi dataset publik terbukti bocor sepenuhnya.** Seluruh 91 tumpukan
muncul di sisi latih, dan 88,7% gambar uji punya frame bersebelahan langsung di
sisi latih. Split pengganti berbasis tumpukan dibangun dan diverifikasi nol
kebocoran. Besaran inflasinya terukur:

| Metrik | Split jujur | Split resmi (bocor) | Inflasi |
|---|---|---|---|
| mAP@50-95 | 0,7892 | 0,8712 | **+10,4%** |
| Presisi | 0,8309 | 0,9942 | **+19,6%** |

**2. Komponen kematangan awalnya mengenali tumpukan, bukan membedakan tandan.**
Karena 66 dari 91 tumpukan hanya berisi satu tingkat kematangan, model dapat
lulus dengan mengenali adegan. Akurasinya jatuh dari 0,8365 pada tumpukan murni
ke 0,5160 pada tumpukan campuran — kondisi yang sebenarnya mewakili muatan truk.

Diperbaiki lewat rancangan faktorial 2×2:

| Metrik | Awal | **Setelah perbaikan** |
|---|---|---|
| Akurasi muatan campuran | 0,5160 | **0,6346** |
| Kesalahan ≥2 tingkat | 9,17% | **1,50%** |
| Selisih murni−campuran | 0,1178 | **0,0649** |

**3. Selang Model 2 berada tepat di lantai pencuplikan teoretis.** Dengan n
tandan terlihat dari muatan berisi ratusan, galat baku proporsi adalah
`sqrt(p(1-p)/n)` — batas yang tidak bisa dilewati siapa pun secara jujur. Rasio
lebar selang terhadap lantai itu: 0,999 / 1,017 / 1,122 / 1,010.

Artinya model sudah memeras seluruh informasi yang tersedia dan tidak mengaku
tahu lebih banyak. Konsekuensinya juga dinyatakan terbuka: **selang tidak bisa
dipersempit dengan arsitektur yang lebih canggih**, hanya dengan menambah sudut
kamera.

Nilainya pun tidak merata. Pada muatan yang **ditata sengaja** ia memulihkan
+19,3% atas pendekatan naif; pada muatan jujur hanya +2,0%. Model 2 adalah
mekanisme ketahanan terhadap penataan muatan, bukan penambah akurasi umum.

**4. Buah mentah terbukti tidak dihitung dua kali.** Klaim keadilan tidak boleh
berhenti sebagai paragraf, jadi ia diuji mekanis:

| Yang diperiksa | Hasil |
|---|---|
| Pergeseran sisi pabrik saat mutu buah memburuk 0→40% mentah | **0,00e+00 poin** |
| Kekekalan pemasok + tak terjelaskan | 2,66e-15 poin |
| Pergeseran tagihan pemasok saat koefisien pabrik meleset ±15% | **0,000 poin** |

Baris terakhir adalah sifat keadilan yang paling penting: ketika angka pabrik
salah, yang bergeser adalah baris pabrik dan baris tak terjelaskan — bukan
tagihan petani.

**5. Model 6 menemukan kembali aturan yang tidak pernah diberitahukan padanya.**
Simulator menanam lima jenis kerusakan; Model 6 hanya melihat delapan hasil ukur
laboratorium per hari, tanpa label. Empat dari lima pulih dengan kosinus
0,931–0,9995 (pemasangan Hungarian, bukan "ambil yang termirip").

Yang kelima gagal, dan sebabnya bisa dihitung: `sludge_separator_tersumbat`
berimpit tanda tangannya dengan `cst_dingin`. Tidak ada metode tanpa label yang
bisa memisahkan dua sebab yang meninggalkan jejak sama — batasnya ada di
datanya, bukan di modelnya.

Ketahanannya juga diukur, dan arah kegagalannya benar: saat derau laboratorium
naik ke 22%, yang memburuk lebih dulu adalah hari rusak yang terlewat (0% →
19,4%), bukan tuduhan palsu. Sistem jadi pendiam, bukan jadi asal tuduh.

**Riwayat minimum yang dibutuhkan: 120 hari giling.** Di bawah itu modul
atribusi belum layak menunjuk sebab, dan sistem hanya menyajikan neraca.

Dua intervensi yang diuji **gagal dan dilaporkan gagal**: memotong tepi crop
sendirian justru merugikan, dan augmentasi agresif menghancurkan sinyal.
Struktur ordinal CORAL juga kalah dari cross-entropy, dan hipotesis
penyebabnya diuji lewat varian berkapasitas 256× lalu terbantah.

Rincian lengkap beserta notebook yang dapat dijalankan ulang ada di
[`docs/experiments.md`](docs/experiments.md).

---

## Batasan

Disebutkan di muka, bukan disembunyikan:

- **Kalibrasi ke hasil lab OER aktual belum tervalidasi lapangan.**
  Loop kalibrasi hanya dapat disimulasikan karena data pabrik nyata tidak
  publik.
- **Parameter proses pabrik nyata tidak tersedia**, sehingga usulan
  setelan proses otomatis (Model 7) berstatus tahap lanjutan, bukan klaim
  saat ini.
- **Dampak terhadap keadilan bagi petani dapat diargumentasikan, belum
  dibuktikan** dengan angka lapangan.
- **Sistem ini menyentuh satu penyebab rendemen rendah** — buah mentah
  yang masuk dan proses yang tidak optimal. Selisih menuju potensi 25–27%
  sebagian besar adalah soal bibit dan manajemen kebun, di luar jangkauan
  sistem ini. Kami tidak mengklaim menyelesaikan seluruh masalah rendemen.
- **Angka potensi kerugian nasional bersifat teoretis.** Yang realistis
  direbut adalah sebagian kecilnya; perhitungan lengkap beserta asumsinya
  disertakan dalam proposal.

---

## Roadmap

Dirancang dalam arsitektur, tidak dibangun pada tahap ini:

- **Model 3 — Deteksi muatan tersusun.** Menandai muatan yang sebaran
  mutunya terlalu rapi untuk terjadi secara alami. *Prasyarat wajib:*
  harus disertai pasangan simetrisnya yang mengawasi sisi pabrik
  (misalnya grader yang sistematis menilai lebih rendah, atau loss
  terukur yang tidak masuk akal secara fisika). Tanpa itu, sistem hanya
  mengawasi petani dan tesis "menunjuk dua arah" runtuh.
- **Model 7 — Usulan setelan proses per muatan.** Muatan dengan 20% buah
  mentah membutuhkan perlakuan berbeda dari muatan 95% matang.
- **Model 8 — Umpan balik agronomi ke petani.** Mengubah interaksi dari
  menghukum (potongan) menjadi membantu (rekomendasi interval panen).
- **Model 9 — Deteksi anomali tak terjelaskan.** Kebocoran peralatan,
  timbangan tidak terkalibrasi, kesalahan pengukuran.
- **Sertifikat sortasi digital** untuk petani: foto bukti, rincian per
  kategori dengan selang, dan dasar perhitungan potongan yang bisa
  dihitung ulang secara mandiri.

---

## Lisensi

Lihat berkas [LICENSE](LICENSE).

Dataset yang digunakan berlisensi CC-BY 4.0 dan disitasi pada bagian
[Dataset](#dataset). Ketentuan lisensi pustaka pihak ketiga mengikuti
lisensi masing-masing sebagaimana tercantum di `backend/requirements.txt`
dan `frontend/package.json`.
