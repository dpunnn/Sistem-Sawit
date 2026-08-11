"""NERACA MINYAK — API.

Arsitektur dua lapis:
  app/perception/  Lapis 1 — "Apa yang masuk?"   (Model 1, 2, 4)
  app/reasoning/   Lapis 2 — "Ke mana perginya?" (Model 5, 6)

Pemisahan folder ini disengaja: arsitektur dua lapis harus terbaca
langsung dari struktur kode, bukan cuma dari diagram di proposal.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, init_pool, ping

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    # TODO(Phase 1.4.3): warm-up model detektor di sini.
    # Jangan lazy-load: request pertama ke model yang belum dimuat bisa
    # makan 10-20 detik, dan itu terlihat seperti sistem lambat kalau
    # kebetulan terjadi saat live demo di depan juri.
    yield
    close_pool()


app = FastAPI(
    title="Neraca Minyak",
    description=(
        "Sistem forensik kehilangan rendemen kelapa sawit. "
        "Menutup neraca dari gerbang sampai tangki, lalu mengatribusikan "
        "setiap poin rendemen yang hilang ke penyebabnya."
    ),
    version=VERSION,
    lifespan=lifespan,
)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Membuktikan API dan Postgres benar-benar tersambung.

    Dipakai healthcheck docker-compose (service `web` menunggu ini
    sehat) dan saat merekam video proof of work.
    """
    return {"status": "ok" if ping() else "degraded", "version": VERSION}


# TODO(Phase 1.4.4): app.include_router(grading.router)
# TODO(Phase 3.2.4): app.include_router(balance.router)
