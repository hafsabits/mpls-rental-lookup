-- Rental-relevant violations, grouped into categories a renter understands.
CREATE OR REPLACE TABLE `{project}.{dataset}.violations_clean` AS
SELECT
  apn,
  display,
  violation_case_number,
  case_group_desc,
  CASE
    WHEN case_group_desc IN ('HIS Rental Inspection', 'HIS Inspection') THEN 'Inside the home'
    WHEN case_group_desc LIKE 'FIS%' THEN 'Fire safety'
    WHEN case_group_desc = 'Nuisance' THEN 'Outside the property'
    WHEN case_group_desc = 'Residential Vacant Building Registration' THEN 'Vacant or boarded'
    ELSE 'Other enforcement'
  END AS category,
  violation_code_description AS description,
  status_violation AS status,
  processed_date,
  resolved_date,
  resolved_date IS NULL AS is_open
FROM `{project}.{dataset}.code_violations`
WHERE case_group_desc NOT IN ('FIS Commercial Inspection', 'Commercial Vacant Building Registration')
  AND apn IS NOT NULL;