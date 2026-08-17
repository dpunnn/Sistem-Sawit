# Catatan Eksperimen — Neraca Minyak

Dokumen ini adalah sumber angka untuk proposal. Setiap angka berasal dari
notebook yang bisa dijalankan ulang, bukan dari ingatan.

| Notebook | Isi |
|---|---|
| `01_eda_piles.ipynb` | Karakter dataset tumpukan |
| `02_split_per_tumpukan.ipynb` | Bukti kebocoran + pembangunan split sah |
| `03_eda_ordinal.ipynb` | Karakter dataset ordinal + jarak domain |
| `04_train_detektor.ipynb` | Pelatihan & evaluasi detektor |
| `05_train_head_ordinal.ipynb` | Pelatihan & evaluasi head kematangan |
| `06_perbaikan_jalan_pintas.ipynb` | Faktorial 2×2 menutup jalan pintas konteks |

---

## 1. Karakter dataset tumpukan

Sumber: *Annotated Datasets of Oil Palm Fruit Bunch Piles for Ripeness
Grading* (Scientific Data, 2023), PKS Kalimantan Selatan, CC-BY 4.0.

| Besaran | Nilai |
|---|---|
| Gambar | 4.160 |
| Kotak anotasi | **14.558** |
| Tumpukan unik | **91** |
| Frame per tumpukan | median 39 · rata-rata 45,7 · maksimum **421** |
| Objek per gambar | median 4 · maksimum 10 · tanpa anotasi: 0 |
| Resolusi | 416 × 416 (seragam) |

### Catatan verifikasi angka
Publikasi menyebut **14.559** objek; penghitungan langsung atas berkas label
menghasilkan **14.558**. Selisih satu kotak. Angka yang dipakai adalah hasil
penghitungan sendiri.

Publikasi juga menyebut 7.171 citra beranotasi, sedangkan paket yang tersedia
berisi 4.160 — yaitu subset yang dipakai penulis untuk split 70/20/10
(2.908 + 835 + 417). Kedua angka konsisten dan merujuk hal berbeda.

### Distribusi kelas

| Kelas | Kotak | % |
|---|---|---|
| TBS masak | 2.973 | 20,42 |
| TBS mentah | 2.913 | 20,01 |
| Terlalu masak | 2.641 | 18,14 |
| TBS abnormal | 2.599 | 17,85 |
| Kurang masak | 2.575 | 17,69 |
| Janjang kosong | 857 | 5,89 |

Lima kelas berimbang (17,7–20,4%); hanya `Janjang kosong` minoritas.

### Geometri objek — membantah asumsi awal

| Kategori COCO | Proporsi |
|---|---|
| large (>96²) | **84,5%** |
| medium (32²–96²) | 15,5% |
| small (<32²) | **0,0%** |

Rasio lebar/tinggi median 1,11 (p5 0,78 · p95 1,96).

**Implikasi:** kekhawatiran bahwa resolusi 416×416 membatasi deteksi objek
kecil tidak terbukti. Resolusi ini memadai. Tidak ada alasan mengejar
resolusi lebih tinggi, dan hal ini **tidak** dicantumkan sebagai keterbatasan.

### Struktur tumpukan

| Kelompok | Tumpukan | Frame | Berkelas tunggal |
|---|---|---|---|
| framesawit | 42 | 1.677 | 19 |
| framementah | 20 | 685 | **20** |
| frame | 12 | 465 | **12** |
| frame10kombinasi | 1 | **421** | 0 |
| frame9kombinasi | 1 | **362** | 0 |
| frameterlalumasak | 9 | 356 | **9** |
| framekurangmasak | 6 | 194 | **6** |

Dua temuan:

1. **66 dari 91 tumpukan hanya berisi satu tingkat kematangan.** Sebagian besar
   dataset bukan muatan truk alami, melainkan rekaman terkurasi per tingkat.
2. **Dua tumpukan "kombinasi" menyimpan 783 frame — 18,8% seluruh dataset** —
   dan justru keduanya yang paling menyerupai muatan campuran sungguhan.

