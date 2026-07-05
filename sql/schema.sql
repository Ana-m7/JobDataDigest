-- JobDataDigest analytics schema (SQLite).
--
-- Design note: `postings` is keyed by Adzuna's own posting_id, not by
-- (role, city) search combo. The same real-world job can legitimately match
-- more than one role search (e.g. a "Data Analyst / Scientist" hybrid
-- posting) or appear the same in two different city searches. Rather than
-- pick one role and silently drop that information, we model role-matching
-- as many-to-many via posting_roles -- the same pattern we'll reuse for
-- posting_skills in Step 3.

CREATE TABLE IF NOT EXISTS postings (
    posting_id            TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    company               TEXT,
    description           TEXT,
    description_length    INTEGER NOT NULL,
    description_truncated INTEGER NOT NULL,  -- 1 if Adzuna cut it off at 500 chars (free-tier limit)
    primary_role          TEXT NOT NULL,     -- most-specific role this posting matched (see ROLE_PRIORITY)
    seniority             TEXT NOT NULL,     -- Junior / Mid / Senior / Unknown, inferred (see nlp/seniority.py)
    location_raw          TEXT,              -- Adzuna's own display_name, kept for reference/debugging
    city                  TEXT NOT NULL,     -- normalized search-city bucket (Delhi + Gurgaon -> 'Delhi NCR')
    state                 TEXT,
    category              TEXT,
    contract_type         TEXT,              -- permanent / contract, nullable
    contract_time         TEXT,              -- full_time / part_time, nullable
    salary_min            REAL,
    salary_max            REAL,
    salary_avg            REAL,              -- midpoint of min/max, or whichever bound is present
    has_salary            INTEGER NOT NULL,  -- 0/1: most postings don't disclose pay at all
    created_date          TEXT,              -- Adzuna's posting creation date (ISO)
    redirect_url          TEXT,
    pull_date             TEXT NOT NULL      -- which ingestion run last saw this posting
);

CREATE TABLE IF NOT EXISTS posting_roles (
    posting_id TEXT NOT NULL REFERENCES postings(posting_id),
    role       TEXT NOT NULL,
    PRIMARY KEY (posting_id, role)
);

CREATE INDEX IF NOT EXISTS idx_postings_city ON postings(city);
CREATE INDEX IF NOT EXISTS idx_postings_primary_role ON postings(primary_role);
CREATE INDEX IF NOT EXISTS idx_postings_has_salary ON postings(has_salary);
CREATE INDEX IF NOT EXISTS idx_posting_roles_role ON posting_roles(role);

-- Step 3 (NLP skill extraction): one row per posting-skill pair found by
-- nlp/extract_skills.py. Same many-to-many pattern as posting_roles.
CREATE TABLE IF NOT EXISTS posting_skills (
    posting_id TEXT NOT NULL REFERENCES postings(posting_id),
    skill      TEXT NOT NULL,
    PRIMARY KEY (posting_id, skill)
);

CREATE INDEX IF NOT EXISTS idx_posting_skills_skill ON posting_skills(skill);
