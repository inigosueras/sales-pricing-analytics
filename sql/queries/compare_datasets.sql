-- Compares aggregate KPIs across datasets (joined with the datasets registry
-- for readable names), used for the "compare datasets" view in the app.
SELECT
    d.dataset_id,
    d.dataset_name,
    d.industry_label,
    SUM(sales_data.Revenue)                                             AS revenue,
    SUM(sales_data.Margin)                                               AS margin,
    ROUND(100.0 * SUM(sales_data.Margin) / NULLIF(SUM(sales_data.Revenue), 0), 2)   AS margin_pct,
    SUM(sales_data.Quantity)                                             AS units,
    ROUND(SUM(sales_data.Revenue) / NULLIF(COUNT(*), 0), 2)                AS avg_ticket
FROM sales_data
JOIN datasets d ON d.dataset_id = sales_data.dataset_id
{where_clause}
GROUP BY d.dataset_id, d.dataset_name, d.industry_label
ORDER BY revenue DESC;
