"""Load a pandas DataFrame into a BigQuery table."""

import pandas as pd
from google.cloud import bigquery


def load_dataframe(df: pd.DataFrame, project_id: str, dataset: str, table: str, location: str = "US") -> int:
    """Replace the table's contents with the DataFrame. Returns the row count in BigQuery."""
    client = bigquery.Client(project=project_id)

    dataset_ref = bigquery.Dataset(f"{project_id}.{dataset}")
    dataset_ref.location = location
    client.create_dataset(dataset_ref, exists_ok=True)  # safe to run every time

    table_id = f"{project_id}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # replace old rows, so re-runs never duplicate
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # wait for the load to finish

    row_count = client.get_table(table_id).num_rows
    print(f"Loaded {row_count:,} rows into {table_id}")
    return row_count