---

## 2. Kebocoran split resmi

### Bukti kuantitatif

| Irisan | Tumpukan |
|---|---|
| train ∩ valid | **91 dari 91** |
| train ∩ test | **87 dari 87** |
| valid ∩ test | **87 dari 87** |

Seluruh tumpukan di sisi validasi dan uji juga ada di sisi latih.

Ukuran yang lebih menjelaskan parahnya:

| | |
|---|---|
| Median jarak frame terdekat ke sisi latih | **1** |
| Gambar uji dengan frame bersebelahan di sisi latih | **370 / 417 (88,7%)** |

Sisi uji bukan sekadar berisi tumpukan yang sama — melainkan **momen yang
sama**. Untuk model, itu praktis gambar yang sama.

### Split pengganti

Pembagian pada tingkat tumpukan, distratifikasi menurut kelompok, sadar bobot
frame. Karena 66 tumpukan berkelas tunggal, keseimbangan kelas sempurna
**tidak mungkin secara struktural**. Yang dilakukan: 300 seed diuji, 110
memenuhi seluruh kendala, lalu dipilih divergensi Jensen-Shannon terkecil.

| | seed pertama (42) | **terpilih (274)** |
|---|---|---|
| Divergensi JS | 0,2189 | **0,1092** |
| `TBS abnormal` di val | 9,9% | **19,4%** |
| `Kurang masak` di val | 31,0% | **15,8%** |

### Hasil akhir

```
train : 3.037 gambar (73,0%) | 62 tumpukan (43 murni / 19 campuran) | 10.290 kotak
val   :   575 gambar (13,8%) | 15 tumpukan (13 murni /  2 campuran) |  2.313 kotak
test  :   548 gambar (13,2%) | 14 tumpukan (10 murni /  4 campuran) |  1.955 kotak

kebocoran tumpukan : 0     kelas hilang : 0
```

### Keterbatasan yang tersisa
`TBS mentah` tetap lebih terwakili di sisi uji (27,3%) daripada latih (17,2%);
`TBS masak` sebaliknya (12,5% vs 23,4%). Konsekuensi langsung struktur dataset.
**Metrik per kelas wajib dilaporkan terpisah; rata-rata makro lebih
representatif daripada mikro.**

---

## 3. Karakter dataset ordinal

Sumber: *An Ordinal Dataset for Ripeness Level Classification*,
Kalimantan Tengah.

| Tingkat | Citra |
|---|---|
| 0 Immature | 758 |
| 1 PartiallyRipe | 1.405 |
| 2 FullyRipe | 1.489 |
| 3 OverRipe | 665 |
| 4 Decayed | 411 |

| | |
|---|---|
| Total | 4.728 |
| Ketimpangan terbesar/terkecil | 3,62× |
| Resolusi | **256 × 256 seragam**, simpangan baku 0 |
| Rasio aspek | **1,00 tepat** |
| Split resmi | 69,9 / 14,9 / 15,2 — **nol irisan berkas** |

### Jarak domain ke kondisi kerja

| | Dataset ordinal | Crop dari tumpukan |
|---|---|---|
| Resolusi | 256 px seragam | dari citra 416 px, bervariasi |
| Rasio aspek | 1,00 tepat | median 1,11 · rentang 0,78–1,96 |
| Latar | bersih | terhalang tandan lain |

**Implikasi:** pra-latih di dataset ini **wajib** disusul penyesuaian pada crop
asli, dan augmentasi pra-latih harus meniru kerusakan crop — termasuk
**distorsi rasio aspek**, justru karena semua citra sumber persegi sempurna.

### Peringatan
Nama berkas tidak menyimpan penanda sumber, sehingga kebocoran tingkat sesi
pemotretan **tidak dapat dikesampingkan**. Angka dari dataset ini
diperlakukan sebagai indikator pra-latih, bukan klaim performa.

---

## 4. Detektor tandan

### Rancangan
Tiga kelas struktural, bukan enam kelas asli:

