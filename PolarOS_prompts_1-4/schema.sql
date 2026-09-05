-- =====================================================================
--  PolarOS — schema.sql
--  Smart India Hackathon 2026 · PS SIH26062 · NCPOR Antarctic logistics
--
--  ONE IDEA, HELD THROUGHOUT:
--    There is exactly one writable table in this system: `events`.
--    It is append-only. Nothing is ever UPDATEd or DELETEd.
--    Every question about "what is true right now" — how much diesel is
--    at Maitri, where crate CR-0142 is, who is on station, which field
--    party is still out — is answered by REPLAYING the log through a
--    VIEW. State is derived, never stored.
--
--  WHY THIS MATTERS FOR ANTARCTICA (the judging answer):
--    Nodes (GOA, VESSEL, MAITRI, BHARATI, SANDHI) are disconnected for
--    days or weeks. If two nodes both stored "current stock" and both
--    edited it, merging them would need a human to arbitrate. An
--    append-only log has no merge problem: syncing is set union. Two
--    nodes that have seen the same set of events compute the same state,
--    in any order of arrival. Corrections are new events (a STOCK_COUNTED
--    audit, a re-scan), never edits — so the record stays auditable, which
--    is what a government polar programme actually needs.
--
--  PORTABILITY:
--    Pure SQLite. No extensions, no loadable modules, no triggers-as-logic.
--    json_extract() is part of the SQLite core build since 3.38 (2022) and
--    is compiled into the sqlite3 CLI and Python's sqlite3 module by
--    default. Verify on any machine with:  SELECT json_valid('{}');
--    (returns 1). If a very old SQLite is all that is available, every
--    json_extract(payload,'$.x') can be replaced by a substr()/instr()
--    helper — but do not do that unless you have to; it hurts readability.
--
--  Run:  sqlite3 season.db < schema.sql
-- =====================================================================

-- NOTE ON journal_mode: WAL is the right mode for a station tablet — it
-- survives an ungraceful power cut, which happens at a polar station more
-- often than anywhere else you have worked. But WAL needs a shared-memory
-- file, and some filesystems cannot provide one: network shares, synced
-- folders (Dropbox, OneDrive, Google Drive) and some VM mounts will
-- accept the PRAGMA and then fail on the first real write with
-- "disk I/O error" that looks like database corruption but is not.
--
-- DELETE mode fails on those filesystems too, for a different reason:
-- it is named for the fact that it deletes the journal on every commit,
-- and several sandboxed and synced mounts forbid unlink while still
-- allowing writes. TRUNCATE zeroes the journal instead of unlinking it,
-- so it works where the other two do not, and is equally crash-safe.
--
-- generate_season.py therefore probes WAL, then TRUNCATE, then PERSIST,
-- committing a real row in each until one works. If you are running THIS
-- FILE by hand into a database on such a folder and hit an I/O error,
-- that is the cause: run  PRAGMA journal_mode = TRUNCATE;  first, or
-- move the database to a local disk.
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. THE LOG
-- ---------------------------------------------------------------------
--
--  event_id  Globally unique. Convention: node_id || '-' || zero-padded seq
--            (e.g. 'MAITRI-000412'). Deterministic, so the same event
--            generated twice is the same row — sync is idempotent.
--  node_id   Which node WROTE this event. Not where the thing is.
--  seq       Per-node monotonic counter starting at 1. UNIQUE(node_id,seq)
--            gives every node its own gap-free lane, so a sync can say
--            "send me everything from MAITRI after seq 3170" in one number.
--  ts        ISO-8601 UTC, 'YYYY-MM-DDTHH:MM:SSZ'. Fixed width, so
--            lexicographic string comparison IS chronological comparison.
--            This is why every view below can just use  ts > base_ts.
--  priority  1=safety 2=personnel 3=cargo 4=inventory 5=admin.
--            The sync layer drains priority 1 first: on a 15-minute
--            Iridium window, a man-overdue alert must not queue behind
--            400 rows of tinned-food consumption.
--  type      One of exactly 18 verbs. Enforced by CHECK, below.
--  subject   The entity this event is ABOUT. This is the join key for
--            every view, so the convention is strict:
--              crate events        -> crate_id      'CR-0142'
--              lot events          -> lot_id        'LOT-2'
--              member events       -> member_id     'M-017'
--              party events        -> party_id      'FP-03'
--              stock events        -> 'STATION:category'  'MAITRI:diesel'
--              SOP / ALERT         -> the subject of the thing it is about
--  payload   JSON object. Type-specific fields, documented in
--            PAYLOAD_CONTRACT below. Anything not needed by a view lives
--            here so the schema never has to change to carry a new field.

