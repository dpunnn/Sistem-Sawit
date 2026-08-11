"""MODEL 1 — Deteksi & klasifikasi ordinal per tandan.

INPUT   : citra tumpukan TBS
OUTPUT  : bounding box tiap tandan + kelas kematangan + keyakinan
KELAS   : unripe -> underripe -> ripe -> overripe -> rotten
          (+ empty_bunch, abnormal)

CATATAN : kematangan itu BERURUTAN. Pakai loss ordinal (CORAL),
          bukan cross-entropy biasa. Salah tebak "ripe"->"overripe"
          jauh lebih murah daripada "unripe"->"rotten".
"""
