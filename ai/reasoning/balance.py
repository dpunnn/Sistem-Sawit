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
"""
