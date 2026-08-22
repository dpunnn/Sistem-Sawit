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

## 7. Komposisi muatan dari permukaan (Model 2)

Persoalannya bukan klasifikasi melainkan **inferensi statistik di bawah
observasi parsial**: menaksir komposisi seluruh muatan dari lapisan permukaan
yang terlihat kamera. Dua sumber ketidakpastiannya berbeda sifat, dan hanya
satu yang bisa dikurangi.

### Kenapa datanya harus dibuat sendiri

Kebenaran "komposisi seluruh muatan" tidak ada di dataset mana pun. Mengukurnya
berarti membongkar dan menyortir satu truk penuh secara manual. Jalan keluarnya:
menyusun 45.000 muatan buatan dari 11.102 crop tandan **berlabel nyata**,
sehingga komposisi sebenarnya diketahui sempurna.

Dua mekanisme bias dimodelkan: tandan besar tenggelam (penumpukan) dan buah
bagus ditaruh di atas (penataan sengaja). Yang pertama dasar empirisnya lemah
dan disebut demikian - ukuran kotak antar tingkat kematangan hanya berselisih
11% (rasio 1,114). Karena itu kekuatannya diacak termasuk nol, dan ketahanan
model terhadap kesalahan asumsi ini diuji terpisah.

### Lantai pencuplikan - batas yang tidak bisa dilewati siapa pun

Dengan n tandan terlihat dari muatan berisi ratusan, galat baku proporsi adalah
`sqrt(p(1-p)/n)`. Model yang melaporkan selang lebih sempit dari itu bukan
pintar, melainkan berbohong. Nilai tambah Model 2 adalah mengoreksi **bias**,
bukan mengecilkan ragam.

### Hasil

| Ukuran | Nilai |
|---|---|
| MAE proporsi | 0,0548 |
| MAE pendekatan naif (permukaan apa adanya) | 0,0605 |
| Perbaikan relatif | +9,3% |
| Cakupan selang 90% sebelum kalibrasi | 0,8726 |
| Cakupan setelah kalibrasi conformal (CQR) | **0,9046** |
| Rasio lebar selang terhadap lantai pencuplikan | 0,999 / 1,017 / 1,122 / 1,010 |

Rasio mendekati 1,0 di seluruh tingkat berarti model berada tepat di lantai
teoretis: sudah memeras seluruh informasi yang tersedia, dan tidak mengaku tahu
lebih banyak. Konsekuensinya juga harus dinyatakan - **selang tidak bisa
dipersempit dengan arsitektur yang lebih canggih**, hanya dengan menambah
jumlah tandan yang terlihat.

### Di mana nilainya terkonsentrasi

| Karakter muatan | Perbaikan atas pendekatan naif |
|---|---|
| Ditata sengaja | **+19,3%** |
| Tidak ditata (jujur) | +2,0% |

Model 2 bukan penambah akurasi umum melainkan **mekanisme ketahanan terhadap
penataan muatan**. Pada muatan jujur koreksinya nyaris nihil - dan memang
seharusnya begitu.

### Ketahanan terhadap asumsi yang lemah

MAE dipecah menurut kekuatan mekanisme tenggelam, termasuk nol: 0,0549 /
0,0551 / 0,0546. Rentangnya 0,00048, atau 0,88% dari MAE rerata. Model tidak
bergantung pada asumsi yang dasar empirisnya tipis.

---

## 8. Potensi minyak dan neraca tiga baris (Model 4 & 5)

### Tata kelola koefisien

Setiap angka domain wajib punya `sumber` dan `status`. Loader menolak koefisien
tanpa sumber, dan menolak koefisien berstatus `perlu_verifikasi` kecuali
diizinkan secara eksplisit. Audit terakhir: **34 koefisien, 0 tanpa sumber,
22 terverifikasi, 12 perlu verifikasi - SEHAT**.

### Kesalahan satuan yang tertangkap tata kelola

Nilai kehilangan minyak dari studi kasus (kondensat 1,83 ... underflow CST
7,04) sempat dicatat bersatuan `persen_terhadap_tbs`. Dibaca begitu, totalnya
18,01 dan rendemen akhir jatuh ke ~3% - mustahil. Angka itu sebenarnya **kadar
minyak di dalam aliran** (persen terhadap contoh), dan harus dikalikan nisbah
massa aliran terhadap TBS untuk menjadi poin rendemen.

Nisbah massanya sendiri taksiran teknik, bukan kutipan terbit, dan berstatus
`perlu_verifikasi`. Yang membuatnya layak dipakai sementara: jumlah kadar x
nisbah mendarat di **1,670 poin**, sesuai norma industri 1,5-1,75 poin untuk
pabrik terkelola baik.

