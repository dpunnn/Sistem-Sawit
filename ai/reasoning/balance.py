"""MODEL 5 — Rekonsiliasi neraca massa.

STRUKTUR 3 BARIS (JANGAN PERNAH 2 BARIS):

    Potensi TEORETIS   (andai seluruh muatan matang)
      (-) rugi komposisi buah masuk    -> tanggung jawab PEMASOK
    ------------------------------------------------------------
    Potensi REALISTIS  (muatan ini apa adanya)
      (-) kehilangan proses pabrik     -> tanggung jawab PABRIK
      (-) tidak terjelaskan
    ------------------------------------------------------------
    Rendemen AKTUAL

Struktur ini mencegah buah mentah dihitung DUA KALI, sekaligus
memisahkan tanggung jawab pemasok vs pabrik secara matematis.
Lihat tests/test_balance.py.

## Kenapa dua baris berbahaya

Neraca dua baris berbentuk "potensi teoretis dikurangi kehilangan".
Dengan bentuk itu, buah mentah muncul dua kali: sekali karena
menurunkan kandungan minyak yang masuk pabrik, sekali lagi karena
pabrik yang memproses buah mentah memang mencatat kehilangan lebih
tinggi. Pemasok lalu dipotong dua kali untuk satu kesalahan yang sama.

Baris tengah memutus rantai itu. Setelah potensi realistis dihitung,
buah mentah selesai urusannya — sisanya urusan pabrik. Sifat ini
diuji secara mekanis, bukan sekadar diyakini: menggandakan buah mentah
harus mengubah rugi pemasok DAN TIDAK BOLEH menyentuh rugi pabrik
maupun bagian tak terjelaskan.

## Kenapa ada baris "tidak terjelaskan"

Karena kehilangan yang terukur tidak pernah menjumlah pas. Sistem yang
memaksanya nol sedang membebankan selisihnya ke salah satu pihak tanpa
bukti — biasanya ke pihak yang lebih lemah. Baris ini adalah
pengakuan tertulis bahwa ada bagian yang belum diketahui, dan besarnya
adalah ukuran seberapa jauh sistem ini boleh dipercaya hari itu.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.config import coefficients as C
from ai.perception import potential as M4

PIHAK_PEMASOK = "pemasok"
PIHAK_PABRIK = "pabrik"
PIHAK_TIDAK_JELAS = "tidak_terjelaskan"


@dataclass
class Baris:
    """Satu baris kehilangan pada kartu neraca."""

    nama: str
    poin: float                 # poin OER, bertanda negatif
    kg: float
    pihak: str
    dasar_sah: bool = True      # False = memakai koefisien belum terverifikasi
    keterangan: str = ""


@dataclass
class KartuNeraca:
    berat_bruto_kg: float

    oer_teoretis: float
    potensi_teoretis_kg: float

    rugi_pemasok: list[Baris]
    oer_realistis: float
    potensi_realistis_kg: float

    rugi_pabrik: list[Baris]
    tak_terjelaskan: Baris

    oer_aktual: float
    minyak_aktual_kg: float

    selang_potensi_kg: tuple[float, float] | None = None
    catatan: list[str] = field(default_factory=list)

    # -- ringkasan ----------------------------------------------------

    @property
    def total_pemasok_poin(self) -> float:
        return sum(b.poin for b in self.rugi_pemasok)

    @property
    def total_pabrik_poin(self) -> float:
        return sum(b.poin for b in self.rugi_pabrik)

    @property
    def semua_baris(self) -> list[Baris]:
        return [*self.rugi_pemasok, *self.rugi_pabrik, self.tak_terjelaskan]

    def bagi_tanggung_jawab(self) -> dict[str, float]:
        """Pangsa tiap pihak atas total selisih, dalam pecahan 0-1.

        Dipakai frontend untuk batang bertumpuk. Kalau totalnya nol
        (mustahil dalam praktik) semuanya dikembalikan nol supaya tidak
        ada pembagian dengan nol yang menghasilkan angka mengada-ada.
        """
        total = abs(self.total_pemasok_poin) + abs(self.total_pabrik_poin) \
            + abs(self.tak_terjelaskan.poin)
        if total <= 0:
            return {PIHAK_PEMASOK: 0.0, PIHAK_PABRIK: 0.0, PIHAK_TIDAK_JELAS: 0.0}
        return {
            PIHAK_PEMASOK: abs(self.total_pemasok_poin) / total,
            PIHAK_PABRIK: abs(self.total_pabrik_poin) / total,
            PIHAK_TIDAK_JELAS: abs(self.tak_terjelaskan.poin) / total,
        }

    def galat_penutupan(self) -> float:
        """Sisa aritmetika neraca. Harus nol sampai batas presisi mesin.

        Ini BUKAN bagian tak terjelaskan — bagian tak terjelaskan sudah
        jadi baris tersendiri. Ini pemeriksaan bahwa penjumlahannya benar.
        """
        jalur = (self.oer_teoretis + self.total_pemasok_poin
                 + self.total_pabrik_poin + self.tak_terjelaskan.poin)
        return abs(jalur - self.oer_aktual)

    def sebagai_dict(self) -> dict:
        """Bentuk yang dikirim ke backend, tanpa kehilangan satu baris pun."""
        return {
            "berat_bruto_kg": self.berat_bruto_kg,
            "teoretis": {"oer": self.oer_teoretis,
                         "kg": self.potensi_teoretis_kg},
            "rugi_pemasok": [vars(b) for b in self.rugi_pemasok],
            "realistis": {"oer": self.oer_realistis,
                          "kg": self.potensi_realistis_kg,
                          "selang_kg": self.selang_potensi_kg},
            "rugi_pabrik": [vars(b) for b in self.rugi_pabrik],
            "tak_terjelaskan": vars(self.tak_terjelaskan),
            "aktual": {"oer": self.oer_aktual, "kg": self.minyak_aktual_kg},
            "pangsa": self.bagi_tanggung_jawab(),
            "galat_penutupan": self.galat_penutupan(),
            "catatan": self.catatan,
        }

    def cetak(self) -> None:
        L = 66
        print("=" * L)
        print(f"  KARTU NERACA MINYAK      berat bruto "
              f"{self.berat_bruto_kg:,.0f} kg".replace(",", "."))
        print("=" * L)
        print(f"  Potensi TEORETIS          {self.oer_teoretis:6.3f} poin"
              f"   {self.potensi_teoretis_kg:10,.0f} kg")
        print(f"  {'(seandainya seluruh muatan matang)':>62s}")
        print("-" * L)
        for b in self.rugi_pemasok:
            tanda = "" if b.dasar_sah else "  [dasar belum sah]"
            print(f"   - {b.nama:<22s} {b.poin:6.3f} poin   "
                  f"{b.kg:10,.0f} kg{tanda}")
        print(f"  {'^ tanggung jawab PEMASOK':>62s}")
        print("-" * L)
        print(f"  Potensi REALISTIS         {self.oer_realistis:6.3f} poin"
              f"   {self.potensi_realistis_kg:10,.0f} kg")
        if self.selang_potensi_kg:
            lo, hi = self.selang_potensi_kg
            print(f"  {'selang 90%: ' + f'{lo:,.0f} - {hi:,.0f} kg':>62s}")
        print("-" * L)
        for b in self.rugi_pabrik:
            tanda = "" if b.dasar_sah else "  [dasar belum sah]"
            print(f"   - {b.nama:<22s} {b.poin:6.3f} poin   "
                  f"{b.kg:10,.0f} kg{tanda}")
        print(f"  {'^ tanggung jawab PABRIK':>62s}")
        b = self.tak_terjelaskan
        print(f"   - {b.nama:<22s} {b.poin:6.3f} poin   {b.kg:10,.0f} kg")
        print("-" * L)
        print(f"  Rendemen AKTUAL           {self.oer_aktual:6.3f} poin"
              f"   {self.minyak_aktual_kg:10,.0f} kg")
        print("=" * L)
        p = self.bagi_tanggung_jawab()
        print(f"  pangsa   pemasok {p[PIHAK_PEMASOK]:5.1%}"
              f"   pabrik {p[PIHAK_PABRIK]:5.1%}"
              f"   tak terjelaskan {p[PIHAK_TIDAK_JELAS]:5.1%}")
        print(f"  galat penutupan aritmetika: {self.galat_penutupan():.2e}")
        for c in self.catatan:
            print(f"  ! {c}")
        print("=" * L)


# --------------------------------------------------------------------

def susun(
    komposisi: dict[str, float],
    berat_bruto_kg: float,
    minyak_aktual_kg: float,
    *,
    kehilangan_pabrik_poin: dict[str, float] | None = None,
    jam_restan: float = 0.0,
    mode: str = "terverifikasi",
    selang_potensi_kg: tuple[float, float] | None = None,
) -> KartuNeraca:
    """Susun kartu neraca satu muatan / satu hari giling.

    Parameter
    ---------
    komposisi
        Keluaran Model 2 (titik tengah), pecahan berjumlah 1.
    minyak_aktual_kg
        Yang benar-benar dihasilkan pabrik. Ini SATU-SATUNYA angka yang
        tidak ditaksir — datang dari timbangan.
    kehilangan_pabrik_poin
        Hasil ukur laboratorium per aliran, sudah dalam poin rendemen
        (kadar x nisbah massa). Bertanda positif; tandanya dibalik di sini.
    mode
        `terverifikasi` menolak koefisien yang belum tertelusur. Efeknya:
        rugi pemasok ditaksir LEBIH KECIL, dan selisihnya berpindah ke
        baris tak terjelaskan. Arah itu disengaja — kalau ragu, jangan
        merugikan petani.
    """
    catatan: list[str] = []

    # --- baris 1: potensi teoretis ---------------------------------
    # Tidak melihat komposisi sama sekali. Inilah yang membuat baris
    # kedua bisa berdiri sendiri sebagai "kerugian akibat mutu".
    basis = C.nilai("rendemen.basis_matang")
    potensi_teoretis_kg = berat_bruto_kg * basis / 100.0

    # --- baris 2: rugi sisi pemasok --------------------------------
    p = M4.hitung(komposisi, berat_bruto_kg, mode=mode)
    rugi_pemasok = [
        Baris(nama="mutu buah masuk",
              poin=p.rugi_komposisi,
              kg=berat_bruto_kg * p.rugi_komposisi / 100.0,
              pihak=PIHAK_PEMASOK,
              dasar_sah=p.dasar_sah,
              keterangan="selisih kandungan minyak akibat tingkat kematangan")
    ]
    if p.penalti_dilewati:
        catatan.append(
            "koefisien dilewati karena belum terverifikasi: "
            + ", ".join(p.penalti_dilewati)
            + " -> rugi pemasok ditaksir lebih kecil, selisihnya masuk "
              "ke baris tak terjelaskan")

    oer_realistis = p.oer_realistis
    potensi_realistis_kg = p.potensi_kg

    # --- baris 3: rugi sisi pabrik ---------------------------------
    rugi_pabrik: list[Baris] = []

    if jam_restan > 0:
        # Restan adalah kehilangan sisi PABRIK meski sebabnya buah
        # menunggu: yang mengatur antrean giling adalah pabrik, bukan
        # petani yang sudah menyerahkan buahnya.
        try:
            k = C.get("restan.penalti_per_jam",
                      izinkan_belum_terverifikasi=(mode != "terverifikasi"))
        except C.KoefisienError:
            catatan.append(
                "penalti restan belum terverifikasi -> tidak dibebankan ke "
                "pabrik pada mode terverifikasi; masuk ke tak terjelaskan")
        else:
            poin = jam_restan * k.nilai
            rugi_pabrik.append(
                Baris(nama=f"restan {jam_restan:.0f} jam", poin=poin,
                      kg=berat_bruto_kg * poin / 100.0, pihak=PIHAK_PABRIK,
                      dasar_sah=(k.status == C.TERVERIFIKASI),
                      keterangan="minyak menurun selama buah menunggu diolah"))

    for nama, poin in (kehilangan_pabrik_poin or {}).items():
        rugi_pabrik.append(
            Baris(nama=nama.replace("_", " "), poin=-abs(poin),
                  kg=-abs(poin) * berat_bruto_kg / 100.0, pihak=PIHAK_PABRIK,
                  dasar_sah=True,
                  keterangan="hasil ukur laboratorium aliran kehilangan"))

    # --- baris 4: sisa yang tidak bisa dijelaskan -------------------
    oer_aktual = minyak_aktual_kg / berat_bruto_kg * 100.0
    total_pemasok = sum(b.poin for b in rugi_pemasok)
    total_pabrik = sum(b.poin for b in rugi_pabrik)
    sisa = oer_aktual - (basis + total_pemasok + total_pabrik)

    tak_terjelaskan = Baris(
        nama="tidak terjelaskan", poin=sisa,
        kg=berat_bruto_kg * sisa / 100.0, pihak=PIHAK_TIDAK_JELAS,
        dasar_sah=True,
        keterangan="sisa yang tidak boleh dibebankan ke pihak mana pun")

    if sisa > 0:
        catatan.append(
            f"sisa BERTANDA POSITIF ({sisa:+.3f} poin): pabrik menghasilkan "
            "lebih banyak daripada yang dijelaskan neraca. Penyebab yang "
            "mungkin: potensi teoretis terlalu rendah, atau kehilangan "
            "dilaporkan terlalu besar. Tidak boleh dijadikan dasar potongan.")

    kartu = KartuNeraca(
        berat_bruto_kg=berat_bruto_kg,
        oer_teoretis=basis,
        potensi_teoretis_kg=potensi_teoretis_kg,
        rugi_pemasok=rugi_pemasok,
        oer_realistis=oer_realistis,
        potensi_realistis_kg=potensi_realistis_kg,
        rugi_pabrik=rugi_pabrik,
        tak_terjelaskan=tak_terjelaskan,
        oer_aktual=oer_aktual,
        minyak_aktual_kg=minyak_aktual_kg,
        selang_potensi_kg=selang_potensi_kg,
        catatan=catatan,
    )
    return kartu


def dari_simulator(hasil, berat_bruto_kg: float, komposisi: dict[str, float],
                   *, jam_restan: float = 0.0,
                   mode: str = "terverifikasi") -> KartuNeraca:
    """Bangun kartu dari keluaran ai/simulator/mill.py.

    Dipakai untuk pengujian: simulator tahu kebenarannya, Model 5 hanya
    boleh melihat yang akan terlihat di pabrik nyata — komposisi taksiran,
    hasil ukur aliran, dan angka timbangan.
    """
    kehilangan = {k: abs(v) for k, v in hasil.kehilangan_aliran.items()}
    return susun(komposisi, berat_bruto_kg, hasil.minyak_kg,
                 kehilangan_pabrik_poin=kehilangan, jam_restan=jam_restan,
                 mode=mode)


def _peragaan() -> None:
    from ai.simulator.mill import Pabrik

    komposisi = {"mentah": 0.12, "kurang_masak": 0.18, "masak": 0.65,
                 "terlalu_masak": 0.05}
    berat = 240_000.0
    pabrik = Pabrik(seed=42, ragam_proses=0.0)
    h = pabrik.olah(komposisi, berat, jam_restan=9.0,
                    gangguan="perebusan_kurang_matang")

    print()
    print("### mode terverifikasi (bawaan) ###")
    dari_simulator(h, berat, komposisi, jam_restan=9.0).cetak()
    print()
    print("### mode lengkap (memakai koefisien belum tertelusur) ###")
    dari_simulator(h, berat, komposisi, jam_restan=9.0, mode="lengkap").cetak()


if __name__ == "__main__":
    _peragaan()
