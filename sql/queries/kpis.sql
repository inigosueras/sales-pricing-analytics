-- Main KPI summary: total revenue, total margin, margin %, avg ticket, units sold.
-- {where_clause} is injected by src/metrics.py based on active dashboard filters.
SELECT
    SUM(Revenue)                              AS total_revenue,
    SUM(Margin)                               AS total_margin,
    ROUND(100.0 * SUM(Margin) / NULLIF(SUM(Revenue), 0), 2)   AS margin_pct,
    ROUND(SUM(Revenue) / NULLIF(COUNT(*), 0), 2)               AS avg_ticket,
    SUM(Quantity)                             AS total_units,
    COUNT(DISTINCT Product)                   AS distinct_products,
    COUNT(DISTINCT Country)                   AS distinct_countries
FROM sales_data
{where_clause};