### Model 4 - uji akal sehat

| Uji | Hasil |
|---|---|
| Muatan 100% matang | 21,00 poin - LULUS |
| Muatan 100% mentah | 8,00 poin - LULUS |
| Monoton menurun terhadap proporsi mentah | LULUS |

Disiplin koefisien terlihat dampaknya: pada muatan dengan 20% buah non-masak,
mode `terverifikasi` melaporkan 1.182 kg sedangkan mode `lengkap` 1.144 kg.
Selisih itu bukan galat melainkan penolakan memakai dua penalti yang belum
tertelusur. Arah kesalahannya disengaja - kalau ragu, jangan merugikan petani.

### Model 5 - kenapa tiga baris, bukan dua

Neraca dua baris membuat buah mentah dihitung **dua kali**: sekali karena
menurunkan kandungan minyak yang masuk, sekali lagi karena pabrik yang
memproses buah mentah memang mencatat kehilangan lebih tinggi. Baris tengah
(potensi realistis) memutus rantai itu.

Sifat tersebut diuji mekanis, bukan diyakini:

| Yang diperiksa | Hasil |
|---|---|
| Galat penutupan aritmetika | 0,00e+00 |
| Pergeseran sisi pabrik saat mutu buah memburuk 0-40% mentah | **0,00e+00 poin** |
| Kekekalan pemasok + tak terjelaskan | 2,66e-15 poin |
| Sisa tak terjelaskan saat koefisien sama persis dengan simulator | tepat 0,000 |
| Jumlah uji lulus | 19/19 |

Sisa tepat nol pada mode lengkap membuktikan aritmetikanya eksak - sehingga
2,005 poin yang muncul di mode terverifikasi benar-benar berasal dari koefisien
yang ditolak, bukan dari salah hitung.

### Simulator pabrik

Data proses harian pabrik tidak publik. Simulator deterministik dan seedable
menggantikannya, dengan enam swauji yang harus lolos sebelum boleh dipakai -
termasuk pemeriksaan silang bahwa rugi komposisi identik dengan Model 4.

Pemeriksaan itu menangkap kesalahan nyata: konvensi penalti kematangan sempat
meleset **100x** (fraksi vs persen), dan neraca tetap terlihat masuk akal karena
angkanya kebetulan mendarat dekat rendemen petani swadaya yang terpublikasi.

### Pertentangan antar koefisien terbit yang harus disebut

Supaya neraca menutup tepat di rendemen TBS petani swadaya yang terpublikasi
(18,88 poin), buah mentah harus hanya **3,5%** dan sisanya sempurna. Laporan
lapangan menyebut 10-15%. Selisih itu nyata, berasal dari koefisien terbit yang
saling bertentangan, dan justru itulah yang dilaporkan Model 5 sebagai bagian
tak terjelaskan - bukan disembunyikan dengan menyetel salah satu angka.

---

## 9. Atribusi tanpa label dan pemulihan aturan (Model 6)

### Kenapa tanpa label

Di pabrik nyata label kerusakan tidak ada; tidak ada operator yang mencatat
"hari ini sterilizer kurang tekanan" dalam bentuk yang bisa dilatih. Metode
yang butuh label hanya bisa didemokan, tidak bisa dipasang. Model 6 hanya
melihat delapan hasil ukur laboratorium per hari.

Ia harus menentukan sendiri berapa banyak pola kerusakan yang ada (lewat
siluet, bukan ditetapkan), memulihkan bentuk tiap pola, menamai hari
berikutnya, dan mengaku tidak tahu ketika polanya tidak cocok dengan apa pun.

### Cara mengukurnya

Tiap gangguan yang ditanam punya tanda tangan sebenarnya berupa vektor arah
kenaikan delapan aliran. Pola temuan juga vektor arah. Kecocokannya diukur
dengan kosinus, lalu **dipasangkan satu-satu memakai Hungarian** - tanpa itu,
satu pola bagus bisa diklaim sebagai keberhasilan untuk lima gangguan sekaligus.

### Hasil

| Gangguan ditanam | Pola temuan | Kosinus | Pulih |
|---|---|---|---|
| perebusan_kurang_matang | naik janjang+ampas | 0,9976 | ya |
| perebusan_berlebih | naik kondensat | 0,9995 | ya |
| kempa_aus | naik nut+ampas | 0,9992 | ya |
| cst_dingin | naik sludge+underflow | 0,9307 | ya |
| sludge_separator_tersumbat | - | 0,0042 | **tidak** |

