"""Rebuild the summary tables the website reads from, using the SQL files in sql/.

Run on its own (without re-downloading data):
    python -m src.build_tables
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

SQL_DIR = Path("sql")
# Order matters: each table reads from the ones before it.
SQL_FILES = ["violations_clean.sql", "rental_properties.sql", "owners.sql"]


def build_tables(project_id: str, dataset: str) -> None:
    client = bigquery.Client(project=project_id)
    for filename in SQL_FILES:
        sql = (SQL_DIR / filename).read_text()
        sql = sql.replace("{project}", project_id).replace("{dataset}", dataset)
        client.query(sql).result()  # wait until the table is built
        print(f"Built table from {filename}")


if __name__ == "__main__":
    load_dotenv()
    build_tables(os.environ["GCP_PROJECT_ID"], os.environ.get("BQ_DATASET", "mpls_rentals"))