-- Revenue, margin, avg ticket and units by Customer_Segment.
SELECT
    Customer_Segment                                     AS segment,
    SUM(Revenue)                                          AS revenue,
    SUM(Margin)                                            AS margin,
    ROUND(100.0 * SUM(Margin) / NULLIF(SUM(Revenue), 0), 2)   AS margin_pct,
    SUM(Quantity)                                          AS units,
    ROUND(SUM(Revenue) / NULLIF(COUNT(*), 0), 2)              AS avg_ticket,
    COUNT(DISTINCT Product)                                 AS distinct_products
FROM sales_data
{where_clause}
GROUP BY Customer_Segment
ORDER BY revenue DESC;
