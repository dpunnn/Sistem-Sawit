-- ====================================================================
-- DATA SEED — dibangkitkan oleh scripts/seed_shift.py
--
-- JANGAN disunting tangan. Seluruh angka di bawah keluar dari
-- ai/simulator/mill.py dan ai/reasoning/balance.py, sehingga
-- barisnya benar-benar menutup. Angka yang diketik tangan pasti
-- tidak menutup, dan itu hal pertama yang akan dicoba juri.
--
-- Dibangkitkan ulang: python scripts/seed_shift.py --sql
-- ====================================================================

INSERT INTO supplier (name, kind) VALUES
    ('KUD Jaya Makmur', 'kud'),
    ('Tani Sawit Mandiri', 'swadaya'),
    ('PT Inti Lestari', 'inti'),
    ('Koperasi Sawit Bersama', 'kud'),
    ('Petani Swadaya Blok C', 'swadaya');

INSERT INTO batch (truck_plate, supplier_id, received_at, gross_weight_kg, queue_hours, shift_date) VALUES
    ('KH 1000 AJ', 1, '2026-08-03 06:00:00+07', 7595.82, 1.32, '2026-08-03'),
    ('KH 1037 BK', 2, '2026-08-03 06:47:00+07', 7934.39, 2.09, '2026-08-03'),
    ('KH 1074 CL', 3, '2026-08-03 07:35:00+07', 4876.71, 2.93, '2026-08-03'),
    ('KH 1111 DM', 4, '2026-08-03 08:24:00+07', 7544.56, 4.14, '2026-08-03'),
    ('KH 1148 EN', 5, '2026-08-03 09:11:00+07', 5012.45, 2.80, '2026-08-03'),
    ('KH 1185 FP', 1, '2026-08-03 10:00:00+07', 5983.19, 4.71, '2026-08-03'),
    ('KH 1222 GJ', 2, '2026-08-03 10:48:00+07', 7075.46, 4.29, '2026-08-03'),
    ('KH 1259 HK', 3, '2026-08-03 11:36:00+07', 6273.66, 1.91, '2026-08-03'),
    ('KH 1296 AL', 4, '2026-08-03 12:24:00+07', 6718.34, 1.19, '2026-08-03'),
    ('KH 1333 BM', 5, '2026-08-03 13:11:00+07', 7810.52, 2.89, '2026-08-03'),
    ('KH 1370 CN', 1, '2026-08-03 14:00:00+07', 7532.35, 10.13, '2026-08-03'),
    ('KH 1407 DP', 2, '2026-08-03 14:48:00+07', 8382.79, 13.36, '2026-08-03'),
    ('KH 1444 EJ', 3, '2026-08-03 15:36:00+07', 7613.53, 9.17, '2026-08-03'),
    ('KH 1481 FK', 4, '2026-08-03 16:23:00+07', 6366.88, 8.26, '2026-08-03'),
    ('KH 1518 GL', 5, '2026-08-03 17:12:00+07', 5117.16, 4.73, '2026-08-03'),
    ('KH 1555 HM', 1, '2026-08-03 18:00:00+07', 7479.05, 5.87, '2026-08-03'),
    ('KH 1592 AN', 2, '2026-08-03 18:48:00+07', 5803.30, 3.48, '2026-08-03'),
    ('KH 1629 BP', 3, '2026-08-03 19:36:00+07', 6378.22, 2.76, '2026-08-03'),
    ('KH 1666 CJ', 4, '2026-08-03 20:23:00+07', 5019.69, 3.90, '2026-08-03'),
    ('KH 1703 DK', 5, '2026-08-03 21:12:00+07', 5407.64, 4.68, '2026-08-03');

