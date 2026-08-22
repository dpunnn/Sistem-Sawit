"""NERACA MINYAK — API.

Arsitektur dua lapis:
  ai/perception/   Lapis 1 — "Apa yang masuk?"   (Model 1, 2, 4)
  ai/reasoning/    Lapis 2 — "Ke mana perginya?" (Model 5, 6)

ATURAN 3: backend adalah JEMBATAN, bukan pemilik logika. Tidak ada satu
pun rumus rendemen di dalam `backend/`. Router mengurus HTTP, service
mengurus urutan langkah, dan seluruh penalaran domain hidup di `ai/`.
Kalau ada aritmetika domain menyelinap ke sini, lapisannya bocor.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.db import close_pool, init_pool, ping  # noqa: E402
from app.routers import attribution, balance, grading, suppliers  # noqa: E402
from app.schemas.models import HealthResponse  # noqa: E402
from app.services.grading import DIR_OVERLAY, layanan  # noqa: E402

VERSION = "0.2.0"

DESKRIPSI = """
Sistem forensik kehilangan rendemen kelapa sawit. Menutup neraca dari
gerbang sampai tangki, lalu mengatribusikan setiap poin rendemen yang
hilang ke penyebabnya — **dengan selang keyakinan, dan menunjuk ke dua
arah**.

## Cara mencoba di halaman ini

1. **`GET /api/health`** — pastikan API dan Postgres tersambung.
2. **`GET /api/shifts`** — lihat tanggal shift yang tersedia.
3. **`GET /api/balance`** — kartu neraca tiga baris untuk shift terakhir.
4. **`GET /api/attribution`** — penyebab kehilangan, masing-masing dengan
   selang dan ambang tindakannya.
5. **`POST /api/grading`** — unggah foto muatan TBS. Contoh foto tersedia
   di `data/samples/` pada repo.

## Tiga hal yang membedakan keluaran sistem ini

**Setiap angka hasil model membawa selang.** Tipe `Estimate` tidak punya
varian tanpa `lo`/`hi`. Janji "jujur soal ketidakpastian" ditegakkan
sistem tipe, bukan niat baik.

**Neraca selalu tiga baris, tidak pernah dua.** Baris tengah (potensi
realistis) memutus rantai yang membuat buah mentah dihitung dua kali —
sekali karena menurunkan kandungan minyak yang masuk, sekali lagi lewat
kehilangan pabrik yang naik saat memproses buah mentah.

**Baris `unexplained` wajib ada dan tidak pernah dipaksa nol.** Sistem
yang memaksanya nol sedang membebankan selisihnya ke salah satu pihak
tanpa bukti, dan biasanya ke pihak yang lebih lemah.

## Batas yang harus ikut dibaca

Komponen kematangan berakurasi **0,6346** pada muatan campuran. Itu
menempatkannya pada keyakinan **sedang**: bahan diskusi, belum cukup
untuk memotong pembayaran. Endpoint atribusi menyatakannya eksplisit
lewat `may_deduct_payment`.