| Kelas | Isi | Kotak (total) |
|---|---|---|
| `tandan` | empat tingkat kematangan, dilebur | 11.102 |
| `janjang_kosong` | — | 857 |
| `abnormal` | — | 2.599 |

Alasan peleburan: memusatkan sinyal (kelas `tandan` naik dari ~2.400 jadi
7.838 kotak di sisi latih) dan menghapus persoalan `class_id` alfabetis dari
detektor. Tingkat kematangan ditangani head ordinal terpisah.

### Konfigurasi
`yolov8s` · imgsz 416 · 60 epoch (berhenti dini di **58**) · patience 15 ·
batch 16 · seed 42 · augmentasi pencahayaan diperkuat (hsv_v 0,5).

### Hasil — Eksperimen A (split per tumpukan)

| Metrik | Nilai |
|---|---|
| mAP@50 | **0,9550** |
| mAP@50-95 | **0,7892** |
| Presisi | 0,8309 |
| Recall | 0,9397 |

| Kelas | Presisi | Recall | mAP@50 | mAP@50-95 | Dukungan uji |
|---|---|---|---|---|---|
| tandan | 0,932 | 0,993 | 0,992 | 0,853 | 1.484 |
| janjang_kosong | 0,680 | 1,000 | 0,973 | 0,828 | 148 |
| abnormal | 0,881 | 0,827 | 0,901 | 0,686 | 323 |

`abnormal` paling sulit — wajar untuk kategori sisa yang bentuknya beragam.
`janjang_kosong` recall sempurna tetapi presisi 0,680: model menemukan
semuanya tetapi sering salah tuduh, konsisten dengan dukungan uji yang kecil.

### Hasil — Eksperimen B (split resmi, bocor)

| Metrik | Nilai |
|---|---|
| mAP@50 | 0,9948 |
| mAP@50-95 | 0,8712 |
| Presisi | 0,9942 |
| Recall | 0,9916 |

### Inflasi akibat kebocoran

| Metrik | Split jujur | Split bocor | Inflasi |
|---|---|---|---|
| mAP@50 | 0,9550 | 0,9948 | **+4,2%** |
| mAP@50-95 | 0,7892 | 0,8712 | **+10,4%** |
| **Presisi** | 0,8309 | 0,9942 | **+19,6%** |
| Recall | 0,9397 | 0,9916 | +5,5% |

> Memakai split resmi menghasilkan mAP@50-95 yang **10,4% lebih tinggi** dan
> presisi **19,6% lebih tinggi** daripada evaluasi pada tumpukan yang
> benar-benar belum pernah dilihat. Selisih itu bukan performa — itu hafalan.

### Uji risiko jalan pintas

| Kelompok uji | mAP@50 | mAP@50-95 |
|---|---|---|
| Tumpukan murni | 0,9383 | 0,7665 |
| Tumpukan campuran | 0,9908 | 0,8359 |

Hipotesisnya: jika model mengandalkan pengenalan *adegan*, tumpukan berkelas
tunggal justru lebih mudah. Hasilnya kebalikan — tumpukan murni lebih sulit.
**Tidak ada bukti model mengandalkan jalan pintas tingkat adegan.**

Catatan kehati-hatian: detektor ini tidak menilai kematangan sama sekali
(hanya tiga kelas struktural), sedangkan pembagian murni/campuran
didefinisikan dari komposisi kematangan. Uji ini lebih relevan untuk head
ordinal daripada untuk detektor.

---

## 5. Head ordinal

### Rancangan
Backbone ResNet-18 (ImageNet) dipra-latih dengan cross-entropy pada 4.728 citra
buah tunggal 5 tingkat, lalu tiga varian head disesuaikan pada 11.102 crop dari
tumpukan (4 tingkat) **dari titik awal backbone yang identik**, supaya yang
diuji benar-benar fungsi loss-nya.

Augmentasi pra-latih sengaja meniru kerusakan crop: distorsi rasio aspek,
penurunan-lalu-penaikan resolusi, pengaburan, penghapusan acak.

### Hasil pada seluruh crop uji

