# Export Monitor

Streamlit dashboard for commodity shipments loaded in China or Brazil and discharged outside the selected load country.

## Dashboard behavior

- Sidebar navigation switches the load country between China and Brazil
- Fixed SQL scope for the selected country: `load_country = :load_country` and `discharge_country <> :load_country`
- Daily, weekly, and monthly shipment-volume views
- Searchable commodity and destination filters
- Headline total follows the active commodity filter
- Top 10 commodity ranking without an `Other` group
- Top 20 destination ranking by shipment count and shipment volume
- Selected commodities appear as separate lines in the main shipment-volume trend
- Inspection-only detail table with no download feature, limited to the latest 1,000 rows for browser performance
- Weekly daily-average comparison against the previous five years and historical ranges
- Current-year weekly daily-average bars with a rolling four-week average

## Local setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` using `.streamlit/secrets.toml.example`:

```toml
[mysql]
host = "your-server.mysql.database.azure.com"
database = "axs"
user = "your-user"
password = "your-password"
port = 3306
```

Run:

```bash
streamlit run app.py
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Streamlit Community Cloud

After the repository is pushed to GitHub:

1. Create a Streamlit Community Cloud app using `app.py`.
2. Add the same `[mysql]` block under the app's Secrets settings.
3. Ensure the Azure MySQL firewall permits connections from Streamlit Cloud.

Real credentials are intentionally excluded from this repository.
