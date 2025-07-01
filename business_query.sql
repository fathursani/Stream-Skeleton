-- =============================================
-- MATERIALIZED VIEW UNTUK DATA PER HARI
-- =============================================
CREATE MATERIALIZED VIEW mv_daily_report AS
SELECT 
    DATE(tgl_transaksi) AS day,
    COUNT(*) AS transactions,
    SUM(tarif) AS revenue
FROM fact_toll_transactions ftt 
GROUP BY day;

-- =============================================
-- MATERIALIZED VIEW UNTUK DATA PER JAM
-- =============================================
CREATE MATERIALIZED VIEW mv_trx_perjam AS
SELECT 
    DATE_TRUNC('hour', tgl_transaksi) AS jam,
    COUNT(*) AS total_transaksi,
    SUM(tarif) AS total_pendapatan,
    COUNT(DISTINCT dim_vehicle_id) AS unique_vehicles
FROM fact_toll_transactions
GROUP BY DATE_TRUNC('hour', tgl_transaksi);

-- Index untuk refresh CONCURRENTLY
CREATE UNIQUE INDEX idx_mv_trx_perjam_jam ON mv_trx_perjam(jam);

-- =============================================
-- MATERIALIZED VIEW UNTUK DATA PER SHIFT
-- =============================================
CREATE MATERIALIZED VIEW mv_trx_pershift AS
SELECT 
    shift,
    COUNT(*) AS total_transaksi,
    SUM(tarif) AS total_pendapatan,
    COUNT(DISTINCT dim_vehicle_id) AS unique_vehicles
FROM fact_toll_transactions
GROUP BY shift;

-- Index untuk shift
CREATE UNIQUE INDEX idx_mv_trx_pershift_shift ON mv_trx_pershift(shift);