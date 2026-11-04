"""Download Minneapolis active rental licenses and load them into BigQuery.

Run from the project root:
    python -m src.pipeline
"""

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.fetch import fetch_all
from src.load_bigquery import load_dataframe

LICENSES_URL = (
    "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
    "Active_Rental_Licenses/FeatureServer/0"
)
RAW_DIR = Path("data/raw")
TABLE_NAME = "active_rental_licenses"

# Personal contact details the app doesn't need. Leaving them out keeps
# private information out of our database.
DROP_COLUMNS = ["ownerPhone", "ownerEmail", "applicantPhone", "applicantEmail"]


def to_snake_case(name: str) -> str:
    """licenseNumber -> license_number, OBJECTID -> objectid."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def main() -> None:
    load_dotenv()
    project_id = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ.get("BQ_DATASET", "mpls_rentals")

    print("Downloading active rental licenses...")
    records = fetch_all(LICENSES_URL)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"active_rental_licenses_{date.today().isoformat()}.json"
    raw_path.write_text(json.dumps(records))
    print(f"Saved raw copy to {raw_path}")

    df = pd.DataFrame(records).drop(columns=DROP_COLUMNS, errors="ignore")
    df.columns = [to_snake_case(c) for c in df.columns]
    df["loaded_at"] = datetime.now(timezone.utc)  # when this snapshot was taken

    load_dataframe(df, project_id, dataset, TABLE_NAME)
    print("Done.")


if __name__ == "__main__":
    main()