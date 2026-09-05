-- =====================================================================
--  PolarOS — q_burnrate.sql          PROOF QUERY 1 of 3
--
--  "How long does what we have last, and does the ship get here first?"
--
--  Per station x category:
--      qty_on_hand            replayed from the log, as of :as_of
--      avg_daily_28d          trailing 28-day mean consumption
--      days_of_cover          qty_on_hand / avg_daily_28d
--      projected_zero_date    :as_of + days_of_cover
--      next_resupply          :resupply (parameter)
--      status                 RED  if projected_zero_date < next_resupply
--                             GREEN otherwise
--  RED rows first, soonest zero-date first.
--
--  RUN IT:
--      sqlite3 season.db < q_burnrate.sql
--
--      # or wind the clock to a different day:
--      sqlite3 season.db \
--        ".param set :as_of '2027-06-01T23:59:59Z'" \
--        ".read q_burnrate.sql"
--
--  PARAMETERS (both optional — the COALESCE below supplies defaults, so
--  the file runs standalone and still accepts overrides):
--      :as_of      the moment the forecast is made. Default is the
--                  demo's "today": 15 Sep 2027, the last HQ sync before
--                  the Maitri crossing.
--      :resupply   the date the next ship is expected. Default 15 Dec.
--
--  WHY :as_of EXISTS AT ALL — say this in Q&A, it is the strongest
--  point in the query. Because state is replayed rather than stored,
--  every view can be evaluated at any past instant simply by refusing
--  to look at events after that instant. This query cannot cheat: with
--  :as_of set to 15 September it is blind to the emergency airlift that
--  arrives on 3 October. That is a real property of an append-only log,
--  not a feature we wrote — and it means the forecast you see on the
--  screen is the forecast the duty officer would genuinely have had.
--
--  DATE ARITHMETIC — every piece of it, so you can defend it:
--    * ts is stored as fixed-width 'YYYY-MM-DDTHH:MM:SSZ'. Fixed width
--      means lexicographic string order IS chronological order, so
--      `ts <= as_of` is a valid time filter with no parsing at all.
--    * strftime('%Y-%m-%dT%H:%M:%SZ', X, '-28 days') gives the start of
--      the trailing window in exactly the same format, so it can be
--      compared to ts as a string too.
--    * The window is a FIXED 28 days, not "the last 28 events". Divide
--      total consumption in the window by 28 and you have litres/day
--      whether the station logged once a day or five times. Do not
--      change this to AVG(qty) — that would be the mean draw size, not
--      the mean daily burn, and it would be wrong by a factor of
--      however many draws happen per day.
--    * julianday(a) - julianday(b) is a difference in DAYS as a float.
--      That is the only subtraction SQLite does on dates.
--    * date(as_of, '+N days') does the calendar walk — leap years, month
--      lengths and all. We never add 30 to a day-of-month by hand.
--    * 28 days is chosen because it is exactly four weeks, so a station
--      that issues stores on Mondays contributes exactly four issues to
--      every window. A 30-day window would sometimes catch four Mondays
--      and sometimes five, and the "burn rate" would oscillate by 25%
--      for no physical reason.
-- =====================================================================

.headers on
.mode box

WITH
params AS (
    SELECT
        COALESCE(:as_of,    '2027-09-15T23:59:59Z') AS as_of,
        COALESCE(:resupply, '2027-12-15')           AS resupply
),
win AS (
    SELECT as_of, resupply,
           strftime('%Y-%m-%dT%H:%M:%SZ', as_of, '-28 days') AS win_start
    FROM params
),

