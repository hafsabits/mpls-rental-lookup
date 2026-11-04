"""Download Minneapolis rental licenses and code violations, then load them into BigQuery.

Run from the project root:
    python -m src.pipeline
"""

import gzip
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.fetch import fetch_all
from src.load_bigquery import load_dataframe

BASE_URL = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services"
RAW_DIR = Path("data/raw")


@dataclass
class Dataset:
    name: str        # BigQuery table name and raw file prefix
    url: str         # ArcGIS layer URL
    page_size: int   # the most records the server returns per request
    drop_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)  # dates sent as epoch milliseconds


DATASETS = [
    Dataset(
        name="active_rental_licenses",
        url=f"{BASE_URL}/Active_Rental_Licenses/FeatureServer/0",
        page_size=2000,
        # Personal contact details the app doesn't need.
        drop_columns=["ownerPhone", "ownerEmail", "applicantPhone", "applicantEmail"],
    ),
    Dataset(
        name="code_violations",
        url=f"{BASE_URL}/CaseViolations/FeatureServer/0",
        page_size=16000,
        date_columns=["Processed_Date", "Resolved_Date"],
    ),
]


def to_snake_case(name: str) -> str:
    """licenseNumber -> license_number, Processed_Date -> processed_date."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def run(dataset: Dataset, project_id: str, bq_dataset: str) -> None:
    """Download one dataset, save a compressed raw copy, clean it, and load it."""
    print(f"\n=== {dataset.name} ===")
    records = fetch_all(dataset.url, page_size=dataset.page_size)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{dataset.name}_{date.today().isoformat()}.json.gz"
    with gzip.open(raw_path, "wt", encoding="utf-8") as f:
        json.dump(records, f)
    print(f"Saved raw copy to {raw_path}")

    df = pd.DataFrame(records).drop(columns=dataset.drop_columns, errors="ignore")
    for col in dataset.date_columns:
        df[col] = pd.to_datetime(df[col], unit="ms", utc=True)
    df.columns = [to_snake_case(c) for c in df.columns]
    df["loaded_at"] = datetime.now(timezone.utc)

    load_dataframe(df, project_id, bq_dataset, dataset.name)


def main() -> None:
    load_dotenv()
    project_id = os.environ["GCP_PROJECT_ID"]
    bq_dataset = os.environ.get("BQ_DATASET", "mpls_rentals")

    for dataset in DATASETS:
        run(dataset, project_id, bq_dataset)
    print("\nDone.")


if __name__ == "__main__":
    main()