Siluet kelompok 0,837. Salah tuduh hari normal 5,1%; hari rusak terlewat 0,0%.

Dua arah acak di ruang delapan dimensi rata-rata berkosinus nol dengan simpangan
sekitar 0,35 - kosinus 0,93-0,9995 terhadap pola yang tidak pernah diperlihatkan
bukan kebetulan.

### Kegagalan yang punya sebab, bukan misteri

`sludge_separator_tersumbat` dan `cst_dingin` sama-sama menaikkan sludge
separator dan fat pit; kosinus antar tanda tangan aslinya sudah di atas 0,5.
Tidak ada metode tanpa label yang bisa memisahkan dua sebab yang meninggalkan
jejak sama. Batasnya ada di datanya, bukan di modelnya - menembusnya butuh
sensor tambahan, bukan lapisan jaringan tambahan.

### Ketahanan

| Derau ukur | Pola | Pulih | Kosinus rerata | Salah tuduh | Terlewat |
|---|---|---|---|---|---|
| 0,06 | 6 | 4 | 0,786 | 5,1% | 0,0% |
| 0,10 | 6 | 4 | 0,769 | 7,0% | 0,0% |
| 0,15 | 7 | 4 | 0,803 | 9,0% | 4,9% |
| 0,22 | 6 | 4 | 0,745 | 9,4% | 19,4% |

Yang memburuk lebih dulu adalah hari rusak yang terlewat, bukan tuduhan palsu.
Arah kegagalannya benar: sistem jadi pendiam, bukan jadi asal tuduh.

Perancu berarah (penuaan yang hanya menyentuh tiga aliran) diuji karena bentuk
inilah yang paling mungkin disangka kerusakan. Pemulihan bertahan 4/5 dan salah
tuduh tetap ~5% sampai penuaan 35%. Perancu ini tidak melahirkan tuduhan baru.

| Panjang riwayat | Pola | Pulih | Kosinus rerata | Salah tuduh |
|---|---|---|---|---|
| 60 hari | 1 | 1 | 0,200 | 14,6% |
| 120 hari | 4 | 4 | 0,797 | 8,3% |
| 250 hari | 6 | 4 | 0,762 | 6,4% |
| 400 hari | 6 | 4 | 0,786 | 5,1% |
| 800 hari | 5 | 4 | 0,746 | 2,6% |

**60 hari tidak cukup.** Modul atribusi baru boleh dinyalakan setelah sekitar
empat bulan giling; sampai saat itu sistem menyajikan neraca tanpa menunjuk
sebab, dan itu harus jadi perilaku bawaan saat dipasang.

### Sensitivitas koefisien - sifat keadilan yang terukur

Nisbah massa meleset +/-15%:

| | Sisi pemasok | Sisi pabrik | Tak terjelaskan |
|---|---|---|---|
| Rentang pergeseran | **0,000 poin** | 0,502 poin | 0,502 poin |

Tagihan pemasok tidak bergerak satu poin pun. Itu akibat langsung struktur tiga
baris: koefisien sisi pabrik tidak pernah masuk ke perhitungan potensi
realistis. Pihak yang paling lemah posisinya terlindung dari ketidaktahuan
sistem, bukan menanggungnya.

---

## 10. Perambatan ketidakpastian dan koreksi terpelajar

### e4 — kenapa selisih harus MELEBAR

Selisih neraca dihitung dari beberapa angka yang semuanya tidak pasti:
komposisi taksiran (e2), hasil ukur laboratorium per aliran, dan jembatan
timbang. Ragamnya menjumlah, jadi selangnya melebar. Sistem yang melaporkan
selisih lebih sempit daripada bahan-bahannya sedang mengaku tahu lebih banyak
daripada yang mungkin.

Dipakai Monte Carlo alih-alih rumus rambat analitik, karena baris pemasok
berasal dari selang komposisi yang tidak berbentuk normal dan saling terikat
lewat kendala berjumlah satu. Rumus analitik akan mengasumsikan bentuk yang
tidak dimiliki datanya.

| Penyumbang | Lebar selang 90% |
|---|---|
| Baris pemasok (mutu buah masuk) | 0,6368 poin |
| Baris pabrik terlebar (janjang kosong) | 0,1153 poin |
| Akar jumlah kuadrat seluruh penyumbang | 0,6594 poin |
| **Baris tak terjelaskan (e4)** | **0,7228 poin** |

Sisa lebih lebar daripada akar-jumlah-kuadrat karena ketidakpastian jembatan
timbang menyentuh seluruh neraca sekaligus. Sifat ini dijaga uji
`test_sisa_lebih_lebar_daripada_bahannya` dan
`test_ragam_menjumlah_bukan_mengambil_yang_terbesar`.

