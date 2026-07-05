"""Curated skill vocabulary for keyword/regex-based extraction.

Design choice -- regex over spaCy NER: Named Entity Recognition is built for
*open-set* extraction (arbitrary person/org/location names it's never seen
before). Our problem is closed-set: there are a few dozen skills we actually
care about, and we know all of them in advance. Direct phrase matching
against a curated list is more precise than NER for this, and -- critically
for a portfolio project -- every match is traceable to an explicit rule, not
a black-box model prediction. spaCy's PhraseMatcher would do essentially the
same lookup with more machinery; it's a reasonable v2 upgrade (mentioned in
the project README) if we needed to handle spelling variants at scale, but
isn't needed to get a defensible first version working.

Each skill maps to a list of (alias_text, case_sensitive) pairs. Most
aliases are safe to match case-insensitively. A few short/ambiguous tokens
(R, Go) are marked case_sensitive=True to cut down false positives -- e.g.
matching lowercase "r" would hit constantly on ordinary English text.
Plain "C" is deliberately excluded: it can't be reliably distinguished from
"C++"/"C#" with a word-boundary regex, and it's rarely the differentiating
skill in these fresher-role postings anyway. This is a documented
precision-over-recall call, not an oversight.
"""

SKILL_DICTIONARY: dict[str, list[tuple[str, bool]]] = {
    # Languages
    "Python": [("python", False)],
    "SQL": [("sql", False)],
    "Java": [("java", False)],
    "JavaScript": [("javascript", False), ("js", True)],
    "TypeScript": [("typescript", False)],
    "R": [("r", True)],
    "Scala": [("scala", False)],
    "Go": [("golang", False), ("go", True)],
    "C++": [("c++", False)],
    "C#": [("c#", False)],
    "PHP": [("php", False)],

    # BI / analyst tools
    "Excel": [("excel", False), ("ms excel", False)],
    "Power BI": [("power bi", False), ("powerbi", False)],
    "Tableau": [("tableau", False)],
    "Looker": [("looker", False)],
    "SAS": [("sas", True)],
    "SPSS": [("spss", False)],
    "QlikView": [("qlikview", False), ("qlik", False)],
    "VBA": [("vba", False)],
    "Google Analytics": [("google analytics", False)],

    # Cloud
    "AWS": [("aws", False), ("amazon web services", False)],
    "Azure": [("azure", False)],
    "GCP": [("gcp", False), ("google cloud", False)],

    # Big data / data engineering
    "Spark": [("spark", False), ("pyspark", False)],
    "Hadoop": [("hadoop", False)],
    "Kafka": [("kafka", False)],
    "Airflow": [("airflow", False)],
    "Hive": [("hive", False)],
    "ETL": [("etl", False)],
    "dbt": [("dbt", True)],

    # Databases
    "MySQL": [("mysql", False)],
    "PostgreSQL": [("postgresql", False), ("postgres", False)],
    "MongoDB": [("mongodb", False), ("mongo", False)],
    "Oracle": [("oracle", False)],
    "Redis": [("redis", False)],
    "Snowflake": [("snowflake", False)],
    "Redshift": [("redshift", False)],
    "BigQuery": [("bigquery", False)],
    "NoSQL": [("nosql", False)],

    # ML / AI
    "Machine Learning": [("machine learning", False), ("ml", True)],
    "Deep Learning": [("deep learning", False)],
    "TensorFlow": [("tensorflow", False)],
    "PyTorch": [("pytorch", False)],
    "scikit-learn": [("scikit-learn", False), ("sklearn", False)],
    "Keras": [("keras", False)],
    "NLP": [("nlp", True), ("natural language processing", False)],
    "Computer Vision": [("computer vision", False)],
    "Statistics": [("statistics", False), ("statistical analysis", False)],

    # Dev / infra
    "Git": [("git", False)],
    "Docker": [("docker", False)],
    "Kubernetes": [("kubernetes", False), ("k8s", False)],
    "Linux": [("linux", False)],
    "REST API": [("rest api", False), ("restful api", False)],
    "CI/CD": [("ci/cd", False), ("ci-cd", False)],
    "Jenkins": [("jenkins", False)],

    # Web
    "HTML": [("html", False)],
    "CSS": [("css", False)],
    "React": [("react", False), ("react.js", False), ("reactjs", False)],
    "Angular": [("angular", False)],
    "Node.js": [("node.js", False), ("nodejs", False)],
    "Django": [("django", False)],
    "Flask": [("flask", False)],
    ".NET": [(".net", False)],

    # Process / soft
    "Agile": [("agile", False)],
    "Scrum": [("scrum", False)],
    "JIRA": [("jira", False)],
    "A/B Testing": [("a/b testing", False), ("ab testing", False)],
}
