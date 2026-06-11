# China Export Dashboard Design

## Goal

Build a Streamlit dashboard for analyzing commodity shipments loaded in China and discharged outside China from the MySQL table `axs`.

## Data Scope

The base query always applies:

```sql
load_country = 'China'
AND discharge_country <> 'China'
```

The dashboard reads these columns:

- `load_start_date`
- `voy_intake_mt`
- `COMMODITY`
- `discharge_country`

Rows with a missing date, commodity, or shipment volume are excluded from analysis.

## Filters

The sidebar contains:

- Date range
- Time grain: Daily, Weekly, or Monthly
- Searchable multi-select commodity filter
- Searchable multi-select discharge-country filter

No selected commodity means all commodities. When one or more commodities are selected, all headline metrics and the main trend follow that selection.

## Dashboard Layout

1. Headline metrics:
   - Total shipment volume for the current filters
   - Change between the latest two periods
   - Distinct commodity count
   - Largest commodity by shipment volume
2. Main shipment-volume trend at the selected time grain.
3. Top 10 commodity ranking for the current date and destination filters.
4. Trend comparison for those Top 10 commodities, with no `Other` group.
5. Filtered detail table for inspection only. No data download feature.

## Metric Semantics

The total shipment volume is never fixed to Top 10:

- No commodity selected: sum all commodities within the active date and destination filters.
- One commodity selected: sum that commodity.
- Multiple commodities selected: sum the selected commodities.

The Top 10 charts are comparison views only and do not redefine the headline total.

## Architecture

- `src/database.py`: create the MySQL connection and load the scoped source data.
- `src/analytics.py`: clean, filter, aggregate, and calculate metrics.
- `app.py`: render Streamlit controls, metrics, Plotly charts, and detail table.
- `.streamlit/secrets.toml.example`: document required secrets without storing credentials.

The query is cached by Streamlit to avoid repeatedly loading a large table during one session. The first version loads the scoped China-export columns, then applies interactive filters in memory.

## Error Handling

- Missing Streamlit secrets produce a clear setup message.
- Database failures produce a clear user-facing error.
- Empty filter results render an explanatory message instead of broken charts.
- Invalid or missing source values are removed during normalization.

## Testing

Unit tests cover:

- The fixed SQL scope and selected columns.
- Daily, weekly, and monthly aggregation.
- Commodity and destination filtering.
- Headline metric semantics.
- Top 10 ranking without an `Other` group.
