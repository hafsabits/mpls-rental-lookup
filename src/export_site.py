"""Export the website's data from BigQuery into static JSON files in site/data/.

Run from the project root, after the pipeline:
    python -m src.export_site
"""

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

OUT_DIR = Path("site/data")


def main() -> None:
    load_dotenv()
    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ.get("BQ_DATASET", "mpls_rentals")
    client = bigquery.Client(project=project)

    def table(name: str) -> str:
        return f"`{project}.{dataset}.{name}`"

    print("Querying BigQuery...")
    properties = client.query(f"""
        SELECT license_number, apn, address, tier, status, units, expiration_date,
               owner_name, owner_key, neighborhood,
               violations_total, violations_2yr, violations_open, violations_2yr_per_unit
        FROM {table('rental_properties')}
        ORDER BY address
    """).to_dataframe()

    owners = client.query(f"""
        SELECT owner_key, owner_name, properties, units,
               violations_open, violations_2yr, violations_2yr_per_unit
        FROM {table('owners')}
        ORDER BY units DESC
    """).to_dataframe()

    violations = client.query(f"""
        SELECT apn,
               FORMAT_TIMESTAMP('%Y-%m-%d', processed_date) AS processed,
               category, description, status,
               FORMAT_TIMESTAMP('%Y-%m-%d', resolved_date) AS resolved
        FROM {table('violations_clean')}
        WHERE apn IN (SELECT DISTINCT apn FROM {table('rental_properties')})
        ORDER BY apn, processed_date DESC
    """).to_dataframe()

    loaded_at = client.query(
        f"SELECT MAX(loaded_at) AS t FROM {table('rental_properties')}"
    ).to_dataframe()["t"].iloc[0]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # to_json turns missing values into null, which JavaScript can read
    properties.to_json(OUT_DIR / "properties.json", orient="records")
    owners.to_json(OUT_DIR / "owners.json", orient="records")

    # Split violations into 100 files by the last 2 characters of the parcel ID.
    # A visitor downloads only the one small file their property is in.
    shard_dir = OUT_DIR / "violations"
    if shard_dir.exists():
        shutil.rmtree(shard_dir)  # clear last run's files
    shard_dir.mkdir(parents=True)

    violations = violations.astype(object).where(violations.notna(), None)
    columns = ["processed", "category", "description", "status", "resolved"]
    shards: dict[str, dict] = defaultdict(dict)
    for apn, group in violations.groupby("apn", sort=False):
        shards[apn[-2:]][apn] = group[columns].values.tolist()
    for key, data in shards.items():
        (shard_dir / f"{key}.json").write_text(json.dumps(data, separators=(",", ":")))

    meta = {
        "last_updated": loaded_at.strftime("%B %d, %Y"),
        "properties": len(properties),
        "owners": len(owners),
        "violations": len(violations),
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta))

    print(f"Wrote {len(properties):,} properties, {len(owners):,} owners, "
          f"{len(violations):,} violations in {len(shards)} files to {OUT_DIR}")


if __name__ == "__main__":
    main()