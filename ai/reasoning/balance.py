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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.config import coefficients as C
from ai.perception import potential as M4

PIHAK_PEMASOK = "pemasok"
PIHAK_PABRIK = "pabrik"
PIHAK_TIDAK_JELAS = "tidak_terjelaskan"


# Ambang keyakinan per baris. Lebar RELATIF terhadap nilainya, karena
# selang +/-0,05 poin berarti sangat berbeda pada baris 2,0 poin dan pada
# baris 0,1 poin.
LEBAR_TINGGI = 0.20
LEBAR_SEDANG = 0.50


def keyakinan_baris(poin: float, lo: float, hi: float, dasar_sah: bool) -> str:
    """Terjemahkan lebar selang jadi kata yang dimengerti manajer pabrik.

    Dua hal menurunkan keyakinan, dan keduanya harus dihormati:

    1. Selang yang MEMUAT NOL. Selama "tidak ada kehilangan sama sekali"
       belum tersingkir, baris ini tidak boleh jadi dasar potongan --
       berapa pun sempitnya angka tengahnya.
    2. Koefisien yang belum tertelusur ke sumber terbit. Angka boleh
       terlihat rapi, tapi rapi bukan sahih.
    """
    if lo * hi <= 0:
        return "rendah"
    lebar_relatif = (hi - lo) / max(abs(poin), 1e-9)
    if lebar_relatif <= LEBAR_TINGGI and dasar_sah:
        return "tinggi"
    if lebar_relatif <= LEBAR_SEDANG:
        return "sedang"
    return "rendah"


@dataclass
class Baris:
    """Satu baris kehilangan pada kartu neraca.

    Selalu membawa selang. Tidak ada varian "tanpa selang": begitu selang
    boleh dimatikan, ia akan dimatikan -- dan angka pasti yang lahir dari
    masukan tidak pasti adalah kebohongan matematis.
    """

    nama: str
    poin: float                 # poin OER, bertanda negatif
    kg: float
    pihak: str
    poin_lo: float = 0.0        # batas bawah selang 90%
    poin_hi: float = 0.0
    dasar_sah: bool = True      # False = memakai koefisien belum terverifikasi
    keterangan: str = ""

    def __post_init__(self) -> None:
        # Baris tanpa selang eksplisit diperlakukan sebagai titik, bukan
        # sebagai "tidak diketahui" -- supaya kelalaian tidak menyamar
        # jadi kepastian.
        if self.poin_lo == 0.0 and self.poin_hi == 0.0:
            self.poin_lo = self.poin_hi = self.poin
        if self.poin_lo > self.poin_hi:
            self.poin_lo, self.poin_hi = self.poin_hi, self.poin_lo

    @property
    def lebar(self) -> float:
        return self.poin_hi - self.poin_lo

    @property
    def keyakinan(self) -> str:
        return keyakinan_baris(self.poin, self.poin_lo, self.poin_hi,
                               self.dasar_sah)

    @property
    def boleh_untuk_potongan(self) -> bool:
        """Satu-satunya tempat aturan ini boleh ditulis."""
        return self.keyakinan == "tinggi" and self.poin_lo * self.poin_hi > 0


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

    # e4 -- ketidakpastian selisih neraca, hasil perambatan e2/e3 dari
    # sisi pemasok dan galat ukur laboratorium dari sisi pabrik.
    sisa_lo: float = 0.0
    sisa_hi: float = 0.0

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

    def melebar(self) -> bool:
        """Apakah selisih benar-benar LEBIH tidak pasti daripada bahannya?

        Selisih adalah pengurangan dua angka yang keduanya tidak pasti,
        jadi ragamnya menjumlah -- lebar selangnya WAJIB tidak lebih
        sempit daripada penyumbang terlebar. Kalau uji ini gagal, ada
        yang keliru pada perambatannya, dan kartu ini sedang mengaku
        lebih tahu daripada bahan-bahannya.
        """
        bahan = [b.lebar for b in (*self.rugi_pemasok, *self.rugi_pabrik)]
        return self.tak_terjelaskan.lebar >= max(bahan, default=0.0) - 1e-9

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
            print(_baris_teks(b))
        print(f"  {'^ tanggung jawab PEMASOK':>62s}")
        print("-" * L)
        print(f"  Potensi REALISTIS         {self.oer_realistis:6.3f} poin"
              f"   {self.potensi_realistis_kg:10,.0f} kg")
        if self.selang_potensi_kg:
            lo, hi = self.selang_potensi_kg
            print(f"  {'selang 90%: ' + f'{lo:,.0f} - {hi:,.0f} kg':>62s}")
        print("-" * L)
        for b in self.rugi_pabrik:
            print(_baris_teks(b))
        print(f"  {'^ tanggung jawab PABRIK':>62s}")
        print(_baris_teks(self.tak_terjelaskan))
        print("-" * L)
        print(f"  Rendemen AKTUAL           {self.oer_aktual:6.3f} poin"
              f"   {self.minyak_aktual_kg:10,.0f} kg")
        print("=" * L)
        p = self.bagi_tanggung_jawab()
        print(f"  pangsa   pemasok {p[PIHAK_PEMASOK]:5.1%}"
              f"   pabrik {p[PIHAK_PABRIK]:5.1%}"
              f"   tak terjelaskan {p[PIHAK_TIDAK_JELAS]:5.1%}")
        print(f"  galat penutupan aritmetika: {self.galat_penutupan():.2e}")
        print(f"  selisih melebar dari bahannya: "
              f"{'YA' if self.melebar() else 'TIDAK — periksa perambatan'}")
        for c in self.catatan:
            print(f"  ! {c}")
        print("=" * L)


