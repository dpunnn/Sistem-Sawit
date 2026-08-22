"""Penerjemah istilah lapis AI ke kontrak HTTP.

ATURAN 3: backend adalah JEMBATAN, bukan pemilik logika. Berkas ini
adalah bentuk paling murni dari aturan itu — ia hanya menerjemahkan
nama, tidak menghitung apa pun.

## Kenapa istilahnya berbeda sejak awal

Lapis `ai/` memakai bahasa Indonesia karena seluruh penalaran domainnya
ditulis begitu: `rugi_komposisi`, `tak_terjelaskan`, `keyakinan`.
Kontrak HTTP memakai bahasa Inggris karena itu yang dipakai frontend,
Pydantic, dan siapa pun yang membaca OpenAPI nanti.

Menyatukan keduanya berarti salah satu sisi kehilangan bahasanya.
Menerjemahkan di banyak tempat berarti setiap penambahan kelas harus
dicari ke seluruh basis kode. Satu berkas ini adalah jalan tengahnya,
dan kecocokannya dijaga uji.
"""

from __future__ import annotations

# Tingkat kematangan: nama internal AI -> nama kontrak.
KELAS = {
    "mentah": "unripe",
    "kurang_masak": "underripe",
    "masak": "ripe",
    "terlalu_masak": "overripe",
}
KELAS_BALIK = {v: k for k, v in KELAS.items()}

# Pihak penanggung jawab.
PIHAK = {
    "pemasok": "supplier",
    "pabrik": "mill",
    "tidak_terjelaskan": "unknown",
}

# Tingkat keyakinan.
KEYAKINAN = {
    "tinggi": "high",
    "sedang": "medium",
    "rendah": "low",
}

# Nama aliran kehilangan -> nama stasiun pada kontrak & basis data.
STASIUN = {
    "kondensat_sterilizer": "condensate",
    "janjang_kosong": "empty_bunch",
    "ampas_kempa": "press_cake",
    "nut_in_fiber": "nut_in_fiber",
    "underflow_cst": "cst_underflow",
    "sludge_separator": "sludge",
    "fat_pit": "fat_pit",
    "deoiling_pond": "deoiling_pond",
}

# Label yang enak dibaca manusia, dipakai pada kartu neraca.
LABEL_STASIUN = {
    "condensate": "Sterilizer — kondensat",
    "empty_bunch": "Thresher — janjang kosong",
    "press_cake": "Press — ampas kempa",
    "nut_in_fiber": "Press — nut in fiber",
    "cst_underflow": "Klarifikasi — underflow CST",
    "sludge": "Klarifikasi — sludge separator",
    "fat_pit": "Klarifikasi — fat pit",
    "deoiling_pond": "Klarifikasi — deoiling pond",
}


def pihak(nama: str) -> str:
    """Terjemahkan pihak; yang tidak dikenal jadi 'unknown'.

    Sengaja TIDAK melempar error. Pihak yang tidak dikenal berarti ada
    sesuatu yang belum bisa diatribusikan, dan itu persis arti 'unknown'
    — jauh lebih baik daripada request gagal dan seluruh kartu hilang.
    """
    return PIHAK.get(nama, "unknown")


def keyakinan(nama: str) -> str:
    """Terjemahkan keyakinan; yang tidak dikenal jadi 'low'.

    Arah bawaannya disengaja: kalau sistem tidak tahu seberapa yakin
    dirinya, jawabannya bukan 'tinggi'.
    """
    return KEYAKINAN.get(nama, "low")


def kelas(nama: str) -> str:
    """Terjemahkan tingkat kematangan. Nama di luar sumbu dilewatkan apa
    adanya, karena `empty_bunch` dan `abnormal` memang bukan tingkat
    kematangan dan sudah memakai nama kontrak."""
    return KELAS.get(nama, nama)


# --------------------------------------------------------------------
# Bentuk JSONB di basis data
# --------------------------------------------------------------------
#
# Kolom `composition` memakai kunci pendek {v, lo, hi} sesuai skema di
# lampiran pipeline, sedangkan kontrak HTTP memakai {value, lo, hi}
# karena itu bentuk `Estimate`.
#
# Dua bentuk untuk kolom yang sama adalah undangan bagi bug, dan
# undangan itu sempat diterima: jalur tulis endpoint memakai `value`
# sementara jalur baca mencari `v`, sehingga /api/balance mengembalikan
# 500 begitu ada satu baris hasil endpoint di dalam shift. Konversinya
# sekarang hanya boleh lewat dua fungsi di bawah ini.

def komposisi_ke_db(komposisi: dict) -> dict:
    """Bentuk kontrak -> bentuk basis data."""
    return {k: {"v": round(v["value"], 2), "lo": round(v["lo"], 2),
                "hi": round(v["hi"], 2)}
            for k, v in komposisi.items()}


def komposisi_dari_db(komposisi: dict) -> dict:
    """Bentuk basis data -> bentuk kontrak.

    Menerima `v` maupun `value` supaya baris lama yang terlanjur
    tersimpan dengan bentuk lain tidak menjatuhkan seluruh endpoint.
    Toleransi ini untuk MEMBACA saja; yang ditulis selalu satu bentuk.
    """
    out = {}
    for k, v in komposisi.items():
        nilai = v["v"] if "v" in v else v["value"]
        out[k] = {"value": float(nilai), "lo": float(v["lo"]), "hi": float(v["hi"])}
    return out
