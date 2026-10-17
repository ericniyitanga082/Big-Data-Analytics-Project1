-- Location: sql/4_dashboard_analytics.sql
-- Section 5.1 & 7.2: PANEL 1 - Hourly Regional Energy Profile (Continuous View)
SELECT bucket AS "time", region AS metric, total_energy_kwh AS "energy_kwh"
FROM grid_agg_hourly
WHERE bucket >= '2026-09-22 00:00:00+02' AND bucket <= '2026-09-29 00:00:00+02'
ORDER BY 1;

-- Section 5.1 & 7.2: PANEL 2 - Daily Network System Consumption Profile
SELECT time_bucket('1 day', bucket) AS "time", 'Total Materialized System Load' AS metric, SUM(total_energy_kwh) AS "energy_kwh"
FROM grid_agg_15min
WHERE bucket >= '2026-09-22 00:00:00+02' AND bucket <= '2026-09-29 00:00:00+02'
GROUP BY 1 ORDER BY 1;

-- Section 5.1 & 7.2: PANEL 3 - Periodic Seven-Day Demand Distribution Curve
SELECT period_label AS metric, SUM(total_energy_kwh) AS "energy_kwh"
FROM (
  SELECT 
    CASE 
      WHEN bucket >= '2026-09-01 00:00:00+02' AND bucket < '2026-09-08 00:00:00+02' THEN 'Period 1 (Sep 01-07)'
      WHEN bucket >= '2026-09-08 00:00:00+02' AND bucket < '2026-09-15 00:00:00+02' THEN 'Period 2 (Sep 08-14)'
      WHEN bucket >= '2026-09-15 00:00:00+02' AND bucket < '2026-09-22 00:00:00+02' THEN 'Period 3 (Sep 15-21)'
      WHEN bucket >= '2026-09-22 00:00:00+02' AND bucket < '2026-09-29 00:00:00+02' THEN 'Period 4 (Sep 22-28)'
    END AS period_label,
    total_energy_kwh
  FROM grid_agg_15min
  WHERE bucket >= '2026-09-01 00:00:00+02' AND bucket <= '2026-09-28 23:45:00+02'
) AS sub
WHERE period_label IS NOT NULL
GROUP BY period_label;

-- Section 5.1 & 7.2: PANEL 4 - Individual Meter Node Tracker Load Curve
SELECT bucket AS "time", 'Meter 1000000000' AS metric, total_energy_kwh AS "energy_kwh"
FROM grid_agg_daily
WHERE meter_id = 1000000000 AND bucket >= '2026-09-22 00:00:00+02' AND bucket <= '2026-09-29 00:00:00+02'
ORDER BY 1;

-- Section 5.3 & 7.2: PANEL 5 - Unified Substation Telemetry Completeness Rate
SELECT region AS metric, (SUM(reading_count) / (400.0 * 2688.0)) * 100 AS "completeness_pct"
FROM grid_agg_15min
WHERE bucket >= '2026-09-01 00:00:00+02' AND bucket <= '2026-09-28 23:45:00+02'
GROUP BY region;
