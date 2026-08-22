-- ====================================================================
-- NERACA MINYAK — skema basis data
--
-- Berkas ini dipasang di /docker-entrypoint-initdb.d, jadi ia berjalan
-- OTOMATIS saat volume Postgres pertama kali dibuat. Juri tidak perlu
-- menjalankan migrasi manual, dan tidak ada langkah yang bisa terlewat.
--
-- Menjalankan ulang: `docker compose down -v` lalu `up`. Tanpa -v,
-- volume lama bertahan dan berkas ini TIDAK dijalankan lagi.
-- ====================================================================

-- --------------------------------------------------------------------
-- PEMASOK
-- --------------------------------------------------------------------
CREATE TABLE supplier (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    -- swadaya  : petani perorangan, posisi tawar paling lemah
    -- kud      : koperasi unit desa
    -- inti     : kebun milik perusahaan sendiri
    kind        TEXT NOT NULL CHECK (kind IN ('swadaya', 'kud', 'inti')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------
-- MUATAN TRUK
-- --------------------------------------------------------------------
CREATE TABLE batch (
    id               SERIAL PRIMARY KEY,
    truck_plate      TEXT NOT NULL,
    supplier_id      INTEGER NOT NULL REFERENCES supplier(id) ON DELETE RESTRICT,
    received_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    gross_weight_kg  NUMERIC(12, 2) NOT NULL CHECK (gross_weight_kg > 0),
    -- restan: jam menunggu sebelum diolah. Ini kehilangan sisi PABRIK
    -- meski sebabnya buah menunggu -- yang mengatur antrean giling
    -- adalah pabrik, bukan petani yang sudah menyerahkan buahnya.
    queue_hours      NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (queue_hours >= 0),
    shift_date       DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX batch_shift_date_idx ON batch (shift_date);
CREATE INDEX batch_supplier_idx   ON batch (supplier_id);

-- --------------------------------------------------------------------
-- HASIL GRADING (Model 1 + 2 + 4)
-- --------------------------------------------------------------------
CREATE TABLE grading_result (
    id                SERIAL PRIMARY KEY,
    batch_id          INTEGER REFERENCES batch(id) ON DELETE CASCADE,

    -- JSONB karena strukturnya berubah-ubah (kelas bisa bertambah) dan
    -- TIAP nilai butuh selang. Memaksakannya ke kolom relasional akan
    -- menghasilkan puluhan kolom yang sebagian besar NULL.
    --   {"ripe":{"v":68,"lo":63,"hi":73}, "unripe":{"v":12,...}}
    composition       JSONB NOT NULL,

    -- Potensi minyak SELALU bertiga: nilai tanpa selang tidak boleh
    -- ada di basis data ini. Kalau kolom lo/hi boleh NULL, cepat atau
    -- lambat akan ada baris yang mengisinya NULL dan janji "jujur soal
    -- ketidakpastian" bocor lewat pintu belakang.
    potential_oil_kg  NUMERIC(12, 2) NOT NULL,
    potential_lo      NUMERIC(12, 2) NOT NULL,
    potential_hi      NUMERIC(12, 2) NOT NULL,

    detections        JSONB NOT NULL DEFAULT '[]'::jsonb,
    overlay_path      TEXT,
    low_confidence_n  INTEGER NOT NULL DEFAULT 0,

    -- Jejak audit. Kalau ada sengketa tiga bulan kemudian, harus bisa
    -- dijawab "penilaian itu dibuat model versi berapa".
    model_version     TEXT NOT NULL,

    human_corrected   BOOLEAN NOT NULL DEFAULT FALSE,
    correction_note   TEXT,
    processed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT selang_potensi_masuk_akal
        CHECK (potential_lo <= potential_oil_kg AND potential_oil_kg <= potential_hi)
);

CREATE INDEX grading_batch_idx ON grading_result (batch_id);

-- --------------------------------------------------------------------
-- KEHILANGAN MINYAK PER STASIUN
-- --------------------------------------------------------------------
CREATE TABLE station_loss (
    id            SERIAL PRIMARY KEY,
    shift_date    DATE NOT NULL,
    station       TEXT NOT NULL,

    -- PERINGATAN SATUAN. loss_pct adalah KADAR MINYAK DI DALAM ALIRAN
    -- ITU (persen terhadap contoh), BUKAN persen terhadap TBS.
    -- Menjumlahkan kolom ini memberi ~18% dan rendemen mustahil ~3%.
    -- Yang boleh dijumlahkan adalah points_oer.
    loss_pct      NUMERIC(6, 3) NOT NULL CHECK (loss_pct >= 0),
    standard_pct  NUMERIC(6, 3),

    -- nisbah massa aliran terhadap TBS. Berstatus perlu_verifikasi di
    -- ai/config/coefficients.yaml -- disimpan di sini supaya poin bisa
    -- dihitung ulang oleh siapa pun tanpa membuka kode.
    mass_ratio    NUMERIC(6, 4) NOT NULL CHECK (mass_ratio > 0),
    points_oer    NUMERIC(8, 4) GENERATED ALWAYS AS (loss_pct * mass_ratio) STORED,

    UNIQUE (shift_date, station)
);

CREATE INDEX station_loss_date_idx ON station_loss (shift_date);

-- --------------------------------------------------------------------
-- KELUARAN SHIFT (dari timbangan, bukan taksiran)
-- --------------------------------------------------------------------
CREATE TABLE shift_output (
    shift_date      DATE PRIMARY KEY,
    cpo_actual_kg   NUMERIC(14, 2) NOT NULL CHECK (cpo_actual_kg >= 0),
    tbs_processed_kg NUMERIC(14, 2) NOT NULL CHECK (tbs_processed_kg > 0),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------
-- NERACA HARIAN (Model 5 + 6)
-- --------------------------------------------------------------------
CREATE TABLE balance (
    shift_date             DATE PRIMARY KEY REFERENCES shift_output(shift_date)
                                ON DELETE CASCADE,

    -- TIGA kolom potensi, bukan dua. Ini bukan pilihan gaya:
    -- struktur tabel yang MEMAKSA baris tengah ada adalah cara
    -- termurah mencegah buah mentah dihitung dua kali menyelinap
    -- masuk lagi saat refactor. Dengan dua kolom, cacat aritmetikanya
    -- tidak akan tertahan apa pun.
    potential_theoretical  NUMERIC(6, 3) NOT NULL,   -- andai seluruh muatan matang
    potential_realistic    NUMERIC(6, 3) NOT NULL,   -- muatan ini apa adanya
    actual_oer             NUMERIC(6, 3) NOT NULL,   -- dari timbangan

    -- [{"cause":"unripe","side":"supplier","points":0.7,
    --   "lo":0.45,"hi":0.95,"confidence":"medium","detail":"pemasok A, C, F"}, ...]
    attribution            JSONB NOT NULL DEFAULT '[]'::jsonb,

    loss_value_idr         NUMERIC(16, 2) NOT NULL DEFAULT 0,
    coefficient_mode       TEXT NOT NULL DEFAULT 'terverifikasi'
                                CHECK (coefficient_mode IN ('terverifikasi', 'lengkap')),
    computed_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Urutan ketiganya tidak boleh terbalik. Potensi realistis yang
    -- melampaui potensi teoretis berarti mutu buah MENAMBAH kandungan
    -- minyak, yang mustahil.
    CONSTRAINT urutan_tiga_baris
        CHECK (potential_realistic <= potential_theoretical)
);

-- --------------------------------------------------------------------
-- KOREKSI GRADER — tiap koreksi adalah data latih
-- --------------------------------------------------------------------
CREATE TABLE grader_decision (
    id            SERIAL PRIMARY KEY,
    grading_id    INTEGER NOT NULL REFERENCES grading_result(id) ON DELETE CASCADE,
    decision      TEXT NOT NULL CHECK (decision IN ('agree', 'correct')),
    note          TEXT,
    corrected     JSONB,
    decided_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX grader_decision_grading_idx ON grader_decision (grading_id);
