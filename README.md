# JobDataDigest

Turning live tech job postings into a clear read on the hiring market: which skills are actually in demand, what they pay, and where.

JobDataDigest pulls real job postings from the [Adzuna Job Search API](https://developer.adzuna.com/), cleans and stores them in SQLite, extracts the skills each posting asks for, and then answers concrete career questions through SQL analytics, an interpretable ML model, a Power BI dashboard, and a small Streamlit app.

The current analysis covers **4,858 unique postings** across **6 roles** and **6 Indian metros**, pulled on 2026-07-04.

## Key findings

From [`notebooks/03_sql_analytics.ipynb`](notebooks/03_sql_analytics.ipynb):

- **Python and SQL are the most transferable skills in this market.** They rank near the top for almost every role, and they appear together in more postings (196) than any other skill pair. In practice they behave like a shared baseline rather than two options you pick between.
- **Which role you target matters more for pay than which city.** The gap between roles is about ₹6L per year (Machine Learning Engineer at ₹17.6L down to Business Analyst at ₹11.6L). The gap between cities is only about ₹2L (Chennai ₹15.8L to Hyderabad ₹13.8L), roughly a third of the role gap.
- **Inferred seniority lines up with salary the way you'd hope:** Junior ₹7.0L, Mid ₹14.6L, Senior ₹17.3L. That clean progression doubles as a check that the seniority rule is picking up real signal and not just noise.
- **The best-paying individual skills are the data engineering and ML infrastructure tools** (Airflow ₹19.3L, GCP ₹18.9L, Deep Learning ₹18.1L), all comfortably above the ₹14.6L average across postings that disclose pay.

Each finding in the notebook is reported with its caveats (sample size, how many postings disclose salary, description truncation), because the goal was analysis that survives a follow-up question, not just charts.

## Architecture

```
Adzuna API
   |  ingestion/           paginated pulls, retry/backoff, dated raw JSON + manifest audit log
   v
data/raw/YYYY-MM-DD/*.json  (immutable raw layer)
   |  cleaning/            dedupe, city normalization, salary sanity checks, seniority inference
   v
data/jobdatadigest.db      (SQLite: postings, posting_roles, posting_skills)
   |  nlp/                 regex/dictionary skill extraction into posting_skills
   v
   |- notebooks/03_sql_analytics.ipynb   business questions answered in SQL
   |- notebooks/04_ml_model.ipynb        salary band prediction and evaluation
   |- models/                            trained, persisted model artifact
   |- dashboard/                         Power BI, built from exported CSVs
   |- app/                               Streamlit interactive demo
```

The database is a pure derived view of the raw layer. Cleaning and extraction wipe and rebuild the tables on every run, so if a rule turns out to be wrong you fix the rule and re-run rather than patching rows that are already loaded.

## Pipeline stages

**1. Ingestion** ([`ingestion/`](ingestion/)) pulls postings for each role and city from Adzuna with retry and backoff, writing dated raw JSON plus a `manifest.csv` audit log. A full run is about 126 API calls, tuned to stay under the free tier's 250 per day.

**2. Cleaning and load** ([`cleaning/`](cleaning/)) deduplicates postings that show up under more than one role search, merges Delhi and Gurgaon into "Delhi NCR", drops implausible salaries (anything below ₹1L per year, which are almost always monthly stipends mis-entered as annual pay), and loads the result into SQLite.

**3. Skill extraction** ([`nlp/`](nlp/)) matches a curated dictionary of about 65 skills against posting text using compiled regex. I chose this over spaCy NER because the set of skills is closed and known in advance, and because every match stays traceable to an explicit rule instead of a model's guess.

**4. Seniority inference** ([`nlp/seniority.py`](nlp/seniority.py)) reads Junior, Mid, Senior, or Unknown from years-of-experience mentions and title and description keywords. Unknown is kept as a real category rather than a forced guess, and those postings are left out of seniority-based analysis.

**5. SQL analytics** ([`notebooks/03_sql_analytics.ipynb`](notebooks/03_sql_analytics.ipynb)) answers the project's questions directly in SQL: skill demand, skill co-occurrence, salary by role, city, and seniority, and role concentration by city.

**6. ML model** ([`notebooks/04_ml_model.ipynb`](notebooks/04_ml_model.ipynb), [`models/`](models/)) predicts salary band (Low, Mid, High) from posting features with a leakage-checked, cross-validated Logistic Regression.

**7. Dashboard** ([`dashboard/`](dashboard/)) is a Power BI report. The build guide is in [`dashboard/README.md`](dashboard/README.md).

**8. App** ([`app/`](app/)) is a small Streamlit app: pick a role and city, see the top skills and average salary by seniority.

## The ML model

[`notebooks/04_ml_model.ipynb`](notebooks/04_ml_model.ipynb) predicts a posting's salary band (Low, Mid, High tertiles) from its role, city, inferred seniority, contract type, description length, and top-15 skill flags.

The notebook is written to be defensible rather than to chase a headline accuracy number:

- It starts with a leakage check: an explicit table of every field left out and why (raw salary, identifiers, free text).
- It reports a majority-class baseline that scores 36.0% accuracy but only 0.176 macro-F1, which shows the accuracy is mostly a class-imbalance artifact.
- Cross-validation actually changes the conclusion. Random Forest looked better on a single split (52.9% vs 48.4%), but that lead disappeared under 5-fold CV (45.3% vs 45.8%), so I kept the simpler and fully interpretable Logistic Regression (45.8% accuracy, 0.444 macro-F1).
- Because it's a linear model, the coefficients are readable. The strongest one in the whole model is Junior seniority pushing toward the Low band, which matches the salary pattern the SQL step found by hand.

## Power BI dashboard

<!-- TODO: add dashboard screenshots here once the .pbix is built.
     Save images to dashboard/screenshots/ and embed them, e.g.:
     ![Skill demand heatmap](dashboard/screenshots/heatmap.png)
     ![Salary by role and city](dashboard/screenshots/salary.png)
     Then replace this placeholder block with the images and a couple of
     lines on what the dashboard lets a user explore. -->

An interactive Power BI report built from the same SQLite data (exported to CSV). It covers a role by skill demand heatmap, salary distribution by role and city, a top-skills leaderboard, and slicers for role, city, and seniority.

**Dashboard screenshots coming soon.** The full build guide, including the data model, DAX measures, and visual setup, is in [`dashboard/README.md`](dashboard/README.md).

## Interactive app

The [Streamlit app](app/app.py) lets you filter by role and city and watch the top skills and average salary by seniority update live. The scope is intentionally small to keep the deployed app easy to reason about.

```bash
streamlit run app/app.py
```

<!-- TODO: add live app URL once deployed to Streamlit Community Cloud. -->

## Running it yourself

You'll need Python 3.11 or newer, and a free [Adzuna developer account](https://developer.adzuna.com/) for the API credentials.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Adzuna credentials
cp .env.example .env      # then fill in ADZUNA_APP_ID and ADZUNA_APP_KEY

# 3. Run the pipeline
python -m ingestion.run_ingestion    # pull raw postings from Adzuna
python -m cleaning.clean_and_load    # clean and load into SQLite
python -m nlp.extract_skills         # extract skills into posting_skills
python -m models.train_salary_model  # train and save the salary band model

# 4. Explore
jupyter notebook notebooks/          # SQL analytics and ML notebooks
streamlit run app/app.py             # interactive app
```

A couple of notes on what's in the repo. The notebooks are committed with their outputs, so you can read the full SQL analysis and model evaluation straight on GitHub without running anything. The Streamlit app also runs immediately after a clone, since it reads small CSV snapshots that are committed under [`app/data/`](app/data/). Everything else (the raw Adzuna pulls, the SQLite database, and the trained model file) is left out of version control on purpose because it's large or regenerated, so reproducing the data pipeline locally means running step 1 with your own Adzuna credentials and then steps 2 through 4.

## Tech stack

Python and `requests` for ingestion against the Adzuna REST API. SQLite for storage. pandas and NumPy for wrangling. Compiled regex over a curated dictionary for skill extraction. scikit-learn for the model (Logistic Regression inside a `ColumnTransformer` pipeline). Power BI, Plotly, matplotlib, and seaborn for visuals. Streamlit for the app.

## Data notes and limitations

Stated up front, because they decide how far each number should be pushed:

- **Salary coverage.** Only about 23% of postings (1,122 of 4,858) disclose pay, so every salary figure describes that subset, not the whole market.
- **Truncated descriptions.** Adzuna's free tier cuts descriptions at 500 characters, so skill counts undercount and should be read as relative demand, not absolute totals.
- **Rule-based inference.** Skill extraction and seniority labeling both use keyword rules. They can't fully read context, so a small share of postings will be labeled wrong.
- **Small cells.** A few of the per-role, per-city salary breakdowns rest on fewer than 40 postings. The notebook flags these as directional and worth re-checking on a bigger pull.

## Repository layout

```
ingestion/    Adzuna API client, config, runner
cleaning/     raw JSON to SQLite cleaning and load
nlp/          skill dictionary, skill extraction, seniority inference
sql/          database schema
notebooks/    03 SQL analytics, 04 ML model
models/       training script and saved model artifact
dashboard/    Power BI build guide and data export
app/          Streamlit app and data export
data/         raw pulls (data/raw/) and the SQLite database
```