CREATE TABLE IF NOT EXISTS events (
    event_id  TEXT    PRIMARY KEY,
    node_id   TEXT    NOT NULL,
    seq       INTEGER NOT NULL,
    ts        TEXT    NOT NULL,
    priority  INTEGER NOT NULL,
    type      TEXT    NOT NULL,
    subject   TEXT    NOT NULL,
    payload   TEXT    NOT NULL DEFAULT '{}',

    UNIQUE (node_id, seq),

    CHECK (priority BETWEEN 1 AND 5),

    -- Fixed-width ISO-8601 UTC. Cheap, but it is what makes every
    -- string comparison in the views correct.
    CHECK (length(ts) = 20 AND ts LIKE '____-__-__T__:__:__Z'),

    CHECK (json_valid(payload)),

    -- The 18 verbs. Nothing else may ever enter the log.
    CHECK (type IN (
        -- cargo (priority 3)
        'MANIFEST_CREATED', 'CRATE_PACKED', 'CRATE_SCANNED',
        'CUSTODY_TRANSFERRED', 'HAZARD_DECLARED',
        'LOT_DISPATCHED', 'LOT_SAILED',
        -- personnel (priority 2)
        'MEMBER_REGISTERED', 'CLEARANCE_RECORDED', 'MEMBER_MOVED',
        'PARTY_DEPARTED', 'PARTY_RETURNED', 'PARTY_OVERDUE',
        -- inventory (priority 4)
        'STOCK_RECEIVED', 'STOCK_CONSUMED', 'STOCK_COUNTED',
        -- safety / admin
        'SOP_TRIGGERED', 'ALERT_RAISED'
    ))
);

-- ---------------------------------------------------------------------
-- 2. APPEND-ONLY, ENFORCED BY THE DATABASE
-- ---------------------------------------------------------------------
-- A convention that only lives in a comment is a convention that will be
-- broken at 2am the night before judging. These two triggers make the
-- claim true rather than aspirational: any UPDATE or DELETE against
-- `events` aborts the transaction. A correction is a NEW EVENT.

CREATE TRIGGER IF NOT EXISTS trg_events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events is append-only: correct by appending a new event');
END;

CREATE TRIGGER IF NOT EXISTS trg_events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events is append-only: nothing is ever deleted');
END;

-- ---------------------------------------------------------------------
-- 3. INDEXES
-- ---------------------------------------------------------------------
-- Every view below groups by `subject` and orders by `ts`, so that is the
-- index that matters. The (node_id, seq) index is implied by the UNIQUE
-- constraint and is what the sync layer uses.

CREATE INDEX IF NOT EXISTS ix_events_subject_ts ON events (subject, ts);
CREATE INDEX IF NOT EXISTS ix_events_type_ts    ON events (type, ts);
CREATE INDEX IF NOT EXISTS ix_events_ts         ON events (ts);

-- ---------------------------------------------------------------------
-- 4. PAYLOAD CONTRACT  (documentation table — data, not logic)
-- ---------------------------------------------------------------------
-- Kept as a table so `SELECT * FROM payload_contract;` is a live answer to
-- "what fields does this event carry?" during a judging Q&A, instead of
-- somebody scrolling a comment block.

CREATE TABLE IF NOT EXISTS payload_contract (
    type          TEXT PRIMARY KEY,
    subject_is    TEXT NOT NULL,
    priority      INTEGER NOT NULL,
    payload_keys  TEXT NOT NULL
);

