"""Train and persist the final salary-band model.

Model and feature choices are justified in notebooks/04_ml_model.ipynb --
this script just re-fits the same Logistic Regression pipeline on the full
labeled dataset (rather than the 80% training split used for evaluation) and
saves it, so the evaluated metrics in the notebook and the shipped model
artifact aren't the same object trained on less data than necessary.

Usage:
    python -m models.train_salary_model
"""

from __future__ import annotations

import sqlite3

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from cleaning.config import DB_PATH, PROJECT_ROOT

TOP_N_SKILLS = 15
MODEL_PATH = PROJECT_ROOT / "models" / "salary_band_model.joblib"

CAT_COLS = ["primary_role", "city", "seniority", "contract_type", "contract_time"]


def build_feature_frame(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    postings = pd.read_sql_query(
        """
        SELECT posting_id, primary_role, city, seniority, description_length,
               contract_type, contract_time, salary_avg
        FROM postings WHERE has_salary = 1
        """,
        conn,
    )
    skills = pd.read_sql_query("SELECT posting_id, skill FROM posting_skills", conn)
    top_skills = pd.read_sql_query(
        f"""
        SELECT skill, COUNT(DISTINCT posting_id) AS n FROM posting_skills
        GROUP BY skill ORDER BY n DESC LIMIT {TOP_N_SKILLS}
        """,
        conn,
    )["skill"].tolist()

    num_skills = skills.groupby("posting_id").size().rename("num_skills")
    skill_flags = (
        skills[skills.skill.isin(top_skills)]
        .assign(present=1)
        .pivot_table(index="posting_id", columns="skill", values="present", fill_value=0)
    )

    df = postings.merge(num_skills, on="posting_id", how="left").merge(
        skill_flags, on="posting_id", how="left"
    )
    df["num_skills"] = df["num_skills"].fillna(0)
    for skill in top_skills:
        df[skill] = df[skill].fillna(0)
    df["contract_type"] = df["contract_type"].fillna("Unknown")
    df["contract_time"] = df["contract_time"].fillna("Unknown")
    df["salary_band"] = pd.qcut(df["salary_avg"], 3, labels=["Low", "Mid", "High"])

    num_cols = ["description_length", "num_skills"] + top_skills
    X = df[CAT_COLS + num_cols]
    y = df["salary_band"]
    return X, y, top_skills


def run() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        X, y, top_skills = build_feature_frame(conn)
    finally:
        conn.close()

    num_cols = ["description_length", "num_skills"] + top_skills
    preprocessor = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
            ("num", StandardScaler(), num_cols),
        ]
    )
    model = Pipeline([("pre", preprocessor), ("clf", LogisticRegression(max_iter=1000))])
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "top_skills": top_skills, "cat_cols": CAT_COLS}, MODEL_PATH)
    print(f"Trained on {len(X)} labeled postings. Saved to {MODEL_PATH}")


if __name__ == "__main__":
    run()
