-- One row per rental license, with its parcel's violation history.
CREATE OR REPLACE TABLE `{project}.{dataset}.rental_properties` AS
WITH parcel_violations AS (
  SELECT
    apn,
    COUNT(*) AS violations_total,
    COUNTIF(processed_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 730 DAY)) AS violations_2yr,
    COUNTIF(is_open) AS violations_open,
    MAX(processed_date) AS last_violation_date
  FROM `{project}.{dataset}.violations_clean`
  GROUP BY apn
),
licenses AS (
  SELECT
    *,
    SAFE_CAST(licensed_units AS INT64) AS units,
    -- Standardized owner name: uppercase, no punctuation, single spaces ("L.L.C." -> "LLC")
    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(owner_name), r'[^A-Z0-9 ]', ''), r'\s+', ' ')) AS owner_key
  FROM `{project}.{dataset}.active_rental_licenses`
)
SELECT
  l.license_number,
  l.apn,
  l.address,
  UPPER(l.address) AS address_search,
  l.tier,
  l.status,
  l.units,
  l.issue_date,
  l.expiration_date,
  l.owner_name,
  l.owner_key,
  l.neighborhood_desc AS neighborhood,
  l.ward,
  l.latitude,
  l.longitude,
  IFNULL(v.violations_total, 0) AS violations_total,
  IFNULL(v.violations_2yr, 0) AS violations_2yr,
  IFNULL(v.violations_open, 0) AS violations_open,
  v.last_violation_date,
  -- Violations are per parcel, so divide by all units on the parcel, not just this license's.
  ROUND(SAFE_DIVIDE(IFNULL(v.violations_2yr, 0), SUM(l.units) OVER (PARTITION BY l.apn)), 2) AS violations_2yr_per_unit,
  l.loaded_at
FROM licenses l
LEFT JOIN parcel_violations v ON l.apn = v.apn;