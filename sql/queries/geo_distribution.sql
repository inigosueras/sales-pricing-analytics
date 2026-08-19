-- Revenue, margin and units broken down by Country.
SELECT
    Country,
    SUM(Revenue)                                        AS revenue,
    SUM(Margin)                                          AS margin,
    ROUND(100.0 * SUM(Margin) / NULLIF(SUM(Revenue), 0), 2)  AS margin_pct,
    SUM(Quantity)                                        AS units,
    ROUND(SUM(Revenue) / NULLIF(SUM(Quantity), 0), 2)      AS avg_price
FROM sales_data
{where_clause}
GROUP BY Country
ORDER BY revenue DESC;
