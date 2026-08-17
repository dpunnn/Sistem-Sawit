"""Pemuat koefisien domain — dengan penegakan disiplin.

Berkas `coefficients.yaml` menyatakan aturan: setiap angka wajib punya
sumber, dan angka berstatus `perlu_verifikasi` tidak boleh dipakai untuk
perhitungan yang dilaporkan ke petani.

Modul ini membuat aturan itu **ditegakkan kode**, bukan sekadar tertulis:

- `get()` menolak koefisien tanpa `sumber`
- `get()` menolak koefisien `perlu_verifikasi`, kecuali pemanggil
  menyatakan `izinkan_belum_terverifikasi=True` secara eksplisit
- `audit()` melaporkan seluruh koefisien beserta status dan sumbernya,
  sehingga dasar ilmiah sistem dapat diperiksa dari satu perintah

Alasan desainnya sederhana: keluaran sistem ini memotong uang orang.
Angka yang basisnya belum jelas tidak boleh menyelinap ke perhitungan
hanya karena seseorang lupa memeriksa.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = Path(os.environ.get(
    "COEFFICIENTS_PATH", ROOT / "ai" / "config" / "coefficients.yaml"))

TERVERIFIKASI = "terverifikasi"
PERLU_VERIFIKASI = "perlu_verifikasi"


class KoefisienError(RuntimeError):
    """Dilempar saat koefisien tidak memenuhi syarat pemakaian."""


@dataclass(frozen=True)
class Koefisien:
    """Satu koefisien beserta jejak asalnya."""

    jalur: str
    nilai: float | list[float]
    satuan: str | None
    status: str
    sumber_kunci: str
    sumber: dict[str, Any]
    catatan: str | None = None

    @property
    def terverifikasi(self) -> bool:
        return self.status == TERVERIFIKASI

    def __str__(self) -> str:
        tanda = "OK " if self.terverifikasi else "CEK"
        return f"[{tanda}] {self.jalur} = {self.nilai} ({self.sumber_kunci})"


@lru_cache(maxsize=4)
def _muat(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise KoefisienError(f"berkas koefisien tidak ditemukan: {p}")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _telusuri(data: dict, jalur: str) -> Any:
    node: Any = data
    for bagian in jalur.split("."):
        if not isinstance(node, dict) or bagian not in node:
            raise KoefisienError(f"jalur koefisien tidak ada: {jalur}")
        node = node[bagian]
    return node


def get(jalur: str, *, izinkan_belum_terverifikasi: bool = False,
        path: Path | str | None = None) -> Koefisien:
    """Ambil satu koefisien.

    Parameters
    ----------
    jalur
        Jalur bertitik, mis. ``"kematangan.penalti_buah_mentah"``.
    izinkan_belum_terverifikasi
        Harus dinyatakan eksplisit untuk memakai koefisien yang basisnya
        belum dipastikan. Dipakai simulator, TIDAK boleh dipakai jalur
        perhitungan yang dilaporkan ke petani.
    """
    data = _muat(str(path or DEFAULT_PATH))
    node = _telusuri(data, jalur)

    if not isinstance(node, dict):
        raise KoefisienError(
            f"{jalur} bukan koefisien (tidak punya metadata). "
            f"Setiap angka wajib disertai `sumber` dan `status`.")

    if "nilai" in node:
        nilai = node["nilai"]
    elif "rentang" in node:
        nilai = node["rentang"]
    else:
        raise KoefisienError(f"{jalur} tidak punya `nilai` maupun `rentang`")

    sumber_kunci = node.get("sumber")
    if not sumber_kunci:
        raise KoefisienError(
            f"{jalur} tidak punya `sumber`. Koefisien tanpa sumber ditolak — "
            f"dasar perhitungan harus bisa ditelusuri.")

    daftar_sumber = data.get("sumber", {})
    if sumber_kunci not in daftar_sumber:
        raise KoefisienError(
            f"{jalur} merujuk sumber '{sumber_kunci}' yang tidak "
            f"terdaftar di blok `sumber:`")

    status = node.get("status", PERLU_VERIFIKASI)
    if status != TERVERIFIKASI and not izinkan_belum_terverifikasi:
        raise KoefisienError(
            f"{jalur} berstatus '{status}' dan tidak boleh dipakai untuk "
            f"perhitungan yang dilaporkan.\n"
            f"  Catatan: {node.get('catatan', '(tidak ada)')}\n"
            f"  Jika ini memang untuk simulator atau eksplorasi, panggil "
            f"dengan izinkan_belum_terverifikasi=True.")

    return Koefisien(
        jalur=jalur, nilai=nilai, satuan=node.get("satuan"), status=status,
        sumber_kunci=sumber_kunci, sumber=daftar_sumber[sumber_kunci],
        catatan=node.get("catatan"),
    )


def nilai(jalur: str, **kw) -> float:
    """Pintasan: ambil angkanya saja."""
    k = get(jalur, **kw)
    if isinstance(k.nilai, list):
        raise KoefisienError(f"{jalur} berupa rentang, bukan nilai tunggal")
    return float(k.nilai)


def _kumpulkan(node: Any, prefix: str = "") -> list[tuple[str, dict]]:
    keluar = []
    if isinstance(node, dict):
        if "nilai" in node or "rentang" in node:
            keluar.append((prefix, node))
        else:
            for k, v in node.items():
                keluar.extend(_kumpulkan(v, f"{prefix}.{k}" if prefix else k))
    return keluar


def audit(path: Path | str | None = None) -> dict:
    """Periksa seluruh koefisien: berapa terverifikasi, mana yang belum.

    Dipakai sebagai pemeriksaan kesehatan sekaligus lampiran proposal —
    seluruh dasar ilmiah sistem dapat dibaca dari satu keluaran.
    """
    data = _muat(str(path or DEFAULT_PATH))
    lewati = {"meta", "sumber", "tidak_dipakai"}
    semua = []
    for kunci, isi in data.items():
        if kunci in lewati:
            continue
        semua.extend(_kumpulkan(isi, kunci))

    ok, cek, tanpa_sumber = [], [], []
    for jalur, node in semua:
        if not node.get("sumber"):
            tanpa_sumber.append(jalur)
        elif node.get("status") == TERVERIFIKASI:
            ok.append(jalur)
        else:
            cek.append(jalur)

    return {
        "total": len(semua),
        "terverifikasi": ok,
        "perlu_verifikasi": cek,
        "tanpa_sumber": tanpa_sumber,
        "jumlah_sumber": len(data.get("sumber", {})),
        "sehat": len(tanpa_sumber) == 0,
    }


if __name__ == "__main__":
    hasil = audit()
    print("=" * 66)
    print("AUDIT KOEFISIEN DOMAIN")
    print("=" * 66)
    print(f"Total koefisien   : {hasil['total']}")
    print(f"Terverifikasi     : {len(hasil['terverifikasi'])}")
    print(f"Perlu verifikasi  : {len(hasil['perlu_verifikasi'])}")
    print(f"Tanpa sumber      : {len(hasil['tanpa_sumber'])}")
    print(f"Sumber terdaftar  : {hasil['jumlah_sumber']}")
    print("-" * 66)
    if hasil["perlu_verifikasi"]:
        print("BELUM TERVERIFIKASI — tidak boleh dipakai untuk perhitungan")
        print("yang dilaporkan ke petani:")
        for j in hasil["perlu_verifikasi"]:
            print(f"  - {j}")
    if hasil["tanpa_sumber"]:
        print("\nTANPA SUMBER — harus diperbaiki:")
        for j in hasil["tanpa_sumber"]:
            print(f"  - {j}")
    print("=" * 66)
    print("SEHAT" if hasil["sehat"] else "ADA KOEFISIEN TANPA SUMBER")