-- ---------------------------------------------------------------------
-- Stock on hand at :as_of. This is v_stock's replay logic, with one
-- extra clause: `ts <= as_of`. With :as_of set past the end of the log
-- it returns exactly what v_stock returns — the runner asserts that.
-- ---------------------------------------------------------------------
stock_events AS (
    SELECT substr(e.subject, 1, instr(e.subject, ':') - 1) AS station_id,
           substr(e.subject, instr(e.subject, ':') + 1)    AS category,
           e.ts, e.type,
           CAST(json_extract(e.payload, '$.qty') AS REAL)  AS qty,
           json_extract(e.payload, '$.unit')               AS unit
    FROM events e, win w
    WHERE e.type IN ('STOCK_RECEIVED', 'STOCK_CONSUMED', 'STOCK_COUNTED')
      AND instr(e.subject, ':') > 0
      AND e.ts <= w.as_of
),
last_count AS (
    SELECT station_id, category, MAX(ts) AS base_ts
    FROM stock_events WHERE type = 'STOCK_COUNTED'
    GROUP BY station_id, category
),
baseline AS (
    SELECT lc.station_id, lc.category, lc.base_ts, MAX(se.qty) AS base_qty
    FROM last_count lc
    JOIN stock_events se ON se.station_id = lc.station_id
                        AND se.category   = lc.category
                        AND se.ts         = lc.base_ts
                        AND se.type       = 'STOCK_COUNTED'
    GROUP BY lc.station_id, lc.category, lc.base_ts
),
on_hand AS (
    SELECT se.station_id, se.category, MAX(se.unit) AS unit,
           ROUND(COALESCE(b.base_qty, 0)
               + COALESCE(SUM(CASE WHEN se.type = 'STOCK_RECEIVED'
                                    AND se.ts > COALESCE(b.base_ts, '')
                                   THEN se.qty END), 0)
               - COALESCE(SUM(CASE WHEN se.type = 'STOCK_CONSUMED'
                                    AND se.ts > COALESCE(b.base_ts, '')
                                   THEN se.qty END), 0), 2) AS qty_on_hand,
           b.base_ts AS last_counted_ts
    FROM stock_events se
    LEFT JOIN baseline b ON b.station_id = se.station_id
                        AND b.category   = se.category
    GROUP BY se.station_id, se.category, b.base_ts, b.base_qty
),

-- ---------------------------------------------------------------------
-- Trailing 28-day consumption. Divided by 28 — the length of the
-- window — not by the number of rows in it.
-- ---------------------------------------------------------------------
burn AS (
    SELECT substr(e.subject, 1, instr(e.subject, ':') - 1) AS station_id,
           substr(e.subject, instr(e.subject, ':') + 1)    AS category,
           ROUND(SUM(CAST(json_extract(e.payload, '$.qty') AS REAL)) / 28.0, 2)
               AS avg_daily_28d,
           COUNT(*) AS draws_in_window
    FROM events e, win w
    WHERE e.type = 'STOCK_CONSUMED'
      AND e.ts >  w.win_start
      AND e.ts <= w.as_of
    GROUP BY station_id, category
)

SELECT
    o.station_id                                        AS station,
    o.category,
    o.qty_on_hand,
    o.unit,
    COALESCE(b.avg_daily_28d, 0)                        AS avg_daily_28d,
    COALESCE(b.draws_in_window, 0)                      AS draws_28d,

    -- days of cover, and the calendar date that lands on
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN ROUND(o.qty_on_hand / b.avg_daily_28d, 1) END   AS days_of_cover,
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN date(w.as_of,
                   '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days')
    END                                                       AS projected_zero_date,

    date(w.resupply)                                    AS next_resupply,

    -- days of slack: negative means the stock runs out before the ship
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN CAST(julianday(w.resupply)
                 - julianday(date(w.as_of,
                       '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days'))
                  AS INTEGER) * -1
    END                                                 AS days_short_of_ship,

    CASE
        WHEN COALESCE(b.avg_daily_28d, 0) = 0 THEN 'NO DATA'
        WHEN date(w.as_of,
                  '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days')
             < date(w.resupply)               THEN 'RED'
        ELSE 'GREEN'
    END                                                 AS status,

    w.as_of                                             AS forecast_made_at
FROM on_hand o
CROSS JOIN win w
LEFT JOIN burn b ON b.station_id = o.station_id AND b.category = o.category
ORDER BY
    CASE
        WHEN COALESCE(b.avg_daily_28d, 0) = 0 THEN 2
        WHEN date(w.as_of,
                  '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days')
             < date(w.resupply)               THEN 0
        ELSE 1
    END,
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN date(w.as_of,
                   '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days')
         ELSE '9999-12-31' END,
    o.station_id, o.category;
