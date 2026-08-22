"""Merangkai kartu neraca jadi PENYEBAB YANG BISA DITINDAKLANJUTI.

## Kenapa lapis ini ada

Model 5 menghasilkan baris per aliran laboratorium: kondensat, janjang
kosong, ampas kempa, nut in fiber, underflow CST, sludge, fat pit,
deoiling pond. Delapan angka yang benar, terukur, dan bisa diaudit.

Dan tidak berguna bagi manajer pabrik.

"cst underflow 0,21 poin" tidak memberi tahu apa yang harus diubah
besok pagi. Nilai sistem ini bukan mengukur kehilangan — pabrik sudah
mengukurnya tiap hari sebagai pekerjaan rutin — melainkan mengubah
ukuran jadi TINDAKAN, dan menempelkan nama pihak yang bisa
melakukannya.

Bentuk yang dituju ada di nyawit.txt bagian 8.3:

    0,7 +/- 0,25  buah mentah    -> pemasok A, C, F
    0,5 +/- 0,15  restan 9 jam   -> keputusan antrian
    0,6 +/- 0,20  sterilisasi    -> setelan tetap
    0,2 +/- 0,10  ampas kempa    -> di atas standar
    0,2 +/- 0,30  TIDAK TERJELASKAN

Perhatikan kolom kanannya: keputusan dan pihak, bukan nama alat.

## Pengelompokannya bukan karangan

Kelompok diambil dari `ai/reasoning/attribution.py`, dan bentuknya
persis pola yang ditemukan sendiri Model 6 dari riwayat giling —
kosinus 0,93-0,9995 terhadap tanda tangan gangguan yang ditanam.
Manusia tidak memutuskan bahwa kondensat dan janjang kosong satu
kelompok; data yang mengatakannya.

## Restan tidak boleh hilang

Pada mode `terverifikasi`, koefisien restan ditolak karena belum
tertelusur, sehingga kehilangannya masuk ke baris tak terjelaskan.
Akibatnya keputusan antrean bongkar — keputusan PABRIK — tidak pernah
muncul sebagai penyebab bernama.

Itu melubangi tesis "menunjuk dua arah" tepat di tempat yang paling
penting. Karena itu restan selalu ditampilkan sebagai penyebab, dengan
status koefisiennya disebut terus terang dan `may_deduct_payment`
bernilai salah.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ai.config import coefficients as C  # noqa: E402
from ai.reasoning.attribution import KELOMPOK_PENYEBAB  # noqa: E402

from app.services import kontrak  # noqa: E402

AMBANG = {
    "high": "Boleh jadi dasar keputusan finansial",
    "medium": "Cukup untuk bahan diskusi, belum untuk memotong pembayaran",
    "low": "Ditampilkan saja, tidak memicu tindakan",
}

# Nama stasiun kontrak -> nama aliran internal, untuk mencocokkan
# baris kartu neraca ke kelompok penyebabnya.
STASIUN_KE_ALIRAN = {v: k for k, v in kontrak.STASIUN.items()}


def _selang(nilai: float, lo: float, hi: float) -> dict:
    return {"value": round(nilai, 4), "lo": round(lo, 4), "hi": round(hi, 4)}


def _keyakinan(nilai: float, lo: float, hi: float, sah: bool) -> str:
    """Aturan yang sama dengan Model 5, diterapkan pada kelompok."""
    if lo * hi <= 0:
        return "low"
    lebar = (hi - lo) / max(abs(nilai), 1e-9)
    if lebar <= 0.20 and sah:
        return "high"
    return "medium" if lebar <= 0.50 else "low"


def _pemasok_teratas(pemasok: list[dict], n: int = 3) -> str | None:
    """Siapa penyumbang buah mentah terbesar.

    nyawit.txt menulis "buah mentah -> pemasok A, C, F". Tanpa nama,
    baris itu cuma keluhan; dengan nama, ia jadi daftar siapa yang perlu
    didampingi. Karena itu peringkatnya ikut, tetapi disertai jumlah
    muatan supaya tidak dibaca sebagai vonis atas sampel kecil.
    """
    kandidat = [p for p in pemasok if (p.get("unripe_pct") or 0) > 0]
    if not kandidat:
        return None
    kandidat.sort(key=lambda p: -(p["unripe_pct"] or 0))
    bagian = [f"{p['name']} ({p['unripe_pct']:.0f}%, {p['n_muatan']} muatan)"
              for p in kandidat[:n]]
    return "Terkonsentrasi pada " + "; ".join(bagian)


def susun_penyebab(kartu: dict, obj, pemasok: list[dict], *,
                   restan_jam: float, mode: str) -> list[dict]:
    """Ubah baris kartu neraca jadi penyebab yang menunjuk keputusan."""
    penyebab: list[dict] = []

    # --- sisi pemasok: mutu buah, dengan nama pemasoknya ---
    for b in kartu["supplier_losses"]:
        p = b["points"]
        penyebab.append({
            "cause": "Mutu buah masuk",
            "owner": "Pemasok",
            "side": "supplier",
            "points": p,
            "confidence": b["confidence"],
            "detail": _pemasok_teratas(pemasok) or b.get("detail"),
            "action": "Dampingi pemasok dengan proporsi buah mentah tertinggi; "
                      "sepakati interval panen.",
            "basis": b.get("detail"),
            "streams": [],
        })

    # --- restan: keputusan PABRIK, tidak boleh hilang ---
    if restan_jam > 0:
        try:
            k = C.get("restan.penalti_per_jam", izinkan_belum_terverifikasi=True)
            poin = abs(restan_jam * k.nilai)
            sah = k.status == C.TERVERIFIKASI
            dipakai = any("restan" in b["cause"].lower()
                          for b in kartu["mill_losses"])
            penyebab.append({
                "cause": f"Restan {restan_jam:.0f} jam",
                "owner": "Keputusan antrean bongkar",
                "side": "mill",
                # Selang lebar karena koefisiennya sendiri belum tertelusur.
                "points": _selang(poin, poin * 0.7, poin * 1.3),
                "confidence": "medium" if sah else "low",
                "detail": (
                    "Sudah masuk hitungan neraca."
                    if dipakai else
                    f"Koefisien restan berstatus {k.status}, jadi TIDAK "
                    "dibebankan ke pabrik dalam neraca — nilainya masuk ke "
                    "baris tak terjelaskan. Ditampilkan di sini supaya "
                    "keputusan antrean tetap terlihat sebagai penyebab."
                ),
                "action": "Perpendek antrean bongkar untuk muatan yang datang pagi.",
                "basis": f"{restan_jam:.1f} jam x {abs(k.nilai)} poin/jam",
                "streams": [],
                "counted_in_balance": dipakai,
            })
        except C.KoefisienError:
            pass

    # --- sisi pabrik: aliran laboratorium, DIKELOMPOKKAN ---
    sisa_baris = [b for b in kartu["mill_losses"]
                  if "restan" not in b["cause"].lower()]
    per_kelompok: dict[str, list[dict]] = {}
    tak_terkelompok: list[dict] = []
    for b in sisa_baris:
        # Nama baris datang dari Model 5 dengan garis bawah diganti spasi
        # ("empty bunch"), sedangkan peta memakai garis bawah
        # ("empty_bunch"). Tanpa normalisasi ini, yang cocok hanya nama
        # satu kata — dan enam dari delapan aliran diam-diam lolos dari
        # pengelompokan lalu muncul lagi sebagai nama alat di layar.
        kunci = b["cause"].strip().lower().replace(" ", "_").replace("-", "_")
        aliran = STASIUN_KE_ALIRAN.get(kunci, kunci)
        kel = next((k for k, v in KELOMPOK_PENYEBAB.items()
                    if aliran in v["aliran"]), None)
        (per_kelompok.setdefault(kel, []) if kel else tak_terkelompok).append(b)

    for kunci, isi in per_kelompok.items():
        v = KELOMPOK_PENYEBAB[kunci]
        nilai = sum(b["points"]["value"] for b in isi)
        lo = sum(b["points"]["lo"] for b in isi)
        hi = sum(b["points"]["hi"] for b in isi)
        penyebab.append({
            "cause": v["label"],
            "owner": v["pemilik"],
            "side": "mill",
            "points": _selang(nilai, lo, hi),
            "confidence": _keyakinan(nilai, lo, hi, True),
            "detail": v["dasar"],
            "action": v["tindakan"],
            "basis": None,
            "streams": [{"name": b["cause"], "points": b["points"]["value"]}
                        for b in isi],
        })

    for b in tak_terkelompok:
        penyebab.append({
            "cause": b["cause"], "owner": "Pabrik", "side": "mill",
            "points": b["points"], "confidence": b["confidence"],
            "detail": b.get("detail"), "action": None, "basis": None,
            "streams": [],
        })

    # --- yang tidak diatribusikan ke siapa pun ---
    u = kartu["unexplained"]
    penyebab.append({
        "cause": "Tidak terjelaskan",
        "owner": "Tidak dibebankan ke pihak mana pun",
        "side": "unknown",
        "points": u["points"],
        "confidence": u["confidence"],
        "detail": u.get("detail"),
        "action": "Periksa kalibrasi timbangan, kebocoran, dan koefisien "
                  "yang belum tertelusur.",
        "basis": None,
        "streams": [],
    })

    for p in penyebab:
        pt = p["points"]
        p["may_deduct_payment"] = (
            p["confidence"] == "high" and pt["lo"] * pt["hi"] > 0)
        p["action_threshold"] = AMBANG[p["confidence"]]

    penyebab.sort(key=lambda x: -abs(x["points"]["value"]))
    return penyebab