def _baris_teks(b: Baris) -> str:
    tanda = "" if b.dasar_sah else "  [dasar belum sah]"
    return (f"   - {b.nama:<22s} {b.poin:6.3f} poin "
            f"[{b.poin_lo:6.3f};{b.poin_hi:6.3f}] "
            f"{b.kg:9,.0f} kg  {b.keyakinan:7s}{tanda}")


# --------------------------------------------------------------------

def susun(
    komposisi: dict[str, float],
    berat_bruto_kg: float,
    minyak_aktual_kg: float,
    *,
    kehilangan_pabrik_poin: dict[str, float] | None = None,
    komposisi_selang: dict[str, tuple[float, float, float]] | None = None,
    ragam_lab: float = 0.06,
    ragam_timbangan: float = 0.005,
    jam_restan: float = 0.0,
    mode: str = "terverifikasi",
    selang_potensi_kg: tuple[float, float] | None = None,
    alpha: float = 0.10,
    n_sampel: int = 8000,
    seed: int = 42,
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
    komposisi_selang
        ``{kelas: (lo, nilai, hi)}`` dari Model 2. Kalau diberikan, baris
        pemasok memperoleh selang hasil perambatan e2 -> e3; kalau tidak,
        baris itu diperlakukan sebagai titik dan dicatat di `catatan`.
    ragam_lab
        Simpangan relatif pengukuran laboratorium per aliran. Satu contoh
        ampas kempa tidak pernah memberi angka yang sama dua kali; 0,06
        adalah nilai yang dipakai simulator.
    ragam_timbangan
        Simpangan relatif jembatan timbang. Kecil, tetapi bukan nol --
        dan karena ia menyentuh SELURUH neraca, mengabaikannya membuat
        sisa tampak lebih pasti daripada yang mungkin.
    mode
        `terverifikasi` menolak koefisien yang belum tertelusur. Efeknya:
        rugi pemasok ditaksir LEBIH KECIL, dan selisihnya berpindah ke
        baris tak terjelaskan. Arah itu disengaja — kalau ragu, jangan
        merugikan petani.

    Perambatan e4
    -------------
    Sisa adalah pengurangan angka-angka yang semuanya tidak pasti, jadi
    ragamnya MENJUMLAH -- selangnya melebar, bukan menyempit. Itu sifat
    yang harus tampil apa adanya, dan diuji lewat `KartuNeraca.melebar()`.

    Dipakai Monte Carlo alih-alih rumus rambat analitik karena baris
    pemasok berasal dari selang komposisi yang tidak berbentuk normal dan
    saling terikat lewat kendala berjumlah satu. Rumus analitik akan
    mengasumsikan bentuk yang tidak dimiliki datanya.
    """
    catatan: list[str] = []

    # --- baris 1: potensi teoretis ---------------------------------
    # Tidak melihat komposisi sama sekali. Inilah yang membuat baris
    # kedua bisa berdiri sendiri sebagai "kerugian akibat mutu".
    basis = C.nilai("rendemen.basis_matang")
    potensi_teoretis_kg = berat_bruto_kg * basis / 100.0

    # --- baris 2: rugi sisi pemasok --------------------------------
    rng = np.random.default_rng(seed)
    q = (alpha / 2, 1 - alpha / 2)

    p = M4.hitung(komposisi, berat_bruto_kg, mode=mode)

    # e2 -> e3: selang komposisi dirambatkan lewat penalti yang sama.
    # Tanpa selang komposisi, baris ini jujur mengaku diperlakukan titik.
    if komposisi_selang:
        lo_k = np.array([komposisi_selang.get(k, (0, 0, 0))[0] for k in M4.NAMA_KELAS])
        hi_k = np.array([komposisi_selang.get(k, (0, 0, 0))[2] for k in M4.NAMA_KELAS])
        cuplik = rng.uniform(lo_k, hi_k, size=(n_sampel, len(M4.NAMA_KELAS)))
        jml = cuplik.sum(axis=1, keepdims=True)
        cuplik = np.divide(cuplik, np.where(jml == 0, 1, jml)) * 100.0
        pen = np.array([p.penalti_dipakai[k] for k in M4.NAMA_KELAS])
        pemasok_sampel = cuplik @ pen
    else:
        pemasok_sampel = np.full(n_sampel, p.rugi_komposisi)
        catatan.append(
            "selang komposisi tidak diberikan -> baris pemasok diperlakukan "
            "sebagai titik. Sisa yang dihasilkan LEBIH SEMPIT daripada "
            "seharusnya; berikan komposisi_selang dari Model 2 untuk "
            "perambatan penuh")

    pl, ph = np.quantile(pemasok_sampel, q)
    rugi_pemasok = [
        Baris(nama="mutu buah masuk",
              poin=p.rugi_komposisi,
              kg=berat_bruto_kg * p.rugi_komposisi / 100.0,
              pihak=PIHAK_PEMASOK,
              poin_lo=float(pl), poin_hi=float(ph),
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
    sampel_pabrik: list[np.ndarray] = []

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
            # Koefisien restan sendiri belum terverifikasi, jadi
            # ketidakpastiannya jauh lebih besar daripada galat lab --
            # dipakai +/-30% alih-alih pura-pura setepat hasil ukur.
            s_restan = rng.normal(poin, abs(poin) * 0.30, size=n_sampel)
            rl, rh = np.quantile(s_restan, q)
            sampel_pabrik.append(s_restan)
            rugi_pabrik.append(
                Baris(nama=f"restan {jam_restan:.0f} jam", poin=poin,
                      kg=berat_bruto_kg * poin / 100.0, pihak=PIHAK_PABRIK,
                      poin_lo=float(rl), poin_hi=float(rh),
                      dasar_sah=(k.status == C.TERVERIFIKASI),
                      keterangan="minyak menurun selama buah menunggu diolah"))

    for nama, poin in (kehilangan_pabrik_poin or {}).items():
        nilai = -abs(poin)
        # Galat ukur laboratorium: relatif, karena aliran besar dan aliran
        # kecil tidak punya ketelitian absolut yang sama.
        s_aliran = nilai * rng.normal(1.0, ragam_lab, size=n_sampel)
        al, ah = np.quantile(s_aliran, q)
        sampel_pabrik.append(s_aliran)
        rugi_pabrik.append(
            Baris(nama=nama.replace("_", " "), poin=nilai,
                  kg=nilai * berat_bruto_kg / 100.0, pihak=PIHAK_PABRIK,
                  poin_lo=float(al), poin_hi=float(ah),
                  dasar_sah=True,
                  keterangan="hasil ukur laboratorium aliran kehilangan"))

    # --- baris 4: sisa yang tidak bisa dijelaskan -------------------
    oer_aktual = minyak_aktual_kg / berat_bruto_kg * 100.0
    total_pemasok = sum(b.poin for b in rugi_pemasok)
    total_pabrik = sum(b.poin for b in rugi_pabrik)
    sisa = oer_aktual - (basis + total_pemasok + total_pabrik)

    # e4. Semua sumber ketidakpastian dijumlahkan di ruang sampel, bukan
    # di ruang rumus -- termasuk timbangan, yang menyentuh seluruh neraca
    # sekaligus sehingga tidak boleh dianggap sempurna.
    aktual_sampel = oer_aktual * rng.normal(1.0, ragam_timbangan, size=n_sampel)
    pabrik_sampel = (np.sum(sampel_pabrik, axis=0) if sampel_pabrik
                     else np.zeros(n_sampel))
    sisa_sampel = aktual_sampel - (basis + pemasok_sampel + pabrik_sampel)
    sisa_lo, sisa_hi = (float(x) for x in np.quantile(sisa_sampel, q))

    tak_terjelaskan = Baris(
        nama="tidak terjelaskan", poin=sisa,
        kg=berat_bruto_kg * sisa / 100.0, pihak=PIHAK_TIDAK_JELAS,
        poin_lo=sisa_lo, poin_hi=sisa_hi,
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
        sisa_lo=sisa_lo, sisa_hi=sisa_hi,
    )
    return kartu


def dari_simulator(hasil, berat_bruto_kg: float, komposisi: dict[str, float],
                   *, jam_restan: float = 0.0,
                   mode: str = "terverifikasi",
                   komposisi_selang: dict[str, tuple[float, float, float]] | None = None,
                   lebar_komposisi: float = 0.03,
                   **kw) -> KartuNeraca:
    """Bangun kartu dari keluaran ai/simulator/mill.py.

    Dipakai untuk pengujian: simulator tahu kebenarannya, Model 5 hanya
    boleh melihat yang akan terlihat di pabrik nyata — komposisi taksiran,
    hasil ukur aliran, dan angka timbangan.
    """
    kehilangan = {k: abs(v) for k, v in hasil.kehilangan_aliran.items()}
    if komposisi_selang is None and lebar_komposisi > 0:
        # Model 2 tidak selalu ikut dijalankan dalam pengujian. Selang
        # buatan seragam dipakai supaya perambatan tetap teruji, dan
        # lebarnya disebut terbuka lewat parameter.
        komposisi_selang = {
            k: (max(0.0, v - lebar_komposisi), v, min(1.0, v + lebar_komposisi))
            for k, v in komposisi.items()
        }
    return susun(komposisi, berat_bruto_kg, hasil.minyak_kg,
                 kehilangan_pabrik_poin=kehilangan,
                 komposisi_selang=komposisi_selang,
                 jam_restan=jam_restan, mode=mode, **kw)


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


# --------------------------------------------------------------------
# Permukaan resmi (GATE AI-3). Backend memanggil nama ini.
# --------------------------------------------------------------------

def reconcile(*args, **kw) -> KartuNeraca:
    """Nama resmi untuk `susun`. Menghasilkan kartu neraca TIGA baris."""
    return susun(*args, **kw)
