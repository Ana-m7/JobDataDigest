# Streamlit App

## Run locally

```
pip install -r requirements.txt
streamlit run app/app.py
```

Opens at `http://localhost:8501`. No API key needed to run the app itself —
it reads the committed snapshot in `app/data/*.csv`, not the live Adzuna API
or the local SQLite database (see `app/export_app_data.py` for why that
snapshot exists and is committed while the rest of `data/` isn't).

## Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (public or private — Community Cloud supports both
   once your GitHub account is connected).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. **New app** -> pick this repo and branch -> set **Main file path** to
   `app/app.py` -> Deploy.
4. No secrets to configure: the app doesn't call the Adzuna API or need
   `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` at runtime, since it only reads the
   committed CSV snapshot.

To refresh the app's data after a new ingestion + cleaning run:

```
python -m app.export_app_data
git add app/data/*.csv
git commit -m "Refresh app data snapshot"
git push
```

Streamlit Community Cloud auto-redeploys on push to the connected branch.