Nisbah massa yang mengubah kadar laboratorium jadi poin rendemen masih
berstatus `perlu_verifikasi`. Mode bawaan `terverifikasi` menolak
koefisien semacam itu, dan selisihnya muncul di baris `unexplained`
alih-alih dibebankan diam-diam.
"""

TAGS = [
    {"name": "system",
     "description": "Kesehatan sistem dan tata kelola koefisien."},
    {"name": "grading",
     "description": (
         "Lapis 1 — Persepsi. *Apa yang masuk?* Model 1 mendeteksi tandan, "
         "Model 2 menaksir komposisi seluruh muatan dari lapisan permukaan, "
         "Model 4 mengubahnya jadi kilogram minyak.")},
    {"name": "neraca",
     "description": (
         "Lapis 2 — Penalaran. *Ke mana perginya?* Model 5 menutup neraca "
         "dalam struktur tiga baris yang mencegah penghitungan ganda.")},
    {"name": "pemasok",
     "description": (
         "Peringkat pemasok dan koreksi grader, dihitung dari basis data. "
         "Bahan diskusi, bukan dasar potongan.")},
    {"name": "atribusi",
     "description": (
         "Lapis 2 — Model 6 memecah kehilangan jadi penyebab tanpa pernah "
         "melihat label kerusakan, masing-masing dengan selang dan ambang "
         "tindakan.")},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()

    # Pemanasan model. Request pertama ke model yang belum dimuat bisa
    # makan 10-20 detik; kalau itu terjadi di depan juri, yang terlihat
    # bukan "model besar" melainkan "sistem lambat".
    #
    # Kegagalan di sini TIDAK mematikan aplikasi: endpoint neraca dan
    # atribusi tidak butuh bobot detektor sama sekali, dan lebih baik
    # separuh sistem hidup daripada seluruhnya mati karena satu berkas
    # bobot belum tersalin.
    try:
        layanan.warmup()
    except Exception as e:  # noqa: BLE001
        print(f"[peringatan] bobot model belum siap: {e}")
        print("[peringatan] endpoint grading akan menjawab 503; "
              "neraca & atribusi tetap jalan.")

    DIR_OVERLAY.mkdir(parents=True, exist_ok=True)
    yield
    close_pool()


app = FastAPI(
    title="Neraca Minyak",
    description=DESKRIPSI,
    version=VERSION,
    lifespan=lifespan,
    openapi_tags=TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Repositori", "url": "https://github.com/dpunnn/Sistem-Sawit"},
    license_info={"name": "AGPL-3.0"},
)


@app.get("/api/health", tags=["system"], response_model=HealthResponse,
         summary="Kesehatan API, basis data, model, dan koefisien")
def health() -> HealthResponse:
    """Satu perintah untuk membuktikan seluruh rantai hidup.

    Dipakai healthcheck compose dan saat merekam video proof of work.
    `coefficients_healthy` ikut diperiksa karena koefisien tanpa sumber
    adalah kegagalan yang tidak menimbulkan error — ia hanya membuat
    angka terlihat sah padahal tidak.
    """
    try:
        db = ping()
    except Exception:  # noqa: BLE001
        db = False

    try:
        from ai.config import coefficients as C
        koef = bool(C.audit()["sehat"])
    except Exception:  # noqa: BLE001
        koef = False

    return HealthResponse(
        status="ok" if db else "degraded",
        version=VERSION,
        database=db,
        detector_ready=layanan.siap,
        coefficients_healthy=koef,
    )


@app.get("/api/coefficients", tags=["system"],
         summary="Audit koefisien domain beserta status dan sumbernya")
def koefisien():
    """Seluruh angka domain, statusnya, dan sitasinya.

    Diterbitkan lewat API supaya dasar ilmiah sistem bisa diperiksa
    tanpa membuka kode sama sekali. Koefisien berstatus
    `perlu_verifikasi` disebut apa adanya, bukan disembunyikan.
    """
    from ai.config import coefficients as C

    a = C.audit()
    return {
        "total": a["total"],
        "sehat": a["sehat"],
        "terverifikasi": a["terverifikasi"],
        "perlu_verifikasi": a["perlu_verifikasi"],
        "tanpa_sumber": a["tanpa_sumber"],
        "jumlah_sumber": a["jumlah_sumber"],
        "catatan": (
            "Mode bawaan sistem menolak koefisien `perlu_verifikasi`. "
            "Akibatnya kehilangan sisi pemasok ditaksir lebih kecil dan "
            "selisihnya masuk ke baris tak terjelaskan — arah yang disengaja."
        ),
    }


app.include_router(grading.router)
app.include_router(balance.router)
app.include_router(attribution.router)
app.include_router(suppliers.router)

# Gambar overlay disajikan sebagai berkas statis supaya frontend cukup
# memasang <img src=...> tanpa perlu menangani biner.
DIR_OVERLAY.mkdir(parents=True, exist_ok=True)
app.mount("/static/overlays", StaticFiles(directory=DIR_OVERLAY), name="overlays")
