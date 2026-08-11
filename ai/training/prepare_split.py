"""Split train/val/test BERDASARKAN ID TUMPUKAN/VIDEO, bukan per gambar.

Dataset dibuat dari video rotasi 360 derajat -> banyak frame nyaris
duplikat dari tumpukan yang sama. Split per gambar = kebocoran =
metrik melambung dan angkanya PALSU.
"""