INSERT OR REPLACE INTO payload_contract (type, subject_is, priority, payload_keys) VALUES
 ('MANIFEST_CREATED',   'lot_id',            5, 'lot_name, season, line_count, created_by'),
 ('CRATE_PACKED',       'crate_id',          3, 'lot_id, category, item, qty, unit, weight_kg, volume_m3, hazard, destination, needed_by, location'),
 ('CRATE_SCANNED',      'crate_id',          3, 'location, scanner, lot_id'),
 ('CUSTODY_TRANSFERRED','crate_id',          3, 'location, custodian_from, custodian_to, lot_id'),
 ('HAZARD_DECLARED',    'crate_id',          1, 'un_class, un_number, declared_by, note'),
 ('LOT_DISPATCHED',     'lot_id',            3, 'from_location, crate_count, gross_weight_kg'),
 ('LOT_SAILED',         'lot_id',            3, 'vessel, from_location, eta_station, eta_ts'),
 ('MEMBER_REGISTERED',  'member_id',         2, 'name, role, org, cohort, base'),
 ('CLEARANCE_RECORDED', 'member_id',         2, 'clearance, status, valid_until'),
 ('MEMBER_MOVED',       'member_id',         2, 'location, from_location, reason'),
 ('PARTY_DEPARTED',     'party_id',          2, 'station, members, destination, eta_ts, radio_schedule_min'),
 ('PARTY_RETURNED',     'party_id',          2, 'station, members, condition'),
 ('PARTY_OVERDUE',      'party_id',          1, 'station, eta_ts, overdue_min'),
 ('STOCK_RECEIVED',     'STATION:category',  4, 'qty, unit, source, crate_id'),
 ('STOCK_CONSUMED',     'STATION:category',  4, 'qty, unit, headcount, note'),
 ('STOCK_COUNTED',      'STATION:category',  4, 'qty, unit, counted_by, method'),
 ('SOP_TRIGGERED',      'entity it concerns',1, 'sop_id, sop_name, reason'),
 ('ALERT_RAISED',       'entity it concerns',1, 'severity, kind, message');

-- =====================================================================
-- 5. THE VIEWS — all state, computed by replay
-- =====================================================================

-- ---------------------------------------------------------------------
-- v_stock — how much of each category is on hand at each station
-- ---------------------------------------------------------------------
-- REPLAY LOGIC, in words:
--   1. Take every STOCK_* event and split its subject 'MAITRI:diesel'
--      into station and category.
--   2. Find, per (station, category), the timestamp of the most recent
--      STOCK_COUNTED. That is the AUDIT BASELINE: a physical count by a
--      human, which outranks every arithmetic guess before it.
--   3. On-hand = counted quantity
--                + everything RECEIVED strictly after the count
--                - everything CONSUMED strictly after the count.
--   4. If a (station, category) has never been counted, the baseline is
--      0 at time '' — and since every real ts sorts above '', the sum
--      runs over the entire history. Same expression, no special case.
--
-- WHY RE-BASE AT ALL? Because on a station you lose events. A tablet dies
-- mid-winter, someone burns fuel from a drum nobody logged. Rather than
-- letting error accumulate for nine months, the storekeeper does a
-- physical count, logs one STOCK_COUNTED, and the whole projection
-- snaps back to reality — without a single UPDATE. That is the point.
--
-- TIE-BREAK: movements bearing exactly the same ts as the count are
-- treated as already included in it (strict '>'). Physically true: you
-- count what is in the store at the moment you count it.

DROP VIEW IF EXISTS v_stock;
CREATE VIEW v_stock AS
WITH stock_events AS (
    SELECT
        substr(subject, 1, instr(subject, ':') - 1) AS station_id,
        substr(subject, instr(subject, ':') + 1)    AS category,
        ts,
        type,
        CAST(json_extract(payload, '$.qty') AS REAL) AS qty,
        json_extract(payload, '$.unit')              AS unit
    FROM events
    WHERE type IN ('STOCK_RECEIVED', 'STOCK_CONSUMED', 'STOCK_COUNTED')
      AND instr(subject, ':') > 0          -- guards a malformed subject
),
last_count AS (                            -- the audit baseline per pair
    SELECT station_id, category, MAX(ts) AS base_ts
    FROM stock_events
    WHERE type = 'STOCK_COUNTED'
    GROUP BY station_id, category
),
baseline AS (                              -- ...and the quantity counted then
    SELECT lc.station_id, lc.category, lc.base_ts,
           MAX(se.qty) AS base_qty         -- MAX() only to collapse a same-ts duplicate
    FROM last_count lc
    JOIN stock_events se
      ON se.station_id = lc.station_id
     AND se.category   = lc.category
     AND se.ts         = lc.base_ts
     AND se.type       = 'STOCK_COUNTED'
    GROUP BY lc.station_id, lc.category, lc.base_ts
)
SELECT
    se.station_id,
    se.category,
    MAX(se.unit)                                            AS unit,
    ROUND(
        COALESCE(b.base_qty, 0)
      + COALESCE(SUM(CASE WHEN se.type = 'STOCK_RECEIVED'
                           AND se.ts > COALESCE(b.base_ts, '')        -- see note
                          THEN se.qty END), 0)
      - COALESCE(SUM(CASE WHEN se.type = 'STOCK_CONSUMED'
                           AND se.ts > COALESCE(b.base_ts, '')
                          THEN se.qty END), 0)
    , 2)                                                    AS qty_on_hand,
    b.base_ts                                               AS last_counted_ts,
    b.base_qty                                              AS last_counted_qty,
    MAX(se.ts)                                              AS last_movement_ts,
    COUNT(*)                                                AS events_replayed
