# ADR 0001: python-for-data-pipeline
Status: Accepted
Date: Oct. 27th 2026

## Context
The project requires a reliable data ingestion pipeline to process bulk municipal datasets from the City of Minneapolis (including active rental licenses, code violations, and property data).

We needed to select a primary programming language and architecture strategy that enables efficient stream ingestion directly into a local database (PostgreSQL/PostGIS) without unnecessary local file storage clutter, while supporting heavy address cleansing and geospatial transformations.

## Options considered
1. **Python (Selected)**
   * **Pro:** Unmatched ecosystem for geospatial processing, data manipulation, and address standardization (`GeoPandas`, `Shapely`, stream-friendly via `io` and `requests`).
   * **Con:** Higher memory overhead for processing massive binary files compared to compiled low-level languages.

2. **TypeScript / Node.js**
   * **Pro:** Exceptional native support for asynchronous event-driven stream processing and uniform language stack if sharing with a web backend.
   * **Con:** Lacks the rich, mature out-of-the-box spatial analysis and data-cleaning libraries available in Python.

3. **Go (Golang)**
   * **Pro:** Blazing-fast performance, minimal memory footprint, and native handling of dense data streams and Protobuf (`PBF`) formats.
   * **Con:** Steeper implementation curve for complex spatial logic and fewer high-level developer utilities for data science/geospatial tasks.

## Decision
We will use **Python** for the data ingestion pipeline, utilizing stream-based downloading (`io.BytesIO` and chunked processing) to ingest municipal datasets directly into our local PostgreSQL/PostGIS database without persisting raw files to the local disk.

## Consequences
* **What this makes easier:** Writing clean address-matching logic, performing spatial queries, and tapping into a massive library ecosystem designed specifically for geographic and data engineering tasks.
* **What this makes harder or rules out:** Achieving absolute maximum throughput for dense binary parsing (which Go would handle more efficiently), though Python's performance is more than sufficient for municipal-scale datasets.