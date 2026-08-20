# Universal Sales & Pricing Analytics Tool

A plug-and-play commercial analytics dashboard. Upload a sales file with a fixed column structure and get a complete pricing & sales analysis — KPIs, trends, top products, geographic breakdown, price/volume decomposition, customer segment analysis, and free-form multi-dimension pivoting — automatically, with no manual configuration.

Built to demonstrate an end-to-end BI/Pricing Analytics tool: not just an analysis of one dataset, but a reusable engine that works across industries (retail, pharma, manufacturing, or any other sales data following the same schema).

## Live demo

**[inigoserrano-sales-pricing-analytics.streamlit.app](https://inigoserrano-sales-pricing-analytics.streamlit.app/)**

Use the "Load sample" buttons on the Home page for an instant demo — no upload needed.

## Why this project

Most portfolio pieces show "I analyzed a dataset." This one shows "I built a tool that analyzes any dataset." The same Python engine, tested across three unrelated industries with zero code changes, powers both an interactive web app and a ready-to-use Power BI template (`.pbit`, verified number-for-number against Python) — the two environments a BI/Pricing Analytics professional is typically expected to work in.

## What it does

Upload a CSV/Excel file with these exact columns:

```
Date | Product | Category | Country | Revenue | Quantity | Cost | Customer_Segment
```

The tool automatically generates:

- **Main KPIs** — total revenue, margin %, average ticket, units sold, distinct products/countries
- **Monthly/quarterly trend** with year-over-year (YoY) comparison
- **Top 10 products and categories** by revenue, margin, or units
- **Geographic distribution** — choropleth map (auto-zoomed to the region with data) and table by country
- **Price vs. volume decomposition** — how much of a revenue change comes from price vs. quantity
- **Customer segment analysis** — revenue share and margin by segment
- **Pivot Explorer** — combine 1 to 3 dimensions freely (e.g. Country + Category + Product), visualized as a treemap, like an Excel PivotTable
- **Multi-dataset comparison** — load several files at once (e.g. retail + pharma) and compare their KPIs side by side
- **Filters** — period, country, category, segment, and dataset selection, persisted across pages within a session (deselecting a dataset filters the view, exactly like a Power BI slicer — it never deletes the underlying data)

It also automatically cleans the data: near-duplicate category text (e.g. `"Online"`, `"on-line"`, `"ONLINE "`) is merged into a single canonical label using deterministic normalization plus optional fuzzy matching for typos — without ever merging genuinely distinct short codes (e.g. `"US"` vs `"UK"`).

## Project structure

```
sales-pricing-analytics/
├── data/
│   ├── schema.py              # Single source of truth for the required column schema
│   ├── generate_samples.py    # Generates the 3 sample datasets
│   └── samples/                # Retail, pharma, manufacturing sample CSVs
│
├── src/                        # Core Python engine (framework-agnostic, independently testable)
│   ├── validator.py            # Column/dtype/value validation with actionable error reports
│   ├── normalizer.py           # Near-duplicate category text grouping (deterministic + fuzzy)
│   ├── transformer.py          # Derived metrics: margin, avg price, YoY, price/volume decomposition
│   ├── db.py                   # SQLite loader, multi-dataset support, injection-safe filters
│   └── metrics.py              # Typed API wrapping SQL queries for the app layer
│
├── sql/
│   ├── schema.sql               # SQLite DDL (datasets registry + sales_data, multi-dataset design)
│   └── queries/                 # One .sql file per standardized metric query
│
├── app/                         # Streamlit web application
│   ├── streamlit_app.py         # Entry point: upload, validation, dataset manager
│   ├── pages/                   # Overview, Trends, Products & Categories, Geography, Price/Volume, Segments, Explorer
│   └── components/              # Reusable filters (session-persisted), KPI cards, Plotly chart builders
│
├── powerbi/                     # Power BI template — ready to use
│   ├── Universal_Sales_Pricing_Template.pbit  # The completed .pbit template
│   ├── power_query_m_script.txt # M code: dynamic file-path parameter, validation, cleaning, derived fields
│   ├── dax_measures.txt         # DAX measures mirroring the SQL queries
│   └── BUILD_GUIDE.md           # Step-by-step guide showing how the template was assembled
│
└── tests/                       # 32 automated tests covering validator, normalizer, transformer, db
```

## Tech stack

- **Python** — pandas for data validation, cleaning, and derived-field calculation
- **SQLite** — stores the cleaned dataset, runs standardized SQL metric queries (parameterized, injection-safe), supports multi-dimension GROUP BY for the Pivot Explorer
- **Streamlit + Plotly** — interactive web app, deployable on Streamlit Cloud
- **Power BI** — `.pbit` template with a dynamic Power Query file-path parameter, connects to any conforming CSV

## Running it locally

Requirements: Python 3.10+

```bash
# 1. Clone the repository
git clone https://github.com/inigosueras/sales-pricing-analytics.git
cd sales-pricing-analytics

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app/streamlit_app.py
```

The app opens in your browser at `http://localhost:8501`.

## Running the test suite

```bash
pip install pytest
python -m pytest tests/ -v
```

32 tests cover: schema validation (missing columns, bad types, negative/zero values), category normalization (exact and fuzzy grouping, safety guards against false merges), derived metric calculations (margin, YoY, price/volume decomposition reconciliation), and the database layer (multi-dataset isolation, filter correctness, SQL injection safety — including the dynamic multi-dimension queries behind the Pivot Explorer).

## Power BI template

The ready-to-use template is [`powerbi/Universal_Sales_Pricing_Template.pbit`](powerbi/Universal_Sales_Pricing_Template.pbit) — download it, open it in Power BI Desktop, and when prompted, point the `FilePath` parameter to any CSV following the required schema (e.g. one of the files in `data/samples/`). The report rebuilds automatically.

Its KPIs were verified number-for-number against the Python engine using the retail sample dataset.

If you want to see how it was built, or build your own variant, [`powerbi/BUILD_GUIDE.md`](powerbi/BUILD_GUIDE.md) has the full step-by-step assembly guide, with the underlying M script and DAX measures.

## Data & security notes

- The three sample datasets (`data/samples/`) are **synthetically generated** — no real company data is included in this repository.
- All processing is local to the SQLite session; no data is sent to any external service.
- SQL filter values and dynamic GROUP BY dimensions are never string-interpolated from raw user input — filter values are parameterized, and dimension/column names are checked against a fixed allowlist. Both are tested explicitly against injection attempts.
- If you deploy this publicly (e.g. free Streamlit Cloud tier), do not upload sensitive/real business data — anyone with the link could upload a file and view the resulting dashboard, since there is no authentication layer built in.

## Author

Built by **Iñigo Serrano** — BI & Pricing Analytics professional, 3 years of experience across Power BI (DAX, Power Query), SQL, Python, and Microsoft Dynamics CRM, managing 1.8M+ pricing records across 15+ international markets.

[LinkedIn](https://www.linkedin.com/in/iñigo-serrano-m) · [GitHub](https://github.com/inigosueras)
