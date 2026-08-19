-- Revenue & margin trend by month, for YoY comparison in Python (transformer.compute_yoy_table
-- handles the prior-year join since SQLite window functions on custom offsets are cumbersome).
SELECT
    YearMonth,
    SUM(Revenue)   AS revenue,
    SUM(Margin)    AS margin,
    SUM(Quantity)  AS units
FROM sales_data
{where_clause}
GROUP BY YearMonth
ORDER BY YearMonth;