| Varian | Akurasi | MAE indeks | Salah ≥2 tingkat | Parameter head |
|---|---|---|---|---|
| **CE** | **0,7352** | **0,3181** | **5,19%** | 2.052 |
| CORAL | 0,6213 | 0,4589 | 7,35% | 515 |
| CORAL+MLP | 0,6213 | 0,4508 | 6,67% | 131.587 |

**CORAL kalah, dan hipotesis penyebabnya terbantah.** Dugaan awal: CORAL baku
memampatkan 512 dimensi fitur menjadi satu skor, sehingga kapasitas kepalanya
hanya seperempat CE (hambatan rank-1). Varian CORAL+MLP menguji itu dengan
menambah kapasitas **256×** sambil mempertahankan jaminan urutan — hasilnya
hanya membaik 1,8% pada MAE dan akurasinya sama persis. Kapasitas bukan
penyebabnya; pada data ini struktur ordinal berjenjang memang merugikan.

Head yang dipakai: **CE**. Hasil negatif dilaporkan apa adanya.

### Temuan utama — model mengenali tumpukan, bukan membedakan tandan

| Varian | Kelompok | Akurasi | MAE indeks | Salah ≥2 tingkat |
|---|---|---|---|---|
| CE | murni | 0,8365 | 0,1980 | 3,35% |
| **CE** | **campuran** | **0,5160** | **0,5778** | 9,17% |
| CORAL | murni | 0,7931 | 0,2571 | 4,14% |
| **CORAL** | **campuran** | **0,2495** | **0,8955** | 14,29% |
| CORAL+MLP | murni | 0,8000 | 0,2345 | 2,76% |
| **CORAL+MLP** | **campuran** | **0,2345** | **0,9190** | 15,14% |

Dengan empat kelas, tebakan acak = 0,25.

> Kedua varian CORAL pada tumpukan campuran berada di **0,2495 dan 0,2345 —
> setara tebakan acak**. Pada kasus yang paling menyerupai muatan truk
> sungguhan, keduanya praktis tidak mempelajari apa pun yang dapat dipindahkan.
> CE bertahan lebih baik (0,5160) tetapi tetap runtuh dari 0,8365.

**Mekanismenya.** 66 dari 91 tumpukan hanya berisi satu tingkat kematangan.
Crop dipotong dengan padding 10%, sehingga membawa latar, pencahayaan, sudut
kamera, dan potongan tandan tetangga. Petunjuk itu cukup untuk mengenali
tumpukan mana yang sedang dilihat — dan karena mayoritas tumpukan berkelas
tunggal, mengenali tumpukan sama saja dengan mengetahui labelnya.

**Kejujuran metodologis.** Sebagian selisih bersifat bawaan: pada tumpukan
murni semua crop berlabel sama, sehingga menebak satu kelas dominan sudah benar
untuk seluruh tumpukan. Tetapi angka 0,2345–0,2495 pada tumpukan campuran tidak
dapat dijelaskan oleh kemudahan tugas — itu batas tebakan acak.

### Jarak domain terukur

| Tahap | Akurasi validasi |
|---|---|
| Pra-latih, citra buah tunggal bersih | 0,9119 |
| Setelah penyesuaian, crop dari tumpukan | ~0,70 |

### Arah perbaikan, menurut urutan biaya
1. Latih ulang hanya pada 25 tumpukan campuran — jalan pintas tidak lagi berbuah
2. Padding crop nol, hapus konteks tepi
3. Augmentasi perusak latar (penggantian latar, pemotongan agresif)
4. Kumpulkan tumpukan campuran tambahan — akar masalahnya komposisi dataset,
   bukan arsitektur

---

## 6. Menutup jalan pintas konteks

### Perancu yang harus diakui lebih dulu

V0 di Notebook 06 memakai konfigurasi yang **seharusnya** sama dengan CE di
Notebook 05, tetapi hasilnya berbeda jauh:

| | Akurasi tumpukan campuran |
|---|---|
| Notebook 05, CE | 0,5160 |
| Notebook 06, V0 | **0,6674** |