FROM stock_events se
LEFT JOIN baseline b
       ON b.station_id = se.station_id
      AND b.category   = se.category
GROUP BY se.station_id, se.category, b.base_ts, b.base_qty;
-- NOTE on the GROUP BY: base_ts and base_qty are carried in the GROUP BY
-- rather than wrapped in MAX(). `baseline` yields at most one row per
-- (station, category), so adding those two columns cannot split a group —
-- it just makes them plain grouped columns that the CASE expressions are
-- allowed to reference. (Wrapping them in MAX() inside a SUM(CASE ...)
-- would be a nested aggregate, which SQLite rejects.)
-- COALESCE(b.base_ts,'') is the never-counted case: the empty string
-- sorts below every real ISO timestamp, so the sums run over all history.

-- ---------------------------------------------------------------------
-- v_crate_location — where every crate was last seen, and in whose hands
-- ---------------------------------------------------------------------
-- REPLAY LOGIC:
--   Three event types move a crate through the world: CRATE_PACKED (it
--   comes into existence, at Goa), CRATE_SCANNED (a barcode read at a
--   node), CUSTODY_TRANSFERRED (a signed handover). For each crate_id we
--   keep the single latest such event and read its payload.location.
--
--   "Latest" = MAX(ts), tie-broken by event_id. The tie-break is not
--   cosmetic: two nodes can legitimately stamp the same second, and
--   without a deterministic second key, two synced replicas could show
--   different answers for the same log — which would break the core
--   claim. event_id is globally unique and stable, so every replica
--   picks the same winner. This is the whole "conflict resolution"
--   story: last-writer-wins on (ts, event_id), no human arbitration.

DROP VIEW IF EXISTS v_crate_location;
CREATE VIEW v_crate_location AS
WITH moves AS (
    SELECT
        subject                              AS crate_id,
        ts,
        event_id,
        node_id                              AS observed_by,
        type                                 AS last_event,
        json_extract(payload, '$.location')  AS location,
        COALESCE(json_extract(payload, '$.custodian_to'),
                 json_extract(payload, '$.scanner'))  AS custodian,
        json_extract(payload, '$.lot_id')    AS lot_id,
        ts || '|' || event_id                AS sort_key   -- deterministic ordering
    FROM events
    WHERE type IN ('CRATE_PACKED', 'CRATE_SCANNED', 'CUSTODY_TRANSFERRED')
),
latest AS (
    SELECT crate_id, MAX(sort_key) AS sort_key
    FROM moves
    GROUP BY crate_id
),
hazard AS (                                   -- a crate is hazardous from the
    SELECT subject AS crate_id,               -- moment it is declared, forever
           MIN(ts) AS declared_ts,
           json_extract(payload, '$.un_class') AS un_class
    FROM events
    WHERE type = 'HAZARD_DECLARED'
    GROUP BY subject
)
SELECT
    m.crate_id,
    m.location,
    m.custodian,
    m.lot_id,
    m.last_event,
    m.ts            AS last_seen_ts,
    m.observed_by,
    CASE WHEN h.crate_id IS NOT NULL THEN 1 ELSE 0 END AS hazard,
    h.un_class,
    h.declared_ts   AS hazard_declared_ts
FROM moves m
JOIN latest l ON l.crate_id = m.crate_id AND l.sort_key = m.sort_key
LEFT JOIN hazard h ON h.crate_id = m.crate_id;

-- ---------------------------------------------------------------------
-- v_roster — who is where, right now
-- ---------------------------------------------------------------------
-- REPLAY LOGIC:
--   A person's position history is MEMBER_REGISTERED (which establishes
--   them at their base, normally GOA) followed by a chain of
--   MEMBER_MOVED. We union those two into one stream of positions and
--   keep the latest per member — same (ts, event_id) tie-break as crates.
--
--   Registration is included deliberately: a member who has been
--   registered but not yet moved must still appear on the roster, at
--   Goa. A view that only read MEMBER_MOVED would make 35 people vanish
--   until their first flight, and the HQ headcount would be wrong on the
--   one day it matters most — mobilisation.
--
--   Identity fields (name, role) come from the registration event, which
--   is the one place they are stated.