Bila selang komposisi tidak diberikan, baris pemasok diperlakukan sebagai
titik — dan sistem **mengatakannya** lewat `catatan`, alih-alih membiarkan
kelalaian menyamar jadi kepastian.

### Keyakinan per baris

Dua hal menurunkan keyakinan, dan keduanya dihormati:

1. **Selang yang memuat nol.** Selama "tidak ada kehilangan sama sekali" belum
   tersingkir, baris itu tidak boleh jadi dasar potongan — berapa pun sempitnya
   angka tengahnya.
2. **Koefisien yang belum tertelusur.** Angka boleh terlihat rapi; rapi bukan
   sahih.

### AI-2.2.3 — koreksi terpelajar DI ATAS formula

Formula potensi bisa dihitung ulang dengan kalkulator, dan itu satu-satunya
alasan angkanya boleh dipakai dalam sengketa harga. Tetapi formula tidak bisa
belajar kekhasan satu pabrik. Jalan tengahnya:

```
OER = formula(komposisi) + koreksi(komposisi)
      \____ terlacak ___/   \__ maksimum ±0,33 poin __/
```

Tiga pagar yang membuatnya tetap alat bukti: **terbatas** (dipotong pada 0,33
poin), **terpisah** (nilai formula dan koreksi dilaporkan sendiri-sendiri, tidak
pernah menyatu), dan **berbunyi** (koreksi > 0,25 poin menyalakan alarm).

Yang dipelajari adalah **sisa** formula, bukan rendemen itu sendiri. Bedanya
menentukan: model yang belajar langsung dari rendemen akan selalu menemukan
sesuatu, termasuk dari derau. Model yang belajar dari sisa menuju nol dengan
sendirinya bila formulanya sudah benar.

| Percobaan | Yang ditanam | Koreksi dipulihkan | Alarm |
|---|---|---|---|
| Koefisien terbit memang berlaku | 0 | −0,004 poin | tidak |
| Pabrik dengan kekhasan varietas | +0,150 | **+0,153** | tidak |
| Kehilangan pabrik bocor ke sisi pemasok | −0,600 | −0,592 → dipotong −0,330 | **YA** |

Percobaan ketiga adalah yang terpenting: kalau kehilangan sisi pabrik bocor
masuk, koreksi **tidak** boleh menyerapnya diam-diam — itu akan menagihkan
antrean bongkar kepada petani. Ia dipotong pada batas dan alarmnya berbunyi.

Daftar fitur dikunci ke empat proporsi kematangan saja. Fitur apa pun yang
menyangkut proses pabrik ditolak oleh `_periksa_fitur`, dijaga uji terhadap
lima nama terlarang.

### Permukaan API resmi

GATE AI-1 sampai AI-4 menyebut nama tertentu. Nama itu kini ada sebagai lapis
tipis di atas modul internal, supaya perubahan istilah di sisi AI tidak
menyentuh backend:

| GATE | API | Keluaran |
|---|---|---|
| AI-1 | `Detector.predict(gambar)` | `list[Detection]` |
| AI-2 | `composition.infer(...)` | `dict[str, Selang]` |
| AI-2 | `potential.estimate(...)` | `PotensiMinyak` berselang |
| AI-3 | `balance.reconcile(...)` | `KartuNeraca` tiga baris |
| AI-4 | `attribution.decompose(...)` | `Diagnosa` berselang |

`attribution.decompose` menolak dipanggil sebelum `pelajari_riwayat`. Itu
disengaja: sistem yang bisa menuduh sebelum melihat riwayat pabriknya sendiri
sedang menebak.

### Dua berkas yang tercentang tetapi kosong

Ditemukan saat menutup bagian ini, dan dicatat supaya polanya dikenali:

- `ai/evaluation/calibration.py` — 0 baris, padahal AI-2.1.5 sudah tercentang.
- `ai/perception/detector.py` — 11 baris docstring saja, padahal AI-1.4.2 sudah
  tercentang dan GATE AI-1 menuntut `Detector.predict()`.

Keduanya kini terisi. Pelajarannya: centang di pipeline bukan bukti; yang
membuktikan adalah berkas yang bisa dijalankan.

### Dua kekeliruan yang tertangkap saat memasang detektor

1. **Head yang dipakai bermode `ce`, bukan CORAL.** Docstring `detector.py`
   masih menuliskan CORAL sebagai keputusan, padahal hipotesis itu sudah diuji
   dan kalah (bagian 5). Modul kini membaca mode langsung dari checkpoint
   alih-alih menebaknya.
