"""Jembatan ke Lapis 2: neraca (Model 5) dan atribusi (Model 6).

ATURAN 3 lagi: tidak ada aritmetika neraca di berkas ini. Yang ada
hanya pembacaan basis data, pemanggilan `ai/reasoning/`, dan
penerjemahan bentuk.

Cara memeriksanya cepat: cari tanda `+` atau `-` antar besaran domain.
Kalau ada, ada rumus yang menyelinap ke lapis yang salah.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ai.config import coefficients as C  # noqa: E402
from ai.reasoning import balance as M5  # noqa: E402

from app.services import kontrak  # noqa: E402


def selang_baris(b) -> dict:
    """Satu baris kartu neraca dalam bentuk kontrak.

    `poin` di lapis AI bertanda NEGATIF (kehilangan mengurangi
    rendemen). Kontrak HTTP memakai besaran positif karena frontend
    menggambarnya sebagai batang turun, dan tanda ganda di dua tempat
    adalah sumber kekeliruan yang tidak berujung.

    Pembalikannya NEGASI, bukan nilai mutlak. Bedanya baru terlihat
    ketika sisa bertanda positif -- yaitu saat pabrik menghasilkan lebih
    banyak daripada yang bisa dijelaskan neraca. Dengan nilai mutlak,
    batas selangnya tertukar dan `lo` jadi lebih besar daripada `hi`.
    Dengan negasi, urutannya selalu benar karena negasi membalik urutan
    dan batasnya ikut ditukar.

    Kasus itu jarang, tetapi bukan mustahil: ia muncul persis ketika
    koefisien terbit terlalu berhati-hati. Dan nilainya memang harus
    boleh negatif -- "kehilangan negatif" adalah cara neraca mengatakan
    ada yang keliru pada koefisien, bukan sesuatu yang boleh disamarkan
    jadi positif.
    """
    return {
        "cause": b.nama,
        "side": kontrak.pihak(b.pihak),
        "points": {"value": round(-b.poin, 4),
                   "lo": round(-b.poin_hi, 4),
                   "hi": round(-b.poin_lo, 4)},
        "confidence": kontrak.keyakinan(b.keyakinan),
        "detail": b.keterangan or None,
    }


def nilai_rupiah(poin_hilang: float, tbs_kg: float) -> float:
    """Ubah poin rendemen jadi rupiah.

    Kurs berstatus `perlu_verifikasi`, jadi harus diminta dengan izin
    eksplisit. Nilai rupiah dipakai untuk komunikasi ke manajemen dan
    juri non-teknis — bukan untuk keputusan pembayaran, di mana yang
    berlaku tetap poin rendemen beserta selangnya.
    """
    usd = C.nilai("harga.cpo_referensi_usd_per_ton")
    kurs = C.nilai("harga.kurs_idr_per_usd", izinkan_belum_terverifikasi=True)
    return tbs_kg * poin_hilang / 100.0 / 1000.0 * usd * kurs


def kartu_dari_basis_data(shift: date, conn, *,
                          mode: str = "terverifikasi") -> dict | None:
    """Hitung ULANG kartu neraca dari data mentah shift itu.

    Bukan membaca tabel `balance` apa adanya. Tabel itu catatan hasil;
    yang disajikan endpoint adalah perhitungan dari bahan mentahnya,
    sehingga perubahan koefisien langsung terlihat tanpa perlu mengisi
    ulang basis data. Hasilnya lalu ditulis kembali ke `balance` sebagai
    jejak.
    """
    out = conn.execute(
        "SELECT cpo_actual_kg, tbs_processed_kg FROM shift_output "
        "WHERE shift_date = %s", (shift,)).fetchone()
    if not out:
        return None

    tbs = float(out["tbs_processed_kg"])
    cpo = float(out["cpo_actual_kg"])

    # Komposisi shift = rata-rata berbobot berat tiap muatan.
    #
    # DISTINCT ON: satu muatan hanya boleh menyumbang SEKALI, memakai
    # grading terbarunya. Tanpa ini, memindai ulang truk yang sama
    # membuat beratnya dihitung berkali-kali — dan pernah membuat berat
    # yang dipakai neraca menggelembung dari 131.926 kg jadi 205.639 kg
    # tanpa satu pun error muncul.
    baris = conn.execute(
        "SELECT DISTINCT ON (b.id) g.composition, b.gross_weight_kg, "
        "       b.queue_hours "
        "FROM grading_result g JOIN batch b ON b.id = g.batch_id "
        "WHERE b.shift_date = %s "
        "ORDER BY b.id, g.id DESC", (shift,)).fetchall()
    if not baris:
        return None

    total_berat = sum(float(r["gross_weight_kg"]) for r in baris)
    komposisi: dict[str, float] = {}
    lebar: dict[str, float] = {}
    for r in baris:
        w = float(r["gross_weight_kg"]) / total_berat
        for nama_kontrak, v in kontrak.komposisi_dari_db(r["composition"]).items():
            nama = kontrak.KELAS_BALIK.get(nama_kontrak)
            if nama is None:
                continue
            komposisi[nama] = komposisi.get(nama, 0.0) + v["value"] / 100.0 * w
            lebar[nama] = lebar.get(nama, 0.0) + (v["hi"] - v["lo"]) / 200.0 * w

    restan = sum(float(r["queue_hours"]) * float(r["gross_weight_kg"])
                 for r in baris) / total_berat

    # Kehilangan pabrik, sudah dalam poin rendemen. Postgres yang
    # menghitung points_oer (kolom GENERATED), bukan Python -- supaya
    # kadar tidak pernah bisa terjumlah langsung tanpa nisbah massanya.
    kehilangan = {
        r["station"]: float(r["points_oer"])
        for r in conn.execute(
            "SELECT station, points_oer FROM station_loss WHERE shift_date = %s",
            (shift,)).fetchall()
    }

    komposisi_selang = {
        k: (max(0.0, v - lebar.get(k, 0.03)), v, min(1.0, v + lebar.get(k, 0.03)))
        for k, v in komposisi.items()
    }

    kartu = M5.reconcile(
        komposisi, tbs, cpo,
        kehilangan_pabrik_poin=kehilangan,
        komposisi_selang=komposisi_selang,
        jam_restan=restan, mode=mode,
    )

    hilang = kartu.oer_teoretis - kartu.oer_aktual
    return {
        "shift_date": shift,
        # Jejak asal-usul. Tanpa ini, layar tidak punya cara menunjukkan
        # bahwa angkanya baru dihitung ulang — dan orang wajar mengira
        # halamannya beku padahal isinya memang belum berubah.
        "n_muatan": len(baris),
        "computed_at": datetime.now(timezone.utc),
        "potential_theoretical": round(kartu.oer_teoretis, 3),
        "supplier_losses": [selang_baris(b) for b in kartu.rugi_pemasok],
        "potential_realistic": round(kartu.oer_realistis, 3),
        "mill_losses": [selang_baris(b) for b in kartu.rugi_pabrik],
        "unexplained": selang_baris(kartu.tak_terjelaskan),
        "actual_oer": round(kartu.oer_aktual, 3),
        "loss_value_idr": round(nilai_rupiah(hilang, tbs), 2),
        "station_losses": stasiun_shift(shift, conn),
        "_kartu": kartu,
        "_tbs_kg": tbs,
    }


def stasiun_shift(shift: date, conn) -> list[dict]:
    """Rincian kehilangan per stasiun, apa adanya dari basis data.

    Bagian neraca yang tidak melibatkan model sama sekali — fisika dan
    akuntansi dari pekerjaan lab harian. Justru karena itu ia yang
    paling mudah diaudit orang luar.
    """
    rows = conn.execute(
        "SELECT station, loss_pct, standard_pct, mass_ratio, points_oer "
        "FROM station_loss WHERE shift_date = %s ORDER BY points_oer DESC",
        (shift,)).fetchall()
    return [{
        "station": kontrak.LABEL_STASIUN.get(r["station"], r["station"]),
        "oil_content_pct": float(r["loss_pct"]),
        "mass_ratio": float(r["mass_ratio"]),
        "points": round(float(r["points_oer"]), 4),
        "standard_pct": float(r["standard_pct"]) if r["standard_pct"] is not None else None,
    } for r in rows]


def simpan_kartu(kartu_dict: dict, conn, *, mode: str = "terverifikasi") -> None:
    """Tulis kartu ke tabel `balance` sebagai catatan permanen."""
    import json

    atribusi = [
        {**b, "points": b["points"]["value"],
         "lo": b["points"]["lo"], "hi": b["points"]["hi"]}
        for b in (*kartu_dict["supplier_losses"], *kartu_dict["mill_losses"],
                  kartu_dict["unexplained"])
    ]
    conn.execute(
        """
        INSERT INTO balance (shift_date, potential_theoretical,
            potential_realistic, actual_oer, attribution, loss_value_idr,
            coefficient_mode)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
        ON CONFLICT (shift_date) DO UPDATE SET
            potential_theoretical = EXCLUDED.potential_theoretical,
            potential_realistic   = EXCLUDED.potential_realistic,
            actual_oer            = EXCLUDED.actual_oer,
            attribution           = EXCLUDED.attribution,
            loss_value_idr        = EXCLUDED.loss_value_idr,
            coefficient_mode      = EXCLUDED.coefficient_mode,
            computed_at           = now()
        """,
        (kartu_dict["shift_date"], kartu_dict["potential_theoretical"],
         kartu_dict["potential_realistic"], kartu_dict["actual_oer"],
         json.dumps(atribusi), kartu_dict["loss_value_idr"], mode),
    )


def dasar_potongan(komposisi: dict, *, mode: str = "terverifikasi") -> dict:
    """Aritmetika potongan yang bisa dihitung ulang oleh yang membacanya.

    Koefisiennya DIBACA dari ai/config/coefficients.yaml, tidak pernah
    ditulis di sini maupun di frontend. Sebelumnya angka 0,13 disalin ke
    berkas React dan bahkan dicetak sebagai teks — artinya kalau
    koefisiennya berubah, layar tetap memamerkan angka lama sambil
    terlihat sangat meyakinkan.

    Sitasi ikut dikirim supaya petani yang membantah bisa menelusuri
    sumbernya sendiri, bukan disuruh percaya.
    """
    izin = mode != "terverifikasi"
    k = C.get("kematangan.penalti_buah_mentah", izinkan_belum_terverifikasi=izin)
    persen = float(komposisi.get("unripe", {}).get("value", 0.0))
    return {
        "unripe_pct": round(persen, 2),
        "coefficient_per_pct": abs(k.nilai),
        "coefficient_status": k.status,
        "coefficient_source": k.sumber_kunci,
        # Kutipan lengkap ikut dikirim, bukan cuma kuncinya. Petani yang
        # membantah potongan berhak menelusuri sumbernya sendiri tanpa
        # harus membuka repositori.
        "citation": {
            "judul": k.sumber.get("judul"),
            "penerbit": k.sumber.get("penerbit"),
            "url": k.sumber.get("url"),
        },
        "points": round(persen * abs(k.nilai), 3),
        # Sengaja TIDAK mengirim kalimat jadi. Pemformatan angka adalah
        # urusan layar: backend yang merangkai teks akan memakai titik
        # desimal Inggris di tengah antarmuka berbahasa Indonesia, dan
        # itu tidak bisa diperbaiki dari sisi frontend.
        "formula": None,
    }
