/**
 * PolarOS API — Burnrate Query Endpoint
 *
 * Simple Node.js/Express endpoint that queries season.db
 * and returns burnrate data for the Inventory Forecast module
 *
 * Usage:
 *   POST /api/burnrate
 *   { "as_of": "2027-09-15T23:59:59Z", "resupply": "2027-12-15" }
 *
 * Returns:
 *   Array of stock forecast rows with status (RED/GREEN/NO DATA)
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Query: copy-pasted from q_burnrate.sql, parameterized
const BURNRATE_QUERY = `
WITH
params AS (
    SELECT
        COALESCE(?, '2027-09-15T23:59:59Z') AS as_of,
        COALESCE(?, '2027-12-15')           AS resupply
),
win AS (
    SELECT as_of, resupply,
           strftime('%Y-%m-%dT%H:%M:%SZ', as_of, '-28 days') AS win_start
    FROM params
),
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
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN ROUND(o.qty_on_hand / b.avg_daily_28d, 1) END   AS days_of_cover,
    CASE WHEN COALESCE(b.avg_daily_28d, 0) > 0
         THEN date(w.as_of,
                   '+' || CAST(o.qty_on_hand / b.avg_daily_28d AS INT) || ' days')
    END                                                       AS projected_zero_date,
    date(w.resupply)                                    AS next_resupply,
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
`;

/**
 * Handle POST /api/burnrate
 * Body: { as_of, resupply }
 * Returns: Array of forecast rows
 */
async function handleBurnrateQuery(req, res) {
  try {
    const { as_of, resupply } = req.body || {};

    // Path to season.db
    const dbPath = path.join(__dirname, '..', 'PolarOS_prompts_1-4', 'season.db');

    // Open database
    const db = new sqlite3.Database(dbPath, (err) => {
      if (err) {
        console.error('Database open error:', err);
        return res.status(500).json({ error: 'Database connection failed' });
      }
    });

    // Run query with parameters
    db.all(BURNRATE_QUERY, [as_of, resupply], (err, rows) => {
      db.close();

      if (err) {
        console.error('Query error:', err);
        return res.status(500).json({ error: err.message });
      }

      // Convert to JSON-safe format
      const result = rows.map(row => ({
        ...row,
        qty_on_hand: parseFloat(row.qty_on_hand),
        avg_daily_28d: parseFloat(row.avg_daily_28d),
        days_of_cover: row.days_of_cover ? parseFloat(row.days_of_cover) : null
      }));

      res.json(result);
    });
  } catch (err) {
    console.error('Unexpected error:', err);
    res.status(500).json({ error: err.message });
  }
}

module.exports = handleBurnrateQuery;
