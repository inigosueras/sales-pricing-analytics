# Power BI Template — Build Guide

This guide walks you through assembling the `.pbit` template in Power BI
Desktop, using the two files in this folder:
- `power_query_m_script.txt` — the M code that loads and cleans any CSV
- `dax_measures.txt` — the DAX measures for KPIs, YoY, price/volume, segments

**Requirements:** Power BI Desktop (free, Windows only). Download from
the Microsoft Store or powerbi.microsoft.com if you don't have it yet.

Estimated time: 30–45 minutes the first time.

---

## Step 1 — Create the FilePath parameter

1. Open Power BI Desktop -> **Home** -> **Transform Data** (opens Power Query Editor)
2. **Home** -> **Manage Parameters** -> **New Parameter**
3. Name: `FilePath` · Type: `Text` · Current Value: the full path to one of
   the sample CSVs (e.g. `C:\Users\YourName\Downloads\retail_sales.csv`)
4. Click OK

## Step 2 — Create the DateDimension query (optional but recommended)

1. **Home** -> **New Source** -> **Blank Query**
2. Rename it to `DateDimension` (right-click in the Queries pane -> Rename)
3. **Home** -> **Advanced Editor** -> delete the placeholder text -> paste
   the commented `DateDimension` block from the bottom of
   `power_query_m_script.txt` (remove the `//` comment markers first)
4. Click **Done**

## Step 3 — Create the SalesData query

1. **Home** -> **New Source** -> **Blank Query**
2. Rename it to `SalesData`
3. **Home** -> **Advanced Editor** -> delete the placeholder text -> paste
   the full `SalesData` query block from `power_query_m_script.txt`
   (everything between `let` and `in FinalTable`, not including the
   commented Params/DateDimension sections)
4. Click **Done** — you should see a preview table with all 16 columns
   (8 original + 8 derived: Margin, Margin_Pct, Avg_Price, Unit_Cost,
   Year, Quarter, Month, YearMonth)

If you see a red error instead: check that `FilePath` (Step 1) points to
a real file, and that the file has the exact 8 required column headers.

## Step 4 — Build the relationship

1. Still in Power Query Editor, click **Close & Apply** (top left)
2. Go to the **Model** view (left sidebar icon that looks like connected boxes)
3. Drag from `SalesData[Date]` to `DateDimension[Date]` to create a
   relationship (if not created automatically)
4. Double-click the relationship line -> confirm it's **1 (DateDimension)
   to many (SalesData)**, single direction

## Step 5 — Mark the Date table

1. Click on `DateDimension` in the Fields pane
2. **Table tools** (ribbon) -> **Mark as Date Table** -> select the `Date` column
3. Confirm

This step is required for the YoY DAX measures (`SAMEPERIODLASTYEAR`) to
work correctly.

## Step 6 — Add the DAX measures

1. Right-click `SalesData` in the Fields pane -> **New Measure**
2. Open `dax_measures.txt`, copy one measure at a time (the line starting
   with the measure name, e.g. `Total Revenue = SUM ( SalesData[Revenue] )`)
3. Paste into the formula bar, press Enter
4. Repeat for all measures in Sections 1–5 (Section 6 is just a note, not
   a measure to paste)

Tip: paste them in order — some measures (e.g. `Margin %`) reference
earlier ones (`Total Margin`, `Total Revenue`), so Power BI needs those
to exist first.

## Step 7 — Build the report pages

Create one page per analysis area, mirroring the Streamlit app:

| Page | Suggested visuals |
|---|---|
| Overview | Card visuals: Total Revenue, Margin %, Avg Ticket, Total Units. Line chart: Total Revenue by YearMonth |
| Trends | Line chart: Total Revenue + Revenue Prior Year by YearMonth. Bar chart: Revenue YoY % by YearMonth |
| Products & Categories | Bar chart: Total Revenue by Product (Top N filter = 10). Same for Category |
| Geography | Filled Map or Shape Map: Total Revenue by Country. Table: Country, Total Revenue, Margin % |
| Price / Volume | Bar chart: Price Effect + Volume Effect by Product (filter to one Year/Quarter) |
| Segments | Donut chart: Total Revenue by Customer_Segment. Bar chart: Margin % by Customer_Segment |

Add slicers for `Country`, `Category`, `Customer_Segment`, and
`DateDimension[Date]` (as a date range slicer) on every page, or on a
single filter panel synced across pages (**View** -> **Sync Slicers**).

## Step 8 — Save as a template

1. **File** -> **Save As**
2. Save type: **Power BI template files (*.pbit)**
3. Name it `Universal_Sales_Pricing_Template.pbit`
4. When prompted for a description, add something like: *"Connect to any
   CSV with columns Date, Product, Category, Country, Revenue, Quantity,
   Cost, Customer_Segment to generate a full commercial analytics report."*

That's it — from now on, opening this `.pbit` file will prompt anyone
for a `FilePath` value, and the whole report rebuilds automatically
against their file.

---

## Testing it works

1. Open the saved `.pbit` file (double-click it)
2. When prompted, enter the path to a *different* sample file (e.g. switch
   from `retail_sales.csv` to `pharma_sales.csv`)
3. Confirm all visuals update correctly with no manual reconfiguration —
   this is the proof that the template is genuinely universal, exactly
   like the Python/Streamlit tool.

## Known limitations vs. the Python/Streamlit tool

- **Fuzzy typo matching** ("Wholesle" -> "Wholesale") is not replicated in
  the M script — Power Query has no built-in string-similarity function.
  The M script only does the deterministic cleanup (case, spacing,
  separators), which covers the large majority of real-world messiness.
- **Multi-dataset comparison** requires manually appending queries with a
  `Dataset` column added first (see Section 6 of `dax_measures.txt`) —
  it isn't automatic like in the Streamlit app's dataset picker.
