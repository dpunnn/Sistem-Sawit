"""Simulator pabrik — neraca massa deterministik, SEEDABLE.

## Kenapa simulator, bukan data pabrik

Data proses harian pabrik kelapa sawit TIDAK PUBLIK. Meminta satu pun
angka rendemen harian ke pabrik berarti meminta data yang jadi dasar
sengketa harga dengan pemasoknya sendiri. Simulator yang seluruh
koefisiennya terpublikasi dan bisa dijalankan ulang orang lain adalah
penggantinya yang jujur — dan lebih baik untuk pengujian, karena
kebenarannya diketahui.

Yang TIDAK boleh diklaim: bahwa simulator ini memvalidasi Model 5
terhadap kenyataan. Yang divalidasi adalah bahwa **aritmetika neracanya
benar** dan **atribusinya bisa memulihkan gangguan yang ditanam**.

## Bentuk neraca yang dihasilkan

    OER teoretis            basis_matang (21,00 poin)
      - rugi komposisi        <- SISI PEMASOK, dari kematangan buah
      - rugi restan           <- sisi pabrik, buah menunggu diolah
      = OER realistis
      - rugi proses           <- SISI PABRIK, 8 aliran kehilangan
      = OER aktual

## Cara kehilangan proses dihitung

Angka studi kasus (kondensat 1,83, janjang kosong 2,44, ...) adalah
KADAR MINYAK DI DALAM ALIRAN, bukan persen terhadap TBS. Menjumlahkannya
langsung memberi 18,01 dan rendemen mustahil. Yang benar:

    kehilangan_poin_i = kadar_i x nisbah_massa_i

Dengan nisbah massa taksiran, totalnya mendarat di 1,67 poin — sesuai
norma industri 1,5-1,75 poin. Nisbah itu berstatus perlu_verifikasi dan
disebut demikian di mana-mana.

## Gangguan yang bisa ditanam

Supaya Model 6 punya sesuatu untuk ditemukan. Tiap gangguan mengubah
BEBERAPA aliran sekaligus dengan pola khas — itulah tanda tangan yang
harus dipulihkan, bukan satu angka tunggal.

Jalankan:
    python ai/simulator/mill.py                 # peragaan + swauji
    python ai/simulator/mill.py --n-hari 180    # bangkitkan riwayat
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.config import coefficients as C

# Delapan aliran kehilangan, dengan kadar acuan dari studi kasus.
ALIRAN = [
    "kondensat_sterilizer",
    "janjang_kosong",
    "ampas_kempa",
    "nut_in_fiber",
    "underflow_cst",
    "sludge_separator",
    "fat_pit",
    "deoiling_pond",
]

PENALTI_KOMPOSISI = {
    "mentah": "kematangan.penalti_buah_mentah",
    "kurang_masak": "kematangan.penalti_kurang_masak",
    "masak": None,
    "terlalu_masak": "kematangan.penalti_terlalu_masak",
}

# --------------------------------------------------------------------
# GANGGUAN
# --------------------------------------------------------------------
# Tiap gangguan adalah pengali terhadap kadar acuan aliran. Polanya
# dibuat menyerupai sebab-akibat mekanis yang sebenarnya, bukan angka
# acak, supaya soal yang dihadapi Model 6 punya struktur yang memang
# ada di dunia nyata.
#
# Yang membuat soalnya tidak sepele: beberapa gangguan BERBAGI aliran.
# Perebusan kurang matang dan kempa aus sama-sama menaikkan ampas kempa.
# Yang membedakan adalah aliran LAIN yang ikut naik.
GANGGUAN: dict[str, dict[str, float]] = {
    "normal": {},
    "perebusan_kurang_matang": {
        # uap tidak cukup -> buah tidak lepas dari janjang, minyak
        # terbawa keluar bersama tandan kosong; ampas ikut naik sedikit
        "janjang_kosong": 1.85,
        "ampas_kempa": 1.15,
        "kondensat_sterilizer": 0.92,
    },
    "perebusan_berlebih": {
        # kebalikannya: minyak lolos ke air kondensat
        "kondensat_sterilizer": 1.90,
        "janjang_kosong": 0.88,
    },
    "kempa_aus": {
        # ulir aus / tekanan turun -> minyak tertinggal di ampas,
        # biji ikut terbawa serat
        "ampas_kempa": 1.55,
        "nut_in_fiber": 1.70,
    },
    "cst_dingin": {
        # suhu CST turun -> pemisahan gravitasi gagal, minyak lolos
        # ke bawah dan meneruskan diri ke seluruh rangkaian limbah
        "underflow_cst": 1.60,
        "sludge_separator": 1.45,
        "fat_pit": 1.35,
        "deoiling_pond": 1.30,
    },
    "sludge_separator_tersumbat": {
        "sludge_separator": 2.10,
        "fat_pit": 1.25,
    },
}


@dataclass
class HasilPengolahan:
    """Neraca satu hari giling, lengkap dengan kebenaran tersembunyi."""

    oer_teoretis: float
    rugi_komposisi: float          # negatif, sisi pemasok
    rugi_restan: float             # negatif, sisi pabrik
    oer_realistis: float
    rugi_proses: float             # negatif, sisi pabrik
    oer_aktual: float
    minyak_kg: float
    kehilangan_aliran: dict[str, float] = field(default_factory=dict)
    kadar_aliran: dict[str, float] = field(default_factory=dict)
    # --- kebenaran yang hanya diketahui simulator ---
    _gangguan: str = "normal"

    def sebagai_baris(self) -> dict:
        d = {
            "oer_teoretis": self.oer_teoretis,
            "rugi_komposisi": self.rugi_komposisi,
            "rugi_restan": self.rugi_restan,
            "oer_realistis": self.oer_realistis,
            "rugi_proses": self.rugi_proses,
            "oer_aktual": self.oer_aktual,
            "minyak_kg": self.minyak_kg,
        }
        d.update({f"poin_{k}": v for k, v in self.kehilangan_aliran.items()})
        d.update({f"kadar_{k}": v for k, v in self.kadar_aliran.items()})
        d["_gangguan"] = self._gangguan
        return d


class Pabrik:
    """Pabrik dengan koefisien tetap; keacakan hanya dari seed.

    Dua contoh Pabrik dengan seed sama menghasilkan urutan hari yang
    identik. Itu syarat supaya pengujian Model 5 dan 6 bisa diulang
    orang lain.
    """

    def __init__(self, *, mode: str = "lengkap", seed: int = 42,
                 ragam_proses: float = 0.06):
        # Simulator memakai mode lengkap: ia menirukan kenyataan, dan
        # kenyataan tidak menunggu koefisien terverifikasi. Model 5 yang
        # MEMBACA hasilnya boleh lebih berhati-hati — perbedaan itulah
        # yang jadi selisih tak terjelaskan.
        self.izin = mode != "terverifikasi"
        self.rng = np.random.default_rng(seed)
        self.ragam_proses = ragam_proses

        self.basis = C.nilai("rendemen.basis_matang")
        self.penalti = {
            k: (0.0 if j is None
                else C.nilai(j, izinkan_belum_terverifikasi=self.izin))
            for k, j in PENALTI_KOMPOSISI.items()
        }
        self.restan_per_jam = C.nilai(
            "restan.penalti_per_jam", izinkan_belum_terverifikasi=self.izin)
        self.kadar_acuan = {
            a: C.nilai(f"oil_loss.aktual_studi_kasus.{a}") for a in ALIRAN
        }
        self.nisbah = {
            a: C.nilai(f"oil_loss.nisbah_massa.{a}",
                       izinkan_belum_terverifikasi=self.izin)
            for a in ALIRAN
        }

    # -- komponen -----------------------------------------------------

    def kehilangan_proses_acuan(self) -> float:
        """Total kehilangan proses tanpa gangguan, dalam poin rendemen."""
        return sum(self.kadar_acuan[a] * self.nisbah[a] for a in ALIRAN)

    def _kadar_hari_ini(self, gangguan: str) -> dict[str, float]:
        pengali = GANGGUAN[gangguan]
        kadar = {}
        for a in ALIRAN:
            # ragam harian normal — pengambilan contoh laboratorium
            # memang tidak pernah memberi angka yang sama dua kali
            derau = self.rng.normal(1.0, self.ragam_proses)
            kadar[a] = max(0.0, self.kadar_acuan[a] * pengali.get(a, 1.0) * derau)
        return kadar

    # -- satu hari ----------------------------------------------------

    def olah(self, komposisi: dict[str, float], berat_bruto_kg: float, *,
             jam_restan: float = 0.0, gangguan: str = "normal"
             ) -> HasilPengolahan:
        if gangguan not in GANGGUAN:
            raise ValueError(
                f"gangguan '{gangguan}' tidak dikenal. Pilihan: {list(GANGGUAN)}")
        total = sum(komposisi.values())
        if not 0.98 <= total <= 1.02:
            raise ValueError(f"komposisi harus berjumlah 1,0 (dapat {total:.4f})")

        # Penalti bersatuan POIN PER PERSEN, sama seperti Model 4
        # (ai/perception/potential.py). Memakai fraksi di sini akan
        # meleset 100x dan membuat rugi komposisi nyaris hilang.
        rugi_komposisi = sum(komposisi.get(k, 0.0) * 100.0 * self.penalti[k]
                             for k in PENALTI_KOMPOSISI)
        rugi_restan = jam_restan * self.restan_per_jam

        kadar = self._kadar_hari_ini(gangguan)
        per_aliran = {a: -kadar[a] * self.nisbah[a] for a in ALIRAN}
        rugi_proses = sum(per_aliran.values())

        oer_realistis = self.basis + rugi_komposisi + rugi_restan
        oer_aktual = oer_realistis + rugi_proses

        return HasilPengolahan(
            oer_teoretis=self.basis,
            rugi_komposisi=rugi_komposisi,
            rugi_restan=rugi_restan,
            oer_realistis=oer_realistis,
            rugi_proses=rugi_proses,
            oer_aktual=oer_aktual,
            minyak_kg=berat_bruto_kg * oer_aktual / 100.0,
            kehilangan_aliran=per_aliran,
            kadar_aliran=kadar,
            _gangguan=gangguan,
        )

    # -- riwayat ------------------------------------------------------

    def riwayat(self, n_hari: int = 120, *,
                peluang_gangguan: float = 0.35,
                panjang_gangguan: tuple[int, int] = (3, 14)) -> pd.DataFrame:
        """Bangkitkan riwayat giling harian.

        Gangguan datang dalam PERIODE, bukan hari tunggal acak. Kerusakan
        alat nyata berlangsung sampai diperbaiki, dan Model 6 harus bisa
        memanfaatkan kegigihan itu.
        """
        jenis = [g for g in GANGGUAN if g != "normal"]
        jadwal = ["normal"] * n_hari
        hari = 0
        while hari < n_hari:
            if self.rng.random() < peluang_gangguan:
                g = jenis[self.rng.integers(len(jenis))]
                panjang = int(self.rng.integers(*panjang_gangguan))
                for h in range(hari, min(n_hari, hari + panjang)):
                    jadwal[h] = g
                hari += panjang
            else:
                hari += int(self.rng.integers(2, 10))

        baris = []
        for h in range(n_hari):
            # mutu pemasok bergerak musiman: musim hujan menaikkan buah
            # mentah karena panen dipercepat sebelum akses jalan tutup
            musim = 0.5 + 0.5 * np.sin(2 * np.pi * h / 90.0)
            mentah = float(np.clip(self.rng.normal(0.06 + 0.10 * musim, 0.03),
                                   0.0, 0.45))
            kurang = float(np.clip(self.rng.normal(0.14, 0.05), 0.0, 0.40))
            terlalu = float(np.clip(self.rng.normal(0.05, 0.025), 0.0, 0.20))
            komposisi = {
                "mentah": mentah, "kurang_masak": kurang,
                "terlalu_masak": terlalu,
                "masak": max(0.0, 1.0 - mentah - kurang - terlalu),
            }
            s = sum(komposisi.values())
            komposisi = {k: v / s for k, v in komposisi.items()}

            berat = float(self.rng.uniform(180_000, 420_000))
            jam = float(np.clip(self.rng.gamma(2.0, 4.0), 0, 48))

            r = self.olah(komposisi, berat, jam_restan=jam,
                          gangguan=jadwal[h])
            b = r.sebagai_baris()
            b["hari"] = h
            b["berat_bruto_kg"] = berat
            b["jam_restan"] = jam
            b.update({f"komposisi_{k}": v for k, v in komposisi.items()})
            baris.append(b)

        kol = ["hari", "berat_bruto_kg", "jam_restan"]
        df = pd.DataFrame(baris)
        return df[kol + [c for c in df.columns if c not in kol]]


# --------------------------------------------------------------------
# SWAUJI
# --------------------------------------------------------------------

def swauji(verbose: bool = True) -> dict:
    """Pemeriksaan yang harus lolos sebelum simulator boleh dipakai."""
    hasil = {}
    p = Pabrik(seed=42)

    # 1. Kehilangan proses acuan mendarat di norma industri 1,5-1,75 poin.
    #    Kalau nisbah massanya salah besar, uji ini yang gagal duluan.
    acuan = p.kehilangan_proses_acuan()
    hasil["kehilangan_acuan"] = acuan
    hasil["lulus_norma"] = 1.4 <= acuan <= 1.9

    # 2. Neraca harus tertutup: tiap baris = baris sebelumnya + selisihnya.
    #    Ini yang mencegah kesalahan tanda dan penghitungan ganda.
    r = p.olah({"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                "terlalu_masak": 0.05}, 200_000, jam_restan=8.0)
    sisa1 = abs((r.oer_teoretis + r.rugi_komposisi + r.rugi_restan)
                - r.oer_realistis)
    sisa2 = abs((r.oer_realistis + r.rugi_proses) - r.oer_aktual)
    sisa3 = abs(sum(r.kehilangan_aliran.values()) - r.rugi_proses)
    hasil["sisa_neraca"] = max(sisa1, sisa2, sisa3)
    hasil["lulus_tertutup"] = hasil["sisa_neraca"] < 1e-9

    # 3. Determinisme: seed sama -> hasil identik, bit demi bit.
    a = Pabrik(seed=7).riwayat(40)
    b = Pabrik(seed=7).riwayat(40)
    hasil["lulus_deterministik"] = a.equals(b)
    hasil["lulus_seed_beda"] = not Pabrik(seed=8).riwayat(40).equals(a)

    # 4. Tiap gangguan harus MENURUNKAN rendemen. Gangguan yang menaikkan
    #    rendemen berarti tanda pengalinya terbalik.
    komp = {"mentah": 0.10, "kurang_masak": 0.15, "masak": 0.70,
            "terlalu_masak": 0.05}
    dasar = Pabrik(seed=3, ragam_proses=0.0).olah(komp, 200_000).oer_aktual
    turun = {}
    for g in GANGGUAN:
        if g == "normal":
            continue
        oer = Pabrik(seed=3, ragam_proses=0.0).olah(
            komp, 200_000, gangguan=g).oer_aktual
        turun[g] = dasar - oer
    hasil["penurunan_per_gangguan"] = turun
    hasil["lulus_arah"] = all(v > 0 for v in turun.values())

    # 5. Rugi komposisi simulator HARUS identik dengan Model 4. Kalau
    #    dua modul menghitung hal yang sama dengan cara berbeda, salah
    #    satunya pasti salah — dan pernah memang salah 100x di sini.
    from ai.perception import potential as M4
    komp_uji = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                "terlalu_masak": 0.05}
    p_lkp = Pabrik(seed=1, ragam_proses=0.0)
    r_sim = p_lkp.olah(komp_uji, 100_000)
    r_m4 = M4.hitung(komp_uji, 100_000, mode="lengkap")
    hasil["beda_dengan_model4"] = abs(r_sim.rugi_komposisi - r_m4.rugi_komposisi)
    hasil["lulus_cocok_model4"] = hasil["beda_dengan_model4"] < 1e-9

    # 6. Rendemen aktual harus berada di rentang yang mungkin secara fisik.
    df = Pabrik(seed=11).riwayat(200)
    normal = df[df._gangguan == "normal"]["oer_aktual"]
    hasil["oer_normal_rerata"] = float(normal.mean())
    hasil["oer_rentang"] = (float(df.oer_aktual.min()), float(df.oer_aktual.max()))
    hasil["lulus_masuk_akal"] = 14.0 <= normal.mean() <= 20.0

    # 7. Berapa persen buah mentah yang membuat neraca menutup TEPAT di
    #    rendemen TBS petani swadaya yang terpublikasi (18,88)? Jawabannya
    #    adalah temuan, bukan sekadar uji: kalau angkanya jauh lebih kecil
    #    daripada laporan lapangan, berarti koefisien terbit yang dipakai
    #    saling bertentangan — dan itu harus disebut, bukan ditutupi.
    acuan_swadaya = C.nilai("rendemen.tbs_petani_swadaya")
    p0 = Pabrik(seed=5, ragam_proses=0.0)
    sisa_untuk_komposisi = (acuan_swadaya - p0.basis
                            - p0.olah({"masak": 1.0}, 1000).rugi_proses)
    # sisa_untuk_komposisi negatif = poin yang tersedia untuk rugi mutu
    pers_mentah_setara = abs(sisa_untuk_komposisi) / abs(
        p0.penalti["mentah"]) if p0.penalti["mentah"] else float("nan")
    hasil["persen_mentah_setara_1888"] = float(pers_mentah_setara)

    hasil["lulus_semua"] = all(v for k, v in hasil.items()
                               if k.startswith("lulus_"))

    if verbose:
        print("=" * 62)
        print("SWAUJI SIMULATOR PABRIK")
        print("=" * 62)
        print(f"  kehilangan proses acuan : {acuan:.3f} poin "
              f"(norma industri 1,5-1,75)   "
              f"{'LULUS' if hasil['lulus_norma'] else 'GAGAL'}")
        print(f"  neraca tertutup         : sisa {hasil['sisa_neraca']:.2e}"
              f"                    "
              f"{'LULUS' if hasil['lulus_tertutup'] else 'GAGAL'}")
        print(f"  deterministik (seed 7)  : "
              f"{'LULUS' if hasil['lulus_deterministik'] else 'GAGAL'}")
        print(f"  seed beda -> hasil beda : "
              f"{'LULUS' if hasil['lulus_seed_beda'] else 'GAGAL'}")
        print(f"  semua gangguan merugi   : "
              f"{'LULUS' if hasil['lulus_arah'] else 'GAGAL'}")
        print(f"  rugi komposisi = Model 4: beda {hasil['beda_dengan_model4']:.2e}"
              f"                   "
              f"{'LULUS' if hasil['lulus_cocok_model4'] else 'GAGAL'}")
        print(f"  OER normal rerata       : {hasil['oer_normal_rerata']:.2f} poin "
              f"(rentang {hasil['oer_rentang'][0]:.1f}-{hasil['oer_rentang'][1]:.1f})  "
              f"{'LULUS' if hasil['lulus_masuk_akal'] else 'GAGAL'}")
        print("-" * 62)
        print("  penurunan rendemen per gangguan (poin):")
        for g, v in sorted(turun.items(), key=lambda x: -x[1]):
            print(f"    {g:28s} -{v:.3f}")
        print("-" * 62)
        print("  TEMUAN — pertentangan antar koefisien terbit:")
        print(f"    supaya neraca menutup tepat di rendemen swadaya "
              f"terpublikasi\n    (18,88 poin), buah mentah harus hanya "
              f"{hasil['persen_mentah_setara_1888']:.1f}% dan sisanya sempurna.")
        print("    Laporan lapangan menyebut 10-15%. Selisih itu NYATA dan")
        print("    tidak boleh disembunyikan — justru itu yang dilaporkan")
        print("    Model 5 sebagai bagian tak terjelaskan.")
        print("=" * 62)
    return hasil


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-hari", type=int, default=0,
                    help="kalau >0, bangkitkan riwayat dan simpan")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="data/processed/pabrik")
    args = ap.parse_args()

    h = swauji()
    if not h["lulus_semua"]:
        print("\n[GAGAL] swauji tidak lolos — simulator tidak boleh dipakai")
        return 1

    if args.n_hari > 0:
        root = Path(__file__).resolve().parents[2]
        out = root / args.out
        out.mkdir(parents=True, exist_ok=True)
        df = Pabrik(seed=args.seed).riwayat(args.n_hari)
        df.to_parquet(out / "riwayat_giling.parquet", index=False)
        print()
        print(f"riwayat {len(df)} hari -> {out / 'riwayat_giling.parquet'}")
        print(df.groupby("_gangguan").agg(
            hari=("hari", "size"),
            oer_rerata=("oer_aktual", "mean"),
        ).round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
