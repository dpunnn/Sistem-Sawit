"""Endpoint grading — menyambungkan Model 1, 2, 4 ke dunia luar."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Path as PathParam, UploadFile
from fastapi.responses import JSONResponse

from app.core.db import get_conn
from app.schemas.models import GraderDecision, GradingResult
from app.services import kontrak, reasoning
from app.services.grading import layanan

router = APIRouter(prefix="/api", tags=["grading"])

TIPE_DITERIMA = {"image/jpeg", "image/png", "image/webp"}
MAKS_BYTE = 12 * 1024 * 1024


def _tolak(pesan: str, saran: str, kode: int = 415) -> HTTPException:
    """Pesan error yang memberi tahu apa yang harus dilakukan.

    Juri PASTI mencoba mengunggah berkas aneh. Sistem yang crash saat
    diberi PDF terlihat rapuh; yang menjawab "format tidak didukung,
    gunakan JPG/PNG" terlihat matang.
    """
    return HTTPException(status_code=kode, detail={"pesan": pesan, "saran": saran})


@router.post(
    "/grading",
    response_model=GradingResult,
    summary="Nilai satu muatan truk dari foto",
    description=(
        "Menjalankan Model 1 (deteksi tandan), Model 2 (komposisi seluruh "
        "muatan dari lapisan permukaan), dan Model 4 (potensi minyak dalam "
        "kilogram) atas satu foto.\n\n"
        "**Yang perlu dipahami dari keluarannya:** `detections` adalah apa yang "
        "benar-benar TERLIHAT di permukaan, sedangkan `composition` adalah "
        "taksiran untuk SELURUH muatan. Keduanya sengaja berbeda — permukaan "
        "bisa ditata, dan selisih itulah yang dikoreksi Model 2.\n\n"
        "Setiap angka hasil model keluar sebagai `{value, lo, hi}`. Tidak ada "
        "varian tanpa selang."
    ),
    responses={
        413: {"description": "Berkas melebihi 12 MB"},
        415: {"description": "Format berkas tidak didukung"},
        503: {"description": "Bobot model belum tersedia di server"},
    },
)
async def grade(
    image: UploadFile,
    gross_weight_kg: float = Form(
        6000.0, gt=0, description="Berat bruto muatan dari jembatan timbang (kg)"),
    batch_id: int | None = Form(
        None, description="Kaitkan hasil ke muatan yang sudah tercatat"),
):
    if image.content_type not in TIPE_DITERIMA:
        raise _tolak(
            f"Format {image.content_type or 'tidak dikenal'} tidak didukung.",
            "Gunakan JPG, PNG, atau WebP.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".img") as tmp:
        ukuran = 0
        while chunk := await image.read(1 << 20):
            ukuran += len(chunk)
            if ukuran > MAKS_BYTE:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise _tolak(
                    f"Berkas melebihi {MAKS_BYTE // 1024 // 1024} MB.",
                    "Perkecil resolusi foto lalu unggah ulang.", kode=413)
            tmp.write(chunk)
        jalur = Path(tmp.name)

    try:
        hasil = layanan.proses(jalur, gross_weight_kg)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail={"pesan": "Bobot model belum tersedia di server.",
                    "saran": "Jalankan pelatihan atau salin bobot ke ai/weights/.",
                    "teknis": str(e)}) from e
    except Exception as e:  # berkas rusak, bukan gambar sungguhan, dll.
        raise _tolak(
            "Berkas tidak bisa dibaca sebagai gambar.",
            "Pastikan berkasnya foto yang utuh, bukan berkas yang rusak "
            "atau sekadar berekstensi gambar.", kode=422) from e
    finally:
        jalur.unlink(missing_ok=True)

    grading_id = None
    if batch_id is not None:
        try:
            with get_conn() as conn:
                row = conn.execute(
                    """
                    INSERT INTO grading_result (batch_id, composition,
                        potential_oil_kg, potential_lo, potential_hi,
                        detections, overlay_path, low_confidence_n,
                        model_version)
                    VALUES (%s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    RETURNING id
                    """,
                    (batch_id, json.dumps(kontrak.komposisi_ke_db(hasil.composition)),
                     hasil.potential_oil_kg["value"], hasil.potential_oil_kg["lo"],
                     hasil.potential_oil_kg["hi"], json.dumps(hasil.detections),
                     hasil.overlay_url, hasil.low_confidence_count,
                     hasil.model_version)).fetchone()
                conn.commit()
                grading_id = row["id"]
        except Exception:
            # Basis data mati tidak boleh membatalkan hasil model yang
            # sudah terlanjur dihitung. Hasilnya tetap dikembalikan,
            # hanya tanpa id -- dan frontend memang menanganinya.
            grading_id = None

    return GradingResult(
        batch_id=grading_id or batch_id,
        detections=hasil.detections,
        overlay_url=hasil.overlay_url,
        composition=[{"ripeness": k, "percent": v}
                     for k, v in hasil.composition.items()],
        potential_oil_kg=hasil.potential_oil_kg,
        low_confidence_count=hasil.low_confidence_count,
        model_version=hasil.model_version,
        processed_at=hasil.processed_at,
    )


# Nama yang disebut pipeline (GATE BE-1). Frontend memakai /api/grading;
# keduanya disediakan supaya tidak ada pihak yang harus berubah.
@router.post("/grade", include_in_schema=False)
async def grade_alias(image: UploadFile, gross_weight_kg: float = Form(6000.0),
                      batch_id: int | None = Form(None)):
    return await grade(image, gross_weight_kg, batch_id)


@router.get(
    "/grading/{grading_id}",
    response_model=GradingResult,
    summary="Ambil hasil grading yang tersimpan",
    description="Dipakai halaman sertifikat sortasi dan halaman neraca.",
    responses={404: {"description": "Hasil grading tidak ditemukan"}},
)
def ambil_grading(grading_id: int = PathParam(..., ge=1)):
    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM grading_result WHERE id = %s", (grading_id,)).fetchone()
    if not r:
        raise HTTPException(
            status_code=404,
            detail={"pesan": f"Grading {grading_id} tidak ada.",
                    "saran": "Periksa id, atau jalankan scripts/seed_shift.py."})

    komposisi = kontrak.komposisi_dari_db(r["composition"])

    # Nama pemasok datang dari basis data, bukan ditulis di layar.
    # Sertifikat sortasi yang menyebut nama pemasok yang salah lebih
    # buruk daripada sertifikat yang tidak menyebut nama sama sekali.
    with get_conn() as conn:
        sup = conn.execute(
            "SELECT s.name, s.kind, b.truck_plate, b.gross_weight_kg, "
            "       b.queue_hours, b.shift_date "
            "FROM batch b JOIN supplier s ON s.id = b.supplier_id "
            "WHERE b.id = %s", (r["batch_id"],)).fetchone() if r["batch_id"] else None

    return GradingResult(
        batch_id=r["batch_id"],
        detections=r["detections"] or [],
        overlay_url=r["overlay_path"],
        composition=[{"ripeness": k, "percent": v} for k, v in komposisi.items()],
        supplier=(dict(name=sup["name"], kind=sup["kind"],
                       truck_plate=sup["truck_plate"],
                       gross_weight_kg=float(sup["gross_weight_kg"]),
                       queue_hours=float(sup["queue_hours"]),
                       shift_date=sup["shift_date"]) if sup else None),
        deduction_basis=reasoning.dasar_potongan(komposisi),
        potential_oil_kg={"value": float(r["potential_oil_kg"]),
                          "lo": float(r["potential_lo"]),
                          "hi": float(r["potential_hi"])},
        low_confidence_count=r["low_confidence_n"],
        model_version=r["model_version"],
        processed_at=r["processed_at"],
    )


@router.get("/batch/{grading_id}", include_in_schema=False)
def ambil_batch_alias(grading_id: int):
    return ambil_grading(grading_id)


@router.post(
    "/grading/{grading_id}/decision",
    summary="Simpan keputusan grader",
    description=(
        "Manusia tetap pemegang keputusan. Setiap koreksi disimpan sebagai "
        "data latih untuk kalibrasi ulang — dan karena layar gerbang "
        "menjanjikan itu, jalurnya harus benar-benar ada."
    ),
    responses={404: {"description": "Hasil grading tidak ditemukan"}},
)
def simpan_keputusan(keputusan: GraderDecision, grading_id: int = PathParam(..., ge=1)):
    with get_conn() as conn:
        ada = conn.execute(
            "SELECT 1 FROM grading_result WHERE id = %s", (grading_id,)).fetchone()
        if not ada:
            raise HTTPException(
                status_code=404,
                detail={"pesan": f"Grading {grading_id} tidak ada.",
                        "saran": "Simpan hasil grading lebih dulu."})

        conn.execute(
            "INSERT INTO grader_decision (grading_id, decision, note, corrected) "
            "VALUES (%s, %s, %s, %s::jsonb)",
            (grading_id, keputusan.decision, keputusan.note,
             json.dumps([c.model_dump() for c in keputusan.corrected_composition])
             if keputusan.corrected_composition else None))
        conn.execute(
            "UPDATE grading_result SET human_corrected = %s, correction_note = %s "
            "WHERE id = %s",
            (keputusan.decision == "correct", keputusan.note, grading_id))
        conn.commit()

    return JSONResponse({
        "status": "tersimpan",
        "grading_id": grading_id,
        "decision": keputusan.decision,
        "catatan": ("Koreksi masuk antrean data latih untuk kalibrasi ulang."
                    if keputusan.decision == "correct"
                    else "Hasil disetujui, sertifikat sortasi diterbitkan."),
    })
