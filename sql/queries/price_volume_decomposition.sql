-- Pulls revenue & quantity by {dimension} for the two periods being compared.
-- The price/volume/mix decomposition math itself lives in
-- src/transformer.compute_price_volume_decomposition (row-level math is
-- clearer and more testable in pandas than in SQL).
SELECT
    {dimension}   AS dimension_value,
    YearMonth,
    SUM(Revenue)   AS revenue,
    SUM(Quantity)  AS quantity
FROM sales_data
{where_clause}
GROUP BY {dimension}, YearMonth
ORDER BY {dimension}, YearMonth;
