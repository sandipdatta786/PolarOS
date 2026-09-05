#!/usr/bin/env python3
# =====================================================================
#  PolarOS — check_gates.py
#
#  Every acceptance condition from the prompt pack, checked mechanically.
#  If this prints ALL GATES PASS, the artefacts are ready for the deck.
#  If it prints FAIL, do not update the deck — fix the code.
#
#  It also prints the FORECAST SWEEP: the same burn-rate query evaluated
#  at six different "todays" through the winter, showing the projected
#  zero-date tightening as more evidence arrives. That table is the
#  single most persuasive exhibit in the whole project — it demonstrates
#  a forecast improving, not a number asserted.
#
#  Run:  python3 check_gates.py
# =====================================================================

import os
import re
import sqlite3
import subprocess
import sys

DB = "season.db"
RESUPPLY = "2027-12-15"

EIGHTEEN = [
    "MANIFEST_CREATED", "CRATE_PACKED", "CRATE_SCANNED", "CUSTODY_TRANSFERRED",
    "HAZARD_DECLARED", "LOT_DISPATCHED", "LOT_SAILED", "MEMBER_REGISTERED",
    "CLEARANCE_RECORDED", "MEMBER_MOVED", "PARTY_DEPARTED", "PARTY_RETURNED",
    "PARTY_OVERDUE", "STOCK_RECEIVED", "STOCK_CONSUMED", "STOCK_COUNTED",
    "SOP_TRIGGERED", "ALERT_RAISED",
]

results = []