Penyebabnya ditelusuri: **Notebook 05 tidak memakai pembobotan kelas pada tahap
penyesuaian**, hanya pada pra-latih. Notebook 06 memakainya di kedua tahap.

Satu perubahan yang bahkan tidak termasuk rancangan eksperimen — pembobotan
kelas berbanding terbalik dengan frekuensi — menaikkan akurasi pada tumpukan
campuran **+0,151 (naik 29% relatif)**, lebih besar daripada seluruh intervensi
yang sengaja dirancang.

Masuk akal dari komposisinya: pada crop tumpukan campuran, kelas `mentah` hanya
8% data latih. Tanpa pembobotan, model belajar mengabaikan kelas minoritas —
dan justru kelas itu yang paling menentukan potongan pembayaran petani.

### Rancangan faktorial

| | Semua tumpukan | Hanya tumpukan campuran |
|---|---|---|
| Padding +10% | V0 (dasar) | V2 |
| Inset −10% | V1 | V3 |

Ditambah V4 = inset + campuran + augmentasi kuat.

Dua intervensi diuji terpisah supaya dapat diketahui mana yang benar-benar
bekerja, bukan sekadar "dicoba semuanya lalu membaik".

### Hasil

| Varian | Crop latih | Akurasi campuran | MAE campuran | Salah ≥2 tingkat | Selisih murni−campuran |
|---|---|---|---|---|---|
| **V0** dasar | 7.838 | **0,6674** | 0,4179 | 8,32% | 0,1178 |
| V1 inset, semua | 7.835 | 0,5919 | 0,4573 | 4,70% | 0,1717 |
| V2 pad+10, campuran | 3.417 | 0,5586 | 0,4648 | 2,13% | **−0,0503** |
| **V3** inset, campuran | 3.417 | 0,6346 | **0,3825** | **1,50%** | 0,0649 |
| V4 + aug kuat | 3.417 | 0,5427 | 0,5449 | 8,55% | 0,1903 |

### Yang bekerja

**Melatih hanya pada tumpukan campuran menutup jalan pintas.** Selisih
murni−campuran turun dari 0,1178 (V0) ke 0,0649 (V3), dan pada V2 bahkan
**negatif** (−0,0503) — performa pada tumpukan campuran melampaui tumpukan
murni. Itu bukti terkuat model tidak lagi mengandalkan pengenalan tumpukan.

Biayanya: data latih separuh (7.838 → 3.417 crop, 57 → 19 tumpukan).

### Yang tidak bekerja

**Inset saja justru merugikan.** V1 lebih buruk daripada V0 di hampir semua
metrik, dan selisihnya melebar (0,1178 → 0,1717). Memotong 10% ke dalam kotak
tidak hanya membuang latar — ia juga membuang bagian tandan. Hipotesis
"konteks tepi adalah sumber jalan pintas" **tidak terkonfirmasi** saat diuji
sendirian.

**Augmentasi kuat merugikan.** V4 paling buruk pada akurasi campuran dan
selisih. Pemotongan acak sampai 45% dan penghapusan 25% area menghancurkan
sinyal kematangan, bukan hanya konteksnya.

**Inset hanya berguna saat digabung dengan campuran.** V3 mengalahkan V2 di
semua metrik. Efeknya bersifat interaksi, bukan aditif — persis alasan
rancangan faktorial dipakai.

### Varian yang dipilih: V3, bukan yang akurasinya tertinggi

| | V0 | V3 |
|---|---|---|
| Akurasi campuran | **0,6674** | 0,6346 |
| MAE indeks | 0,4179 | **0,3825** |
| **Salah ≥2 tingkat** | 8,32% | **1,50%** |

V0 lebih sering tepat, tetapi V3 **5,5× lebih jarang salah jauh**. Untuk sistem
yang keluarannya memotong pembayaran petani, salah dua tingkat jauh lebih
merugikan daripada salah satu tingkat — dan itu alasan MAE indeks dipilih
sebagai metrik utama sejak awal. Menukar 3,3 poin akurasi untuk memangkas
kesalahan berat dari 8,32% ke 1,50% adalah pertukaran yang tepat.

