"""Mengukur apakah Model 6 benar-benar MENEMUKAN KEMBALI aturannya.

Model 6 tidak pernah melihat label gangguan. Ia hanya melihat delapan
hasil ukur laboratorium per hari. Pertanyaan yang dijawab berkas ini:

    Apakah pola yang ia temukan sendiri benar-benar pola yang ditanam,
    atau kebetulan yang kelihatan meyakinkan?

Cara mengukurnya: tiap gangguan punya tanda tangan sebenarnya — vektor
arah kenaikan delapan aliran. Pola temuan Model 6 juga vektor arah.
Kecocokannya diukur dengan kosinus, lalu dipasangkan satu-satu memakai
Hungarian supaya tidak ada pola yang dipakai dua kali untuk mengaku
berhasil dua kali.

## Yang diuji

1. Pemulihan aturan pada keadaan dasar.
2. Ketahanan terhadap derau laboratorium yang makin besar.
3. Ketahanan terhadap perancu yang tidak dimodelkan (penuaan alat).
4. Berapa hari riwayat yang sebenarnya dibutuhkan.
5. Sensitivitas Model 5 terhadap koefisien yang meleset +/-15%.

Jalankan:
    python ai/evaluation/rule_recovery.py
    python ai/evaluation/rule_recovery.py --cepat
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.reasoning.attribution import Model6
from ai.simulator.mill import ALIRAN, GANGGUAN, Pabrik

# Ambang "berhasil dipulihkan". Kosinus 0,80 antara dua vektor 8 dimensi
# jauh di atas kebetulan: dua arah acak di R^8 rata-rata berkosinus nol
# dengan simpangan ~0,35.
AMBANG_PULIH = 0.80


def tanda_tangan_sebenarnya() -> dict[str, np.ndarray]:
    """Arah kenaikan tiap gangguan, dinormalkan.

    Diambil langsung dari kamus GANGGUAN di simulator — inilah kunci
    jawaban yang tidak pernah diperlihatkan ke Model 6.
    """
    ttd = {}
    for nama, pengali in GANGGUAN.items():
        if not pengali:
            continue
        v = np.array([pengali.get(a, 1.0) - 1.0 for a in ALIRAN])
        ttd[nama] = v / max(np.linalg.norm(v), 1e-9)
    return ttd


def cocokkan(pola: dict[str, np.ndarray]) -> pd.DataFrame:
    """Pasangkan pola temuan dengan gangguan sebenarnya, satu-satu.

    Hungarian, bukan "ambil yang termirip". Tanpa pemasangan satu-satu,
    satu pola bagus bisa diklaim sebagai keberhasilan untuk lima
    gangguan sekaligus.
    """
    ttd = tanda_tangan_sebenarnya()
    nama_asli = list(ttd)
    nama_temu = list(pola)
    if not nama_temu:
        return pd.DataFrame([{"gangguan": g, "pola_temuan": None, "kosinus": 0.0,
                              "pulih": False} for g in nama_asli])

    K = np.array([[float(np.dot(ttd[g], pola[p])) for p in nama_temu]
                  for g in nama_asli])
    baris, kolom = linear_sum_assignment(-K)
    pasangan = dict(zip(baris, kolom))

    out = []
    for i, g in enumerate(nama_asli):
        j = pasangan.get(i)
        k = float(K[i, j]) if j is not None else 0.0
        out.append({"gangguan": g,
                    "pola_temuan": nama_temu[j] if j is not None else None,
                    "kosinus": k, "pulih": k >= AMBANG_PULIH})
    return pd.DataFrame(out)


# Perancu terpilih hanya menyentuh tiga aliran. Bentuk ini jauh lebih
# berbahaya daripada penuaan menyeluruh: ia PUNYA arah, sehingga bisa
# disangka pola kerusakan dan melahirkan tuduhan atas sesuatu yang
# sebenarnya hanya alat menua.
ALIRAN_MENUA = ["ampas_kempa", "nut_in_fiber", "kondensat_sterilizer"]


def _riwayat(n_hari: int, seed: int, ragam: float,
             penuaan: float = 0.0, terpilih: bool = False) -> pd.DataFrame:
    """Bangkitkan riwayat, opsional dengan perancu penuaan alat.

    Penuaan menaikkan aliran perlahan sepanjang waktu. Ia bukan
    gangguan — tidak ada pihak yang bisa dituduh karenanya — tapi ia
    menggeser dasar normal. Kalau Model 6 mengarangnya jadi pola
    kerusakan tersendiri, itu tuduhan palsu.

    `terpilih=True` membatasi penuaan ke tiga aliran saja, sehingga
    perancunya berarah dan bisa tertukar dengan kerusakan sungguhan.
    """
    df = Pabrik(seed=seed, ragam_proses=ragam).riwayat(n_hari)
    if penuaan > 0:
        faktor = 1.0 + penuaan * (df["hari"].to_numpy() / max(n_hari - 1, 1))
        kena = ALIRAN_MENUA if terpilih else ALIRAN
        for a in kena:
            df[f"poin_{a}"] = df[f"poin_{a}"].to_numpy() * faktor
    return df


def uji(n_hari: int = 400, seed: int = 42, ragam: float = 0.06,
        penuaan: float = 0.0, terpilih: bool = False) -> dict:
    """Satu percobaan pemulihan aturan."""
    df = _riwayat(n_hari, seed, ragam, penuaan, terpilih)
    m = Model6(seed=seed).pelajari(df)
    tabel = cocokkan(m.pola_)

    # Salah tuduh: hari normal yang diberi label anomali. Ini kesalahan
    # yang paling mahal secara sosial — menuduh pabrik atau pemasok atas
    # sesuatu yang tidak terjadi.
    normal = df[df["_gangguan"] == "normal"]
    salah_tuduh = float(np.mean([m.diagnosa(r).anomali
                                 for _, r in normal.iterrows()])) if len(normal) else float("nan")

    # Terlewat: hari rusak yang dinyatakan normal.
    rusak = df[df["_gangguan"] != "normal"]
    terlewat = float(np.mean([not m.diagnosa(r).anomali
                              for _, r in rusak.iterrows()])) if len(rusak) else float("nan")

    return {
        "n_hari": n_hari, "ragam": ragam, "penuaan": penuaan,
        "terpilih": terpilih,
        "n_pola_ditemukan": len(m.pola_),
        "n_gangguan_sebenarnya": len(tanda_tangan_sebenarnya()),
        "pulih": int(tabel["pulih"].sum()),
        "kosinus_rerata": float(tabel["kosinus"].mean()),
        "kosinus_min": float(tabel["kosinus"].min()),
        "siluet": float(getattr(m, "siluet_", np.nan)),
        "salah_tuduh": salah_tuduh,
        "terlewat": terlewat,
        "tabel": tabel,
    }


# --------------------------------------------------------------------
# SENSITIVITAS KOEFISIEN — ini menyangkut Model 5, bukan Model 6
# --------------------------------------------------------------------

def sensitivitas_koefisien(galat: float = 0.15, seed: int = 42) -> pd.DataFrame:
    """Kalau nisbah massa meleset +/-15%, seberapa jauh neraca bergeser?

    Nisbah massa berstatus perlu_verifikasi. Pertanyaan yang wajar dari
    juri maupun pabrik: kalau angka itu salah, apakah kesimpulannya
    berubah? Yang diukur di sini adalah pergeseran baris tak
    terjelaskan — baris yang paling peka karena ia menampung semua
    yang tidak cocok.
    """
    from ai.reasoning import balance as M5

    komposisi = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                 "terlalu_masak": 0.05}
    berat = 240_000.0
    p = Pabrik(seed=seed, ragam_proses=0.0)
    h = p.olah(komposisi, berat, jam_restan=9.0)

    baris = []
    for f in [1 - galat, 1.0, 1 + galat]:
        hilang = {k: abs(v) * f for k, v in h.kehilangan_aliran.items()}
        for mode in ["terverifikasi", "lengkap"]:
            k = M5.susun(komposisi, berat, h.minyak_kg,
                         kehilangan_pabrik_poin=hilang, jam_restan=9.0,
                         mode=mode)
            pangsa = k.bagi_tanggung_jawab()
            baris.append({
                "faktor_nisbah": round(f, 3), "mode": mode,
                "pemasok_poin": round(k.total_pemasok_poin, 3),
                "pabrik_poin": round(k.total_pabrik_poin, 3),
                "tak_terjelaskan_poin": round(k.tak_terjelaskan.poin, 3),
                "pangsa_pemasok": round(pangsa["pemasok"], 3),
            })
    return pd.DataFrame(baris)


# --------------------------------------------------------------------

def laporan(cepat: bool = False) -> dict:
    L = 74
    hasil = {}

    print("=" * L)
    print("PEMULIHAN ATURAN — dasar")
    print("=" * L)
    dasar = uji(n_hari=400)
    print(dasar["tabel"].to_string(index=False))
    print()
    print(f"  pola ditemukan   : {dasar['n_pola_ditemukan']} "
          f"(gangguan sebenarnya {dasar['n_gangguan_sebenarnya']})")
    print(f"  pulih (kos>={AMBANG_PULIH}) : {dasar['pulih']}/"
          f"{dasar['n_gangguan_sebenarnya']}")
    print(f"  kosinus rerata   : {dasar['kosinus_rerata']:.3f}   "
          f"terendah {dasar['kosinus_min']:.3f}")
    print(f"  siluet kelompok  : {dasar['siluet']:.3f}")
    print(f"  salah tuduh hari normal : {dasar['salah_tuduh']:.1%}")
    print(f"  hari rusak terlewat     : {dasar['terlewat']:.1%}")
    hasil["dasar"] = dasar

    print()
    print("=" * L)
    print("KETAHANAN 1 — derau laboratorium makin besar")
    print("=" * L)
    ragam_uji = [0.06, 0.12] if cepat else [0.06, 0.10, 0.15, 0.22]
    b = [uji(n_hari=400, ragam=r) for r in ragam_uji]
    t1 = pd.DataFrame([{k: v for k, v in x.items() if k != "tabel"} for x in b])
    print(t1[["ragam", "n_pola_ditemukan", "pulih", "kosinus_rerata",
              "salah_tuduh", "terlewat"]].round(3).to_string(index=False))
    hasil["derau"] = t1

    print()
    print("=" * L)
    print("KETAHANAN 2 — perancu tak termodelkan (penuaan alat)")
    print("=" * L)
    print("  Aliran naik perlahan sepanjang riwayat. Ini BUKAN kerusakan;")
    print("  tidak ada pihak yang boleh dituduh karenanya.")
    print()
    print("  2a. penuaan MENYELURUH — tanpa arah, hanya menggeser skala")
    penuaan_uji = [0.0, 0.20] if cepat else [0.0, 0.10, 0.20, 0.35]
    b = [uji(n_hari=400, penuaan=p) for p in penuaan_uji]
    t2 = pd.DataFrame([{k: v for k, v in x.items() if k != "tabel"} for x in b])
    print(t2[["penuaan", "n_pola_ditemukan", "pulih", "kosinus_rerata",
              "salah_tuduh", "terlewat"]].round(3).to_string(index=False))
    hasil["penuaan"] = t2

    print()
    print(f"  2b. penuaan TERPILIH — hanya {', '.join(ALIRAN_MENUA)}.")
    print("      Perancu berarah: bisa disangka kerusakan sungguhan.")
    b = [uji(n_hari=400, penuaan=p, terpilih=True) for p in penuaan_uji]
    t2b = pd.DataFrame([{k: v for k, v in x.items() if k != "tabel"} for x in b])
    print(t2b[["penuaan", "n_pola_ditemukan", "pulih", "kosinus_rerata",
               "salah_tuduh", "terlewat"]].round(3).to_string(index=False))
    hasil["penuaan_terpilih"] = t2b

    print()
    print("=" * L)
    print("KETAHANAN 3 — berapa hari riwayat yang dibutuhkan")
    print("=" * L)
    hari_uji = [100, 400] if cepat else [60, 120, 250, 400, 800]
    b = [uji(n_hari=n) for n in hari_uji]
    t3 = pd.DataFrame([{k: v for k, v in x.items() if k != "tabel"} for x in b])
    print(t3[["n_hari", "n_pola_ditemukan", "pulih", "kosinus_rerata",
              "salah_tuduh", "terlewat"]].round(3).to_string(index=False))
    hasil["riwayat"] = t3

    print()
    print("=" * L)
    print("SENSITIVITAS KOEFISIEN — nisbah massa meleset +/-15%")
    print("=" * L)
    t4 = sensitivitas_koefisien()
    print(t4.to_string(index=False))
    geser = (t4[t4["mode"] == "terverifikasi"]["tak_terjelaskan_poin"].max()
             - t4[t4["mode"] == "terverifikasi"]["tak_terjelaskan_poin"].min())
    print()
    print(f"  pergeseran baris tak terjelaskan akibat galat +/-15%: "
          f"{geser:.3f} poin")
    hasil["sensitivitas"] = t4
    hasil["pergeseran_15pct"] = float(geser)

    print("=" * L)
    return hasil


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cepat", action="store_true")
    args = ap.parse_args()
    laporan(cepat=args.cepat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