INSERT INTO grading_result (batch_id, composition, potential_oil_kg, potential_lo, potential_hi, model_version, processed_at) VALUES
    (1, '{"unripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}, "underripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}, "ripe": {"v": 91.0, "lo": 88.0, "hi": 94.0}, "overripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}}'::jsonb, 1575.37, 1549.94, 1592.49, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (2, '{"unripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}, "underripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}, "ripe": {"v": 91.0, "lo": 88.0, "hi": 94.0}, "overripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}}'::jsonb, 1645.59, 1619.03, 1663.47, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (3, '{"unripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}, "underripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}, "ripe": {"v": 91.0, "lo": 88.0, "hi": 94.0}, "overripe": {"v": 2.0, "lo": 0.0, "hi": 5.0}}'::jsonb, 1011.43, 995.10, 1022.42, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (4, '{"unripe": {"v": 8.0, "lo": 5.0, "hi": 11.0}, "underripe": {"v": 16.0, "lo": 13.0, "hi": 19.0}, "ripe": {"v": 71.0, "lo": 68.0, "hi": 74.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1505.89, 1482.11, 1530.68, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (5, '{"unripe": {"v": 8.0, "lo": 5.0, "hi": 11.0}, "underripe": {"v": 16.0, "lo": 13.0, "hi": 19.0}, "ripe": {"v": 71.0, "lo": 68.0, "hi": 74.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1000.49, 984.68, 1016.95, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (6, '{"unripe": {"v": 8.0, "lo": 5.0, "hi": 11.0}, "underripe": {"v": 16.0, "lo": 13.0, "hi": 19.0}, "ripe": {"v": 71.0, "lo": 68.0, "hi": 74.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1194.25, 1175.38, 1213.90, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (7, '{"unripe": {"v": 8.0, "lo": 5.0, "hi": 11.0}, "underripe": {"v": 16.0, "lo": 13.0, "hi": 19.0}, "ripe": {"v": 71.0, "lo": 68.0, "hi": 74.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1412.26, 1389.95, 1435.50, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (8, '{"unripe": {"v": 8.0, "lo": 5.0, "hi": 11.0}, "underripe": {"v": 16.0, "lo": 13.0, "hi": 19.0}, "ripe": {"v": 71.0, "lo": 68.0, "hi": 74.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1252.22, 1232.44, 1272.83, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (9, '{"unripe": {"v": 24.0, "lo": 21.0, "hi": 27.0}, "underripe": {"v": 18.0, "lo": 15.0, "hi": 21.0}, "ripe": {"v": 55.0, "lo": 52.0, "hi": 58.0}, "overripe": {"v": 3.0, "lo": 0.0, "hi": 6.0}}'::jsonb, 1201.24, 1180.17, 1222.07, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (10, '{"unripe": {"v": 24.0, "lo": 21.0, "hi": 27.0}, "underripe": {"v": 18.0, "lo": 15.0, "hi": 21.0}, "ripe": {"v": 55.0, "lo": 52.0, "hi": 58.0}, "overripe": {"v": 3.0, "lo": 0.0, "hi": 6.0}}'::jsonb, 1396.52, 1372.03, 1420.74, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (11, '{"unripe": {"v": 10.0, "lo": 7.0, "hi": 13.0}, "underripe": {"v": 15.0, "lo": 12.0, "hi": 18.0}, "ripe": {"v": 70.0, "lo": 67.0, "hi": 73.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1483.87, 1460.32, 1508.27, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (12, '{"unripe": {"v": 10.0, "lo": 7.0, "hi": 13.0}, "underripe": {"v": 15.0, "lo": 12.0, "hi": 18.0}, "ripe": {"v": 70.0, "lo": 67.0, "hi": 73.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1651.41, 1625.19, 1678.57, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (13, '{"unripe": {"v": 10.0, "lo": 7.0, "hi": 13.0}, "underripe": {"v": 15.0, "lo": 12.0, "hi": 18.0}, "ripe": {"v": 70.0, "lo": 67.0, "hi": 73.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1499.87, 1476.06, 1524.53, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (14, '{"unripe": {"v": 10.0, "lo": 7.0, "hi": 13.0}, "underripe": {"v": 15.0, "lo": 12.0, "hi": 18.0}, "ripe": {"v": 70.0, "lo": 67.0, "hi": 73.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1254.28, 1234.36, 1274.90, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (15, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1028.04, 1011.85, 1045.05, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (16, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1502.54, 1478.88, 1527.41, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (17, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1165.88, 1147.52, 1185.18, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (18, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1281.39, 1261.21, 1302.59, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (19, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1008.45, 992.57, 1025.14, 'detector-A/head-V3', '2026-08-03 12:00:00+07'),
    (20, '{"unripe": {"v": 7.0, "lo": 4.0, "hi": 10.0}, "underripe": {"v": 14.0, "lo": 11.0, "hi": 17.0}, "ripe": {"v": 74.0, "lo": 71.0, "hi": 77.0}, "overripe": {"v": 5.0, "lo": 2.0, "hi": 8.0}}'::jsonb, 1086.39, 1069.29, 1104.37, 'detector-A/head-V3', '2026-08-03 12:00:00+07');

-- loss_pct = kadar minyak DI DALAM aliran (persen terhadap
-- contoh), BUKAN persen terhadap TBS. Kolom points_oer
-- dihitung Postgres sendiri: loss_pct * mass_ratio.
INSERT INTO station_loss (shift_date, station, loss_pct, standard_pct, mass_ratio) VALUES
    ('2026-08-03', 'condensate', 1.684, 1.000, 0.1300),
    ('2026-08-03', 'empty_bunch', 4.514, 3.000, 0.2300),
    ('2026-08-03', 'press_cake', 4.795, 5.000, 0.1400),
    ('2026-08-03', 'nut_in_fiber', 0.410, NULL, 0.0500),
    ('2026-08-03', 'cst_underflow', 7.040, NULL, 0.0300),
    ('2026-08-03', 'sludge', 0.660, 1.000, 0.0400),
    ('2026-08-03', 'fat_pit', 0.810, NULL, 0.0200),
    ('2026-08-03', 'deoiling_pond', 0.650, NULL, 0.0200);

INSERT INTO shift_output (shift_date, cpo_actual_kg, tbs_processed_kg) VALUES
    ('2026-08-03', 21322.17, 131925.73);

INSERT INTO balance (shift_date, potential_theoretical, potential_realistic, actual_oer, attribution, loss_value_idr, coefficient_mode) VALUES
    ('2026-08-03', 21.000, 19.827, 16.162, '[{"cause": "mutu buah masuk", "side": "supplier", "points": 1.1726, "lo": 0.8442, "hi": 1.4881, "confidence": "low", "detail": "selisih kandungan minyak akibat tingkat kematangan"}, {"cause": "kondensat sterilizer", "side": "mill", "points": 0.2189, "lo": 0.197, "hi": 0.2405, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "janjang kosong", "side": "mill", "points": 1.0382, "lo": 0.9358, "hi": 1.1379, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "ampas kempa", "side": "mill", "points": 0.6714, "lo": 0.6047, "hi": 0.7373, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "nut in fiber", "side": "mill", "points": 0.0205, "lo": 0.0185, "hi": 0.0226, "confidence": "medium", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "underflow cst", "side": "mill", "points": 0.2112, "lo": 0.1902, "hi": 0.2319, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "sludge separator", "side": "mill", "points": 0.0264, "lo": 0.0238, "hi": 0.029, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "fat pit", "side": "mill", "points": 0.0162, "lo": 0.0145, "hi": 0.0178, "confidence": "medium", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "deoiling pond", "side": "mill", "points": 0.013, "lo": 0.0117, "hi": 0.0143, "confidence": "high", "detail": "hasil ukur laboratorium aliran kehilangan"}, {"cause": "tidak terjelaskan", "side": "unknown", "points": 1.4494, "lo": 1.0735, "hi": 1.8316, "confidence": "low", "detail": "sisa yang tidak boleh dibebankan ke pihak mana pun"}]'::jsonb, 95873449.80, 'terverifikasi');