def gate(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def statements(path):
    """Read a .sql file and return its executable statements.

    Strips sqlite3 CLI dot-commands and whole-line `--` comments BEFORE
    splitting on ';'. That order matters: the header comments in these
    files contain semicolons in ordinary English sentences, and splitting
    first would silently truncate the query to nothing — which is exactly
    the bug this function was written to fix."""
    body = "\n".join(l for l in open(path).read().splitlines()
                     if not l.startswith(".") and not l.lstrip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def run(con, path, n=0, **params):
    """Execute statement n of a .sql file with named parameters bound,
    returning a list of dicts."""
    cur = con.execute(statements(path)[n], params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def burnrate(con, as_of, resupply=RESUPPLY):
    return run(con, "q_burnrate.sql", 0, as_of=as_of, resupply=resupply)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(DB):
        sys.exit("season.db missing — run: python3 generate_season.py")

    con = sqlite3.connect(DB)
    q = lambda s, p=(): con.execute(s, p).fetchall()

    print("\nPROMPT 1 — schema")
    print("-" * 70)
    for v in ("v_stock", "v_crate_location", "v_roster"):
        n = q("SELECT COUNT(*) FROM %s" % v)[0][0]
        gate("view %s returns rows" % v, n > 0, "%d rows" % n)
    # v_open_parties is live ("who is out RIGHT NOW"), and at the end of
    # the log in late November nobody is out — an empty result is the
    # CORRECT answer, not a broken view. It is exercised properly by
    # q_open_parties.sql with :as_of wound back to the January incident.
    n = q("SELECT COUNT(*) FROM v_open_parties")[0][0]
    gate("view v_open_parties evaluates (empty at end of log is correct)",
         n == 0, "%d open at end of season" % n)

    # append-only, enforced
    for stmt, label in (("UPDATE events SET priority=1 WHERE rowid=1", "UPDATE"),
                        ("DELETE FROM events WHERE rowid=1", "DELETE")):
        try:
            con.execute(stmt)
            con.rollback()
            gate("%s on events is rejected" % label, False, "it was allowed!")
        except sqlite3.IntegrityError as e:
            gate("%s on events is rejected" % label, True, str(e)[:44])
        except sqlite3.Error as e:
            gate("%s on events is rejected" % label, "append-only" in str(e),
                 str(e)[:44])

    # no negative stock anywhere
    neg = q("SELECT station_id, category, qty_on_hand FROM v_stock WHERE qty_on_hand < 0")
    gate("no negative on-hand quantity in v_stock", not neg, str(neg[:2]))

    print("\nPROMPT 2 — season generator")
    print("-" * 70)
    total = q("SELECT COUNT(*) FROM events")[0][0]
    gate("4000 <= total events <= 8000", 4000 <= total <= 8000, "%d events" % total)

    types = {t for (t,) in q("SELECT DISTINCT type FROM events")}
    missing = [t for t in EIGHTEEN if t not in types]
    gate("all 18 event types present", not missing, "missing: %s" % missing)

    crates = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='CRATE_PACKED'")[0][0]
    gate("~400 manifest lines", 380 <= crates <= 420, "%d crates" % crates)

    per_crate = q("""SELECT MIN(c), MAX(c), AVG(c) FROM (
                       SELECT COUNT(*) c FROM events
                        WHERE type IN ('CRATE_SCANNED','CUSTODY_TRANSFERRED')
                        GROUP BY subject)""")[0]
    gate("every crate has 4-6 movement events",
         per_crate[0] >= 4 and per_crate[1] <= 6,
         "min %d max %d mean %.2f" % (per_crate[0], per_crate[1], per_crate[2]))

    mem = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='MEMBER_REGISTERED'")[0][0]
    gate("35 members registered", mem == 35, "%d" % mem)

    cl = q("""SELECT COUNT(*) FROM (SELECT subject FROM events
                WHERE type='CLEARANCE_RECORDED' GROUP BY subject
                HAVING COUNT(DISTINCT json_extract(payload,'$.clearance'))=3)""")[0][0]
    gate("every member has 3 clearances on file", cl == 35, "%d of 35" % cl)

    win = q("""SELECT location, COUNT(*) FROM v_roster
                WHERE location IN ('MAITRI','BHARATI') GROUP BY location
                ORDER BY location""")
    gate("winter complement 7 MAITRI / 5 BHARATI",
         dict(win) == {"BHARATI": 5, "MAITRI": 7}, str(dict(win)))

    haz = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='HAZARD_DECLARED'")[0][0]
    gate("hazard rate near 8%", 0.05 <= haz / crates <= 0.11,
         "%d of %d = %.1f%%" % (haz, crates, 100 * haz / crates))

    mix = dict(q("""SELECT json_extract(payload,'$.category'), COUNT(*)
                      FROM events WHERE type='CRATE_PACKED' GROUP BY 1"""))
    want = {"food": .35, "spares": .20, "scientific": .15, "medical": .05, "misc": .05}
    fuel = (mix.get("diesel", 0) + mix.get("jetfuel", 0)) / crates
    ok = abs(fuel - .20) < .01 and all(abs(mix.get(k, 0) / crates - v) < .01
                                       for k, v in want.items())
    gate("category mix matches the brief", ok,
         "fuel %.1f%% food %.1f%%" % (100 * fuel, 100 * mix["food"] / crates))

    print("\nPROMPT 2 — determinism")
    print("-" * 70)
    before = open("season_stats.txt", "rb").read()
    con.close()
    subprocess.run([sys.executable, "generate_season.py"],
                   stdout=subprocess.DEVNULL, check=True)
    after = open("season_stats.txt", "rb").read()
    gate("two runs produce identical season_stats.txt", before == after,
         "%d bytes" % len(after))
    con = sqlite3.connect(DB)
    q = lambda s, p=(): con.execute(s, p).fetchall()

    print("\nPROMPT 3 — proof queries")
    print("-" * 70)

    # (1) burn rate at the demo moment
    rows = burnrate(con, "2027-09-15T23:59:59Z")
    md = [r for r in rows if r["station"] == "MAITRI" and r["category"] == "diesel"][0]
    bd = [r for r in rows if r["station"] == "BHARATI" and r["category"] == "diesel"][0]
    gate("MAITRI diesel is RED", md["status"] == "RED", md["status"])
    gate("MAITRI zero-date is in early October 2027",
         bool(re.match(r"2027-(09-2[5-9]|10-0[1-9]|10-1[0-4])$",
                       md["projected_zero_date"] or "")),
         md["projected_zero_date"])
    gate("BHARATI diesel is GREEN", bd["status"] == "GREEN",
         "%s, zero %s" % (bd["status"], bd["projected_zero_date"]))
    gate("RED rows are ordered first", rows[0]["status"] == "RED",
         "first row: %s %s" % (rows[0]["station"], rows[0]["category"]))

    # the query, run past the end of the log, must equal v_stock exactly
    live = burnrate(con, "2099-01-01T00:00:00Z")
    vs = {(s, c): qty for s, c, qty in
          q("SELECT station_id, category, qty_on_hand FROM v_stock")}
    # Exact equality, not a tolerance: both round to 2dp, so any
    # difference at all would mean the two replays disagree.
    same = all(r["qty_on_hand"] == vs[(r["station"], r["category"])]
               for r in live)
    gate("q_burnrate with a future :as_of == v_stock", same,
         "%d station x category rows compared" % len(live))

    # (2) crate trace
    tr = q("""SELECT COUNT(*) FROM events WHERE subject='CR-0005'
               AND type IN ('CRATE_PACKED','CRATE_SCANNED','CUSTODY_TRANSFERRED')""")[0][0]
    gate("CR-0005 has a complete custody chain", tr >= 5, "%d movement events" % tr)
    late = q("""SELECT h.subject, CAST(ROUND((julianday(h.ts)-julianday(p.ts))*24) AS INT)
                  FROM events h JOIN events p
                    ON p.subject=h.subject AND p.type='CRATE_PACKED'
                 WHERE h.type='HAZARD_DECLARED'
                   AND julianday(h.ts)-julianday(p.ts) > 1.0""")
    gate("exactly one late dangerous-goods declaration", len(late) == 1,
         "%s, %dh late" % (late[0][0], late[0][1]) if late else "none")

    # (3) open parties
    mid = run(con, "q_open_parties.sql", 0, as_of="2027-01-25T21:00:00Z")
    after_ret = run(con, "q_open_parties.sql", 0, as_of="2027-01-26T06:00:00Z")
    gate("one open party at 25 Jan 21:00Z", len(mid) == 1,
         "%s, %d min overdue" % (mid[0]["party_id"], mid[0]["overdue_min"])
         if mid else "none")
    gate("that party is flagged OVERDUE with the alert already raised",
         bool(mid) and mid[0]["state"] == "OVERDUE" and mid[0]["overdue_raised"] == 1,
         mid[0]["state"] if mid else "")
    gate("no open parties six hours later", len(after_ret) == 0,
         "%d open" % len(after_ret))

    # -----------------------------------------------------------------
    print("\nFORECAST SWEEP — the same query, run on six different days")
    print("-" * 70)
    print("  %-14s %-12s %-10s %-9s %-7s" %
          ("forecast made", "projects zero", "on hand L", "L/day", "status"))
    for as_of in ("2027-03-29", "2027-05-01", "2027-06-01", "2027-07-01",
                  "2027-08-01", "2027-09-01", "2027-09-15"):
        r = [x for x in burnrate(con, as_of + "T23:59:59Z")
             if x["station"] == "MAITRI" and x["category"] == "diesel"][0]
        print("  %-14s %-12s %-10.0f %-9.1f %-7s" %
              (as_of, r["projected_zero_date"], r["qty_on_hand"],
               r["avg_daily_28d"], r["status"]))
    # --- the counterfactual, computed rather than asserted -------------
    # In the season as it happened the tank never empties, because the
    # airlift lands first. So "when would it have run dry?" has to be
    # worked out: take the balance the instant before the airlift, then
    # keep subtracting the real consumption and see where it crosses.
    AIRLIFT = "2027-10-03T13:00:00Z"
    rows = q("""SELECT ts, type, json_extract(payload,'$.qty')
                  FROM events WHERE subject='MAITRI:diesel'
                   AND type IN ('STOCK_RECEIVED','STOCK_CONSUMED','STOCK_COUNTED')
                 ORDER BY ts""")
    bal, dry = 0.0, None
    for ts, t, qty in rows:
        if ts >= AIRLIFT and t != 'STOCK_CONSUMED':
            continue                      # ignore the airlift and later re-bases
        bal = qty if t == 'STOCK_COUNTED' else bal + (qty if t == 'STOCK_RECEIVED' else -qty)
        if bal <= 0 and dry is None:
            dry = ts
    alert = q("""SELECT MIN(ts) FROM events
                  WHERE type='ALERT_RAISED' AND subject='MAITRI:diesel'
                    AND json_extract(payload,'$.kind')='BURN_RATE'""")[0][0]
    print("\n  In the season as it happened the tank never empties: the airlift")
    print("  lands %s. Replaying the same consumption WITHOUT that" % AIRLIFT[:10])
    print("  airlift, Maitri would have run dry on %s." % (dry or "-")[:10])
    print("  The system raised the alert on %s — %d days of warning."
          % (alert[:10],
             round((__import__("datetime").date.fromisoformat(dry[:10])
                    - __import__("datetime").date.fromisoformat(alert[:10])).days)))

    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    bad = [n for n, ok, _ in results if not ok]
    if bad:
        print("  %d GATE(S) FAILED: %s" % (len(bad), ", ".join(bad)))
        print("=" * 70)
        sys.exit(1)
    print("  ALL GATES PASS — %d checks" % len(results))
    print("=" * 70)


if __name__ == "__main__":
    main()
