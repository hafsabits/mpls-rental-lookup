-- One row per owner (matched by standardized name), summed across their properties.
CREATE OR REPLACE TABLE `{project}.{dataset}.owners` AS
WITH owner_parcels AS (
  -- Collapse to one row per owner + parcel so a parcel with several licenses
  -- doesn't count its violations more than once.
  SELECT
    owner_key,
    apn,
    ANY_VALUE(owner_name) AS owner_name,
    COUNT(*) AS licenses,
    SUM(IFNULL(units, 0)) AS units,
    MAX(violations_2yr) AS violations_2yr,
    MAX(violations_open) AS violations_open
  FROM `{project}.{dataset}.rental_properties`
  WHERE owner_key IS NOT NULL AND owner_key != ''
  GROUP BY owner_key, apn
)
SELECT
  owner_key,
  ANY_VALUE(owner_name) AS owner_name,
  COUNT(*) AS properties,
  SUM(licenses) AS licenses,
  SUM(units) AS units,
  SUM(violations_2yr) AS violations_2yr,
  SUM(violations_open) AS violations_open,
  ROUND(SAFE_DIVIDE(SUM(violations_2yr), NULLIF(SUM(units), 0)), 2) AS violations_2yr_per_unit
FROM owner_parcels
GROUP BY owner_key;