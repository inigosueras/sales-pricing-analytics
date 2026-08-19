-- Top N by {dimension} (Product or Category), ranked by revenue.
-- {dimension} and {where_clause} injected by src/metrics.py.
SELECT
    {dimension}                                       AS name,
    SUM(Revenue)                                       AS revenue,
    SUM(Margin)                                         AS margin,
    ROUND(100.0 * SUM(Margin) / NULLIF(SUM(Revenue), 0), 2) AS margin_pct,
    SUM(Quantity)                                       AS units
FROM sales_data
{where_clause}
GROUP BY {dimension}
ORDER BY revenue DESC
LIMIT {limit};
