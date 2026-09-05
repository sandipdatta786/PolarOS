-- =====================================================================
--  PolarOS — verify.sql
--  Runs every view and asserts the expected answer. Any line printing
--  FAIL means the schema is wrong — do not proceed to Prompt 2.
--
--  Run:  sqlite3 sample.db < verify.sql
-- =====================================================================
.headers on
.mode box

SELECT '=== 1. v_stock — MAITRI diesel must be 650 L (re-based), not 700 ===' AS "";
SELECT * FROM v_stock ORDER BY station_id, category;

SELECT CASE WHEN (SELECT qty_on_hand FROM v_stock
                   WHERE station_id='MAITRI' AND category='diesel') = 650.0
            THEN 'PASS  re-base applied: 700 counted - 50 consumed after count'
            ELSE 'FAIL  expected 650.0, got ' ||
                 COALESCE((SELECT qty_on_hand FROM v_stock
                            WHERE station_id='MAITRI' AND category='diesel'),'NULL')
       END AS assertion_1;

SELECT CASE WHEN (SELECT last_counted_qty FROM v_stock
                   WHERE station_id='MAITRI' AND category='diesel') = 700.0
            THEN 'PASS  baseline is the physical count'
            ELSE 'FAIL  baseline not picked up' END AS assertion_2;


SELECT '' AS "";
SELECT '=== 2. v_crate_location — CR-0001 at MAITRI, hazardous ===' AS "";
SELECT crate_id, location, custodian, last_event, last_seen_ts, hazard, un_class
FROM v_crate_location;

SELECT CASE WHEN (SELECT location FROM v_crate_location WHERE crate_id='CR-0001') = 'MAITRI'
             AND (SELECT hazard   FROM v_crate_location WHERE crate_id='CR-0001') = 1
            THEN 'PASS  last custody event wins; hazard flag sticks'
            ELSE 'FAIL' END AS assertion_3;

-- The compliance finding the demo narrates: hazard declared AFTER packing.
SELECT '--- hazard declared late (audit finding) ---' AS "";
SELECT c.crate_id,
       (SELECT MIN(ts) FROM events WHERE type='CRATE_PACKED'    AND subject=c.crate_id) AS packed_ts,
       c.hazard_declared_ts,
       CAST(ROUND((julianday(c.hazard_declared_ts) -
              julianday((SELECT MIN(ts) FROM events WHERE type='CRATE_PACKED' AND subject=c.crate_id))
             ) * 24) AS INTEGER) AS hours_late
FROM v_crate_location c
WHERE c.hazard = 1
  AND c.hazard_declared_ts > (SELECT MIN(ts) FROM events WHERE type='CRATE_PACKED' AND subject=c.crate_id);


SELECT '' AS "";
SELECT '=== 3. v_roster — M-001 at MAITRI, M-002 still at GOA ===' AS "";
SELECT member_id, name, role, cohort, location, position_from, since_ts,
       clearances_cleared
FROM v_roster ORDER BY member_id;

SELECT CASE WHEN (SELECT location FROM v_roster WHERE member_id='M-001') = 'MAITRI'
             AND (SELECT location FROM v_roster WHERE member_id='M-002') = 'GOA'
             AND (SELECT position_from FROM v_roster WHERE member_id='M-002') = 'REGISTERED'
            THEN 'PASS  registered-but-unmoved member still on roster'
            ELSE 'FAIL' END AS assertion_4;


SELECT '' AS "";
SELECT '=== 4. v_open_parties — FP-01 open, FP-02 closed by its return ===' AS "";
SELECT party_id, station, members, destination, departed_ts, eta_ts, overdue_raised
FROM v_open_parties ORDER BY party_id;

SELECT CASE WHEN (SELECT COUNT(*) FROM v_open_parties) = 1
             AND (SELECT party_id FROM v_open_parties) = 'FP-01'
            THEN 'PASS  NOT EXISTS closes only the matching trip'
            ELSE 'FAIL' END AS assertion_5;


SELECT '' AS "";
SELECT '=== 5. append-only is enforced by the database, not by manners ===' AS "";
-- These two must both raise. Run them by hand and read the error:
--   UPDATE events SET payload='{}' WHERE event_id='GOA-000001';
--     Error: events is append-only: correct by appending a new event
--   DELETE FROM events WHERE event_id='GOA-000001';
--     Error: events is append-only: nothing is ever deleted
SELECT COUNT(*) AS total_events_in_log FROM events;