Bobot: `ai/weights/head_ordinal_v3_inset_campuran.pt`

### Angka final komponen kematangan

| Metrik | Awal (nb05) | **Final (V3)** |
|---|---|---|
| Akurasi muatan campuran | 0,5160 | **0,6346** |
| MAE indeks | 0,5778 | **0,3825** |
| Kesalahan ≥2 tingkat | 9,17% | **1,50%** |
| Selisih murni−campuran | 0,1178 | **0,0649** |

Perbaikannya nyata, tetapi komponen ini **tetap belum layak menjadi dasar
keputusan finansial otomatis**. Akurasi 0,63 pada empat kelas menyisakan
sepertiga kesalahan. Penempatannya pada ambang tindakan: **keyakinan sedang** —
cukup untuk bahan diskusi dan pemeriksaan, belum cukup untuk memotong
pembayaran.

### Yang tidak bisa diselesaikan dari sisi model

Akar masalahnya komposisi dataset: hanya 25 tumpukan campuran, 19 dipakai
latih, dengan dua rekaman besar mendominasi. Menambah tumpukan campuran adalah
satu-satunya jalur yang menyentuh akar — pekerjaan pengambilan data lapangan,
bukan pekerjaan arsitektur.

---

## Ringkasan klaim yang boleh dibuat

1. Split resmi dataset publik yang dipakai **terbukti bocor sepenuhnya**, dan
   besaran inflasinya terukur (+10,4% mAP@50-95, +19,6% presisi).
2. Split pengganti berbasis tumpukan dibangun, diverifikasi nol kebocoran,
   dan dipilih dari 110 kandidat yang memenuhi kendala.
3. Detektor mencapai mAP@50 0,955 pada 14 tumpukan yang belum pernah dilihat,
   dan **tidak** menunjukkan indikasi jalan pintas (justru sedikit lebih baik
   pada tumpukan campuran).
4. Struktur ordinal CORAL diuji dan **kalah** dari cross-entropy; hipotesis
   penyebabnya (hambatan rank-1) diuji lewat varian berkapasitas 256× dan
   terbantah.
5. Komponen kematangan **terbukti mengandalkan jalan pintas tingkat tumpukan**:
   akurasinya jatuh dari 0,8365 pada tumpukan murni ke 0,5160 pada tumpukan
   campuran — dan varian CORAL jatuh sampai setara tebakan acak.
6. Jalan pintas itu **berhasil ditutup sebagian** lewat rancangan faktorial:
   melatih hanya pada tumpukan campuran menurunkan selisih murni−campuran dari
   0,1178 ke 0,0649, dan menaikkan akurasi muatan campuran 0,5160 → 0,6346
   dengan kesalahan berat turun 9,17% → 1,50%.
7. Dua intervensi yang diuji **gagal dan dilaporkan gagal**: memotong tepi crop
   sendirian justru merugikan, dan augmentasi agresif menghancurkan sinyal.

## Yang TIDAK boleh diklaim

- Bahwa model ini lebih akurat daripada sistem komersial mana pun — kita
  memakai data publik, mereka memakai data pabrik nyata.
- Bahwa 91 tumpukan cukup untuk menyimpulkan performa di seluruh Indonesia.
- Bahwa angka pada dataset ordinal mencerminkan performa akhir — kebocoran
  tingkat sesi di dataset itu tidak dapat dikesampingkan.
- **Bahwa penilaian kematangan sudah siap pakai.** Angka gabungan menyesatkan
  karena didominasi tumpukan berkelas tunggal. Angka yang jujur untuk kondisi
  muatan truk nyata adalah **0,6346**, dan komponen ini ditempatkan pada
  ambang **keyakinan sedang** — bahan diskusi, bukan dasar potongan pembayaran.
- Bahwa perbaikan jalan pintas sudah tuntas. Selisih murni−campuran mengecil
  tetapi belum nol; akar masalahnya komposisi dataset, bukan arsitektur.