2. **Ukuran crop 128, bukan 256.** Nilai itu tersimpan di checkpoint bersama
   normalisasinya. Menuliskannya ulang di sisi inferensi adalah cara paling umum
   head menerima gambar yang tidak pernah dilihatnya sewaktu belajar — dan
   gejalanya bukan error, melainkan akurasi yang diam-diam anjlok.

Pemetaan kelas diverifikasi terhadap label sebenarnya pada 25 citra uji: 76
tandan pada label menghasilkan 86 deteksi berkematangan, 12 abnormal
menghasilkan 9 abnormal.

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
8. Model 2 memberi selang yang lebarnya berada **tepat di lantai pencuplikan
   teoretis** (rasio 0,999-1,122) dengan cakupan 0,9046 setelah kalibrasi
   conformal - memeras seluruh informasi yang tersedia tanpa mengaku tahu lebih.
9. Nilai Model 2 **terkonsentrasi pada muatan yang ditata sengaja** (+19,3%)
   dan nyaris nihil pada muatan jujur (+2,0%): ia mekanisme ketahanan terhadap
   penataan muatan, bukan penambah akurasi umum.
10. Neraca tiga baris **terbukti tidak menghitung buah mentah dua kali**:
    memburukkan mutu buah dari 0% ke 40% mentah menggeser sisi pabrik sebesar
    0,00e+00 poin. 19 uji lulus.
11. Galat koefisien pabrik +/-15% **tidak menggeser tagihan pemasok sama sekali**
    (0,000 poin); seluruhnya mendarat di sisi pabrik dan baris tak terjelaskan.
12. Model 6 **menemukan kembali 4 dari 5 aturan sebab-akibat** yang tidak pernah
    diperlihatkan padanya, dengan kosinus 0,931-0,9995 dan pemasangan Hungarian.
13. Kegagalan yang tersisa **punya sebab yang bisa dihitung**: dua gangguan
    dengan tanda tangan berimpit tidak dapat dipisahkan metode tanpa label.
14. Kebutuhan riwayat minimum terukur: **120 hari giling** sebelum modul
    atribusi layak dinyalakan.
15. Ketidakpastian **terbukti merambat ke arah yang benar**: baris tak
    terjelaskan (0,7228 poin) lebih lebar daripada seluruh penyumbangnya dan
    daripada akar-jumlah-kuadratnya (0,6594 poin).
16. Koreksi terpelajar **memulihkan kekhasan pabrik yang nyata** (+0,150
    ditanam, +0,153 dipulihkan) sambil **menolak menyerap kebocoran sisi
    pabrik**: bias −0,600 dipotong pada batas dan menyalakan alarm.
17. Formula tetap memegang hasil akhir: koreksi dibatasi ±0,33 poin dan
    dilaporkan terpisah, sehingga keterlacakan tidak ditukar dengan kemampuan
    belajar.

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
- **Bahwa Model 2 sudah divalidasi terhadap kenyataan.** Ia diuji terhadap
  simulatornya sendiri. Kebenaran sesungguhnya - komposisi satu truk penuh -
  memerlukan pembongkaran dan penyortiran manual yang belum dilakukan. Yang
  terbukti adalah metodenya benar, bukan akurasi lapangannya.
- **Bahwa Model 5 dan 6 sudah divalidasi terhadap pabrik nyata.** Keduanya diuji
  di atas simulator. Yang terbukti adalah aritmetika neracanya eksak dan
  atribusinya memulihkan gangguan yang ditanam.
- Bahwa nisbah massa aliran sudah sahih. Angka itu taksiran teknik berstatus
  `perlu_verifikasi`, diterima sementara karena jumlahannya mendarat di norma
  industri. Harus diganti dengan nisbah terukur dari satu pabrik nyata sebelum
  sistem menyentuh keputusan pembayaran.
- Bahwa modul atribusi bisa dinyalakan sejak hari pertama pemasangan. Di bawah
  120 hari riwayat, ia belum layak menunjuk sebab.
- Bahwa koreksi terpelajar sudah divalidasi terhadap pabrik nyata. Ia diuji
  terhadap bias yang ditanam sendiri. Yang terbukti adalah mekanismenya benar
  — memulihkan yang wajar, menolak yang mencurigakan — bukan bahwa ia sudah
  mengenal pabrik mana pun.
- Bahwa selang e4 sudah terkalibrasi terhadap kenyataan. Ia rambatan yang
  benar secara aritmetika dari selang-selang masukan; kalau salah satu masukan
  itu belum terkalibrasi di lapangan, hasilnya ikut mewarisi keterbatasan itu.