DROP VIEW IF EXISTS v_roster;
CREATE VIEW v_roster AS
WITH positions AS (
    SELECT subject AS member_id, ts, event_id, 'REGISTERED' AS via,
           COALESCE(json_extract(payload, '$.base'), 'GOA') AS location
    FROM events WHERE type = 'MEMBER_REGISTERED'
    UNION ALL
    SELECT subject, ts, event_id, 'MOVED',
           json_extract(payload, '$.location')
    FROM events WHERE type = 'MEMBER_MOVED'
),
latest AS (
    SELECT member_id, MAX(ts || '|' || event_id) AS sort_key
    FROM positions GROUP BY member_id
),
identity AS (
    SELECT subject AS member_id,
           json_extract(payload, '$.name')   AS name,
           json_extract(payload, '$.role')   AS role,
           json_extract(payload, '$.org')    AS org,
           json_extract(payload, '$.cohort') AS cohort,
           ts                                AS registered_ts
    FROM events WHERE type = 'MEMBER_REGISTERED'
),
clearances AS (                               -- how many clearances are on file
    SELECT subject AS member_id,
           COUNT(*) AS clearances_recorded,
           SUM(CASE WHEN json_extract(payload, '$.status') = 'CLEARED'
                    THEN 1 ELSE 0 END) AS clearances_cleared
    FROM events WHERE type = 'CLEARANCE_RECORDED'
    GROUP BY subject
)
SELECT
    p.member_id,
    i.name,
    i.role,
    i.org,
    i.cohort,
    p.location,
    p.ts   AS since_ts,
    p.via  AS position_from,
    COALESCE(c.clearances_recorded, 0) AS clearances_recorded,
    COALESCE(c.clearances_cleared,  0) AS clearances_cleared,
    i.registered_ts
FROM positions p
JOIN latest l   ON l.member_id = p.member_id
               AND l.sort_key  = p.ts || '|' || p.event_id
LEFT JOIN identity   i ON i.member_id = p.member_id
LEFT JOIN clearances c ON c.member_id = p.member_id;

-- ---------------------------------------------------------------------
-- v_open_parties — field parties that have left and not come back
-- ---------------------------------------------------------------------
-- REPLAY LOGIC:
--   A PARTY_DEPARTED with no PARTY_RETURNED bearing the same party_id is
--   an open party. NOT EXISTS is the whole rule.
--
--   The `>= d.ts` guard matters: party ids are reused across a season
--   (FP-03 goes out in December and again in January). Requiring the
--   return to be at or after THIS departure means a stale return from
--   the previous trip cannot close the current one.
--
--   overdue_min is computed against the wall clock at query time
--   (julianday('now')), so the view is live. The proof query in
--   q_open_parties.sql parameterises "now" so a judge can wind the clock
--   back to the January incident and watch the same view go red.
--   Negative overdue_min = still within its ETA.

DROP VIEW IF EXISTS v_open_parties;
CREATE VIEW v_open_parties AS
WITH departures AS (
    SELECT
        subject                                        AS party_id,
        ts                                             AS departed_ts,
        node_id                                        AS station,
        json_extract(payload, '$.members')             AS members,
        json_extract(payload, '$.destination')         AS destination,
        json_extract(payload, '$.eta_ts')              AS eta_ts,
        json_extract(payload, '$.radio_schedule_min')  AS radio_schedule_min,
        event_id
    FROM events
    WHERE type = 'PARTY_DEPARTED'
)
SELECT
    d.party_id,
    d.station,
    d.members,
    d.destination,
    d.departed_ts,
    d.eta_ts,
    d.radio_schedule_min,
    -- minutes past ETA as of right now; negative means not yet due back
    CAST(ROUND((julianday('now') - julianday(d.eta_ts)) * 1440.0) AS INTEGER)
        AS overdue_min,
    -- has an operator already been told? (PARTY_OVERDUE raised for this trip)
    EXISTS (SELECT 1 FROM events o
             WHERE o.type = 'PARTY_OVERDUE'
               AND o.subject = d.party_id
               AND o.ts >= d.departed_ts)          AS overdue_raised
FROM departures d
WHERE NOT EXISTS (
    SELECT 1 FROM events r
     WHERE r.type    = 'PARTY_RETURNED'
       AND r.subject = d.party_id
       AND r.ts     >= d.departed_ts               -- closes THIS trip only
);

-- =====================================================================
--  End of schema. Four views, one table, zero stored state.
-- =====================================================================
