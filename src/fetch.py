"""Download every record from an ArcGIS FeatureServer layer."""

import time

import requests

PAGE_SIZE = 2000  # the most records this server returns per request


def _get(url: str, params: dict) -> dict:
    """Send one request and fail loudly on any error."""
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()  # stops on HTTP errors like 404 or 500
    data = response.json()
    if "error" in data:  # ArcGIS sometimes returns errors inside a 200 response
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data


def get_count(layer_url: str) -> int:
    """Ask the server how many records exist in total."""
    data = _get(
        f"{layer_url}/query",
        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
    )
    return data["count"]


def fetch_all(layer_url: str, order_by: str = "OBJECTID", pause_seconds: float = 0.5) -> list[dict]:
    """Return every record in the layer as a list of dictionaries."""
    expected = get_count(layer_url)
    print(f"Server reports {expected:,} records")

    records: list[dict] = []
    offset = 0
    while True:
        data = _get(
            f"{layer_url}/query",
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "false",  # latitude/longitude are already regular fields
                "orderByFields": order_by,  # stable order so pages don't overlap
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "f": "json",
            },
        )
        features = data.get("features", [])
        if not features:
            break

        records.extend(feature["attributes"] for feature in features)
        offset += len(features)
        print(f"  fetched {len(records):,} / {expected:,}")

        if not data.get("exceededTransferLimit"):  # no more pages
            break
        time.sleep(pause_seconds)  # be polite to the city's server

    if len(records) != expected:
        raise RuntimeError(f"Expected {expected:,} records but got {len(records):,}")
    return records