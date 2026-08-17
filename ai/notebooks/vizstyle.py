"""Gaya visual bersama untuk seluruh notebook Neraca Minyak.

Semua notebook mengimpor modul ini supaya grafiknya terbaca sebagai satu
sistem, bukan kumpulan plot dengan selera berbeda-beda.

Palet sudah divalidasi terhadap enam pemeriksaan (pita terang, lantai
chroma, pemisahan buta warna, lantai penglihatan normal, kontras):
  - kategorikal 6 slot : LULUS, ΔE buta warna terburuk 9,1
  - ramp ordinal 4     : LULUS, monoton terang->gelap, satu hue

Aturan yang dipegang:
  - Satu ukuran di banyak kategori -> SATU warna. Identitas dibawa label
    sumbu, bukan warna. Batang pelangi untuk seri tunggal itu dekorasi.
  - Warna kategorikal hanya dipakai saat identitas memang perlu dibedakan
    (overlay bbox, komposisi bertumpuk).
  - Tingkat kematangan itu BERURUTAN -> ramp satu hue, bukan hue acak.
  - Teks memakai tinta teks, tidak pernah warna seri.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- palet

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# Kategorikal — urutan TETAP, tidak pernah diputar.
CATEGORICAL = [
    "#2a78d6",  # 1 biru
    "#eb6834",  # 2 oranye
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 kuning
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 hijau
]

# Ramp ordinal untuk 4 tingkat kematangan (mentah -> terlalu masak).
ORDINAL_RAMP = ["#86b6ef", "#3987e5", "#256abf", "#104281"]

# Ramp sequential untuk heatmap / magnitudo kontinu.
SEQUENTIAL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

PRIMARY = CATEGORICAL[0]

# ------------------------------------------------- pemetaan kelas dataset

# class_id di file label tersusun alfabetis, BUKAN menurut urutan
# kematangan. Ini sumber kekeliruan yang mahal kalau tidak dipetakan ulang.
CLASS_NAMES = {
    0: "Janjang kosong",
    1: "Kurang masak",
    2: "TBS abnormal",
    3: "TBS masak",
    4: "TBS mentah",
    5: "Terlalu masak",
}

# Urutan kematangan sebenarnya (indeks ordinal 0..3).
ORDINAL_ORDER = [4, 1, 3, 5]  # mentah -> kurang masak -> masak -> terlalu masak
ORDINAL_LABELS = ["TBS mentah", "Kurang masak", "TBS masak", "Terlalu masak"]

# Di luar skala kematangan — struktural, bukan tingkat kematangan.
NON_ORDINAL = [0, 2]  # janjang kosong, abnormal

# Warna per kelas: tingkat kematangan pakai ramp ordinal (urutan bermakna),
# kelas struktural pakai slot kategorikal yang jelas berbeda.
CLASS_COLORS = {
    4: ORDINAL_RAMP[0],   # TBS mentah
    1: ORDINAL_RAMP[1],   # Kurang masak
    3: ORDINAL_RAMP[2],   # TBS masak
    5: ORDINAL_RAMP[3],   # Terlalu masak
    0: CATEGORICAL[1],    # Janjang kosong  (oranye)
    2: CATEGORICAL[5],    # TBS abnormal    (hijau)
}


def apply_style() -> None:
    """Pasang gaya global matplotlib."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 150,

        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10,

        "text.color": INK,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlecolor": INK,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,

        "axes.titlesize": 12,
        "axes.titleweight": "600",
        "axes.titlepad": 14,
        "axes.labelsize": 10,

        # Kerangka resesif: hanya sumbu kiri & bawah, tipis.
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.8,

        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "grid.alpha": 1.0,
        "axes.axisbelow": True,

        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,

        "legend.frameon": False,
        "legend.fontsize": 9,

        "lines.linewidth": 2.0,
        "lines.markersize": 8,
    })


def label_bars(ax, bars, fmt="{:,.0f}", pad=3, color=INK_SECONDARY):
    """Label langsung di ujung batang.

    Dipakai sebagai 'relief' untuk warna yang kontrasnya di bawah 3:1 —
    identitas dan nilai tidak pernah bergantung pada warna saja.
    """
    for b in bars:
        h = b.get_height()
        ax.annotate(
            fmt.format(h),
            (b.get_x() + b.get_width() / 2, h),
            xytext=(0, pad), textcoords="offset points",
            ha="center", va="bottom", fontsize=9, color=color,
        )


def strip_chart(ax):
    """Bersihkan sumbu untuk plot yang tidak butuh skala (mis. gambar)."""
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(False)


def caption(ax, text):
    """Catatan kecil di bawah grafik — tempat menaruh interpretasi."""
    ax.annotate(
        text, xy=(0, -0.16), xycoords="axes fraction",
        fontsize=8.5, color=INK_MUTED, va="top",
    )


def inline() -> None:
    """Kembalikan backend matplotlib ke inline notebook.

    Ultralytics memanggil `plt.switch_backend("Agg")` di dalam rutin
    pelatihannya. Akibatnya seluruh grafik SETELAH pemanggilan train()
    tidak lagi tertangkap notebook — gambar dibuat tapi tidak pernah
    muncul di keluaran sel.

    Panggil ini di awal tiap sel plot yang berjalan setelah pelatihan.
    """
    import matplotlib.pyplot as _plt
    try:
        _plt.switch_backend("module://matplotlib_inline.backend_inline")
    except Exception:
        pass


def show(fig=None, dpi: int = 140) -> None:
    """Tampilkan figure ke keluaran notebook tanpa bergantung backend.

    `plt.show()` hanya bekerja kalau backend matplotlib berupa inline.
    Ultralytics memaksa backend ke 'Agg' di dalam rutin pelatihannya, dan
    sekali berpindah, seluruh grafik sesudahnya hilang diam-diam — gambar
    tetap dibuat, tetapi tidak pernah masuk ke keluaran sel.

    Fungsi ini melewati persoalan itu: figure dirender ke PNG di memori
    lalu dikirim langsung ke tampilan. Bekerja pada backend apa pun.
    """
    import io
    import matplotlib.pyplot as _plt
    from IPython.display import display, Image as _Image

    fig = fig or _plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    _plt.close(fig)
    display(_Image(data=buf.getvalue()))
