-- =====================================================================
--  PolarOS — q_crate_trace.sql        PROOF QUERY 2 of 3
--
--  "Where has this crate been, and who had it?"
--
--  The full chronological custody chain for one crate: every packing,
--  scan, handover, hazard declaration and alert that names it, in order,
--  with the location and the person or station holding it at each step.
--
--  RUN IT:
--      sqlite3 season.db ".param set :crate_id 'CR-0005'" ".read q_crate_trace.sql"
--
--      # or just take the default crate baked in below:
--      sqlite3 season.db < q_crate_trace.sql
--
--  PARAMETER:
--      :crate_id   defaults to CR-0005, the crate with the deliberately
--                  late dangerous-goods declaration. Trace it and the
--                  compliance gap is visible in the chain itself:
--                  nine days between CRATE_PACKED and HAZARD_DECLARED,
--                  by which time the crate had left Goa.
--
--  DATE ARITHMETIC:
--      elapsed_h is julianday(this event) - julianday(the first event for
--      this crate), times 24. julianday() returns a float number of days;
--      that is the only date subtraction SQLite offers, and multiplying
--      by 24 is the whole conversion. No timezone maths is needed because
--      every ts in the log is already UTC by construction.
--
--  WHY THIS QUERY IS SHORT. A conventional design would need a crates
--  table, a movements table, a custody table and three joins, and would
--  still not be able to answer "what did we know on 3 November?" Here
--  the chain IS the data. There is nothing to reconstruct.
-- =====================================================================

.headers on
.mode box

WITH p AS (
    SELECT COALESCE(:crate_id, 'CR-0005') AS crate_id
),
chain AS (
    SELECT
        e.ts,
        e.type,
        e.node_id                                        AS recorded_by,
        e.priority,
        COALESCE(json_extract(e.payload, '$.location'),
                 json_extract(e.payload, '$.destination')) AS location,
        COALESCE(json_extract(e.payload, '$.custodian_to'),
                 json_extract(e.payload, '$.scanner'),
                 json_extract(e.payload, '$.declared_by'))  AS held_by,
        json_extract(e.payload, '$.category')            AS category,
        json_extract(e.payload, '$.qty')                 AS qty,
        json_extract(e.payload, '$.unit')                AS unit,
        json_extract(e.payload, '$.hazard')              AS hazard_flag,
        json_extract(e.payload, '$.un_number')           AS un_number,
        json_extract(e.payload, '$.note')                AS note,
        json_extract(e.payload, '$.message')             AS message,
        e.event_id
    FROM events e, p
    WHERE e.subject = p.crate_id
      AND e.type IN ('CRATE_PACKED', 'CRATE_SCANNED', 'CUSTODY_TRANSFERRED',
                     'HAZARD_DECLARED', 'ALERT_RAISED')
),
first_seen AS (
    SELECT MIN(ts) AS t0 FROM chain
)
SELECT
    ROW_NUMBER() OVER (ORDER BY c.ts, c.event_id)  AS step,
    c.ts,
    c.type,
    COALESCE(c.location, '-')                      AS location,
    COALESCE(c.held_by, '-')                       AS held_by,
    c.recorded_by,
    -- hours since this crate was packed
    CAST(ROUND((julianday(c.ts) - julianday(f.t0)) * 24.0) AS INTEGER) AS elapsed_h,
    COALESCE(c.un_number, '')                      AS un_number,
    COALESCE(c.note, c.message, '')                AS remark
FROM chain c, first_seen f
ORDER BY c.ts, c.event_id;

-- ---------------------------------------------------------------------
-- Where the crate is NOW (what v_crate_location says about it)
-- ---------------------------------------------------------------------
SELECT crate_id, location, custodian, last_event, last_seen_ts,
       hazard, un_class, hazard_declared_ts
FROM v_crate_location
WHERE crate_id = COALESCE(:crate_id, 'CR-0005');

-- ---------------------------------------------------------------------
-- The compliance test, run across the WHOLE season, not just this crate.
-- IMDG paperwork must travel with the crate, so a declaration filed the
-- same day it was packed is compliant. What is NOT compliant is a
-- declaration filed more than 24 hours later — by then the crate has
-- moved. That is the threshold below.
--
-- In the current paper process nobody can run this check at all: the
-- packing lists and the DG declarations live in different files, held by
-- different people, in different cities. Here it is one join.
-- ---------------------------------------------------------------------
SELECT
    h.subject                                          AS crate_id,
    pk.ts                                              AS packed_ts,
    h.ts                                               AS declared_ts,
    CAST(ROUND((julianday(h.ts) - julianday(pk.ts)) * 24.0) AS INTEGER) AS hours_late,
    json_extract(h.payload, '$.un_number')             AS un_number,
    json_extract(pk.payload, '$.destination')          AS destination
FROM events h
JOIN events pk ON pk.subject = h.subject AND pk.type = 'CRATE_PACKED'
WHERE h.type = 'HAZARD_DECLARED'
  AND julianday(h.ts) - julianday(pk.ts) > 1.0   -- more than 24h late
ORDER BY hours_late DESC;
