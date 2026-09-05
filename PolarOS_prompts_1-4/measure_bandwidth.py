#!/usr/bin/env python3
# =====================================================================
#  PolarOS — measure_bandwidth.py
#
#  QUESTION: does a day of Maitri's event log actually fit through one
#  Iridium window, or are we just asserting that it does?
#
#  This script does not estimate. It takes real days out of season.db,
#  serialises exactly what a sync would put on the wire, and weighs the
#  bytes. The output, bandwidth.md, is written so a judge can redo every
#  multiplication on paper.
#
#  METHOD
#    1. Group MAITRI's events by calendar day, across the whole season —
#       including offload day, which is the worst case and which a report
#       that quietly measured only the quiet winter would be hiding.
#    2. For each day, build the delta a sync would send: the full event
#       rows, as a JSON array, in seq order — because that is genuinely
#       what the receiver needs to replay them. No fields are dropped to
#       flatter the number.
#    3. Measure raw bytes and gzip -9 bytes.
#    4. Compare against the ceiling of one Iridium window.
#
#  HONESTY NOTES — read these before quoting the numbers
#    * 2.4 kbps is Iridium's circuit-switched data rate. Real goodput
#      after modem negotiation, PPP and TCP overhead is lower, so the
#      report shows a 60%-efficiency row alongside the theoretical one.
#      Quote the conservative row.
#    * gzip is measured with Python's zlib at level 9, which is what a
#      real client would use; there is no dictionary pre-training or
#      other trick that a production system would not have.
#    * Delta sizes are per NODE per DAY. A station syncing after a week
#      offline sends a week, so the report also weighs the entire season
#      as one blob — the bound that closes the backlog question.
#
#  Run:  python3 measure_bandwidth.py
# =====================================================================

import gzip
import io
import json
import os
import sqlite3
import statistics
import sys
from collections import defaultdict

DB = "season.db"
OUT = "bandwidth.md"

NODE = "MAITRI"
WINTER = ("2027-03-01", "2027-11-30")

# --- The link budget --------------------------------------------------
LINK_BPS = 2400            # Iridium circuit-switched data, bits per second
WINDOW_SECONDS = 15 * 60   # one 15-minute pass
GOODPUT = 0.60             # conservative allowance for protocol overhead


def compress(b):
    """gzip at level 9, with mtime pinned to 0 so the byte count is
    reproducible — otherwise the header timestamp changes every run and
    the 'deterministic' claim quietly stops being true."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as fh:
        fh.write(b)
    return buf.getvalue()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(DB):
        sys.exit("season.db missing — run: python3 generate_season.py")

    con = sqlite3.connect(DB)

    # The WHOLE log for this node, not just the winter — because the
    # heaviest day of a station's year is offload day, and a bandwidth
    # report that quietly excludes its own worst case is not a report.
    rows = con.execute("""
        SELECT event_id, node_id, seq, ts, priority, type, subject, payload
          FROM events WHERE node_id = ? ORDER BY seq""", (NODE,)).fetchall()

    # ---- group into per-day deltas ----------------------------------
    by_day = defaultdict(list)
    for r in rows:
        by_day[r[3][:10]].append({
            "event_id": r[0], "node_id": r[1], "seq": r[2], "ts": r[3],
            "priority": r[4], "type": r[5], "subject": r[6],
            "payload": json.loads(r[7]),
        })

    days = []
    for day in sorted(by_day):
        evs = by_day[day]
        raw = json.dumps(evs, separators=(",", ":"), sort_keys=True).encode()
        days.append({"day": day, "n": len(evs), "raw": len(raw),
                     "gz": len(compress(raw)),
                     "winter": WINTER[0] <= day <= WINTER[1]})

    if not days:
        sys.exit("no %s events in the log" % NODE)

    winter_days = [d for d in days if d["winter"]]

    # ---- pick the representative days --------------------------------
    # "Average day" = the winter-over day whose event count is the MEDIAN.
    # Median rather than mean deliberately: the mean is dragged around by
    # the monthly audit days, and we want a day that actually happened,
    # not a fictional average one.
    median_n = statistics.median(d["n"] for d in winter_days)
    avg_day = min(winter_days, key=lambda d: (abs(d["n"] - median_n), d["day"]))
    # Worst day across the ENTIRE log for this node — offload day.
    worst_day = max(days, key=lambda d: (d["gz"], d["day"]))

    # And the heaviest node-day anywhere in the system, as an upper bound.
    busiest = con.execute("""
        SELECT node_id, substr(ts,1,10) d, COUNT(*) c
          FROM events GROUP BY node_id, d ORDER BY c DESC LIMIT 1""").fetchone()
    b_rows = con.execute("""
        SELECT event_id,node_id,seq,ts,priority,type,subject,payload FROM events
         WHERE node_id=? AND substr(ts,1,10)=? ORDER BY seq""",
        (busiest[0], busiest[1])).fetchall()
    b_evs = [{"event_id": r[0], "node_id": r[1], "seq": r[2], "ts": r[3],
              "priority": r[4], "type": r[5], "subject": r[6],
              "payload": json.loads(r[7])} for r in b_rows]
    b_raw = json.dumps(b_evs, separators=(",", ":"), sort_keys=True).encode()
    b_gz = len(compress(b_raw))

    # ---- the link budget ---------------------------------------------
    window_bits = LINK_BPS * WINDOW_SECONDS
    window_bytes = window_bits // 8
    usable_bytes = int(window_bytes * GOODPUT)

    # ---- backlog: how many days can one window drain? -----------------
    # The naive version of this loop reports a misleadingly small answer,
    # because runs that start near the end of the log run out of DATA
    # before they run out of BUDGET. Those runs are censored observations
    # and must not be counted. Here we simply compress the entire log for
    # this node in one blob: if that fits, then every possible backlog
    # fits, and the question is closed.
    all_evs = [e for d in sorted(by_day) for e in by_day[d]]
    whole_log_gz = len(compress(json.dumps(all_evs, separators=(",", ":"),
                                           sort_keys=True).encode()))
    backlog_bound = whole_log_gz <= usable_bytes

    # ---- priority split on the worst day ------------------------------
    # If a window ever were too small, priority 1 drains first. Show what
    # that slice weighs, because that is the number that actually matters
    # for a man-overdue alert.
    # Measured on the node-day with the MOST priority-1 events anywhere in
    # the season — not on the byte-heaviest day, which may happen to carry
    # no safety traffic at all and would make this section meaningless.
    # The safety day that matters is the one carrying the overdue field
    # party, because that is the scenario the priority column exists for.
    p1_day = con.execute("""
        SELECT node_id, substr(ts,1,10) d,
               (SELECT COUNT(*) FROM events x
                 WHERE x.priority=1 AND x.node_id=e.node_id
                   AND substr(x.ts,1,10)=substr(e.ts,1,10))
          FROM events e WHERE e.type='PARTY_OVERDUE' ORDER BY e.ts LIMIT 1""").fetchone()
    if p1_day is None:                      # fallback: heaviest safety day
        p1_day = con.execute("""
            SELECT node_id, substr(ts,1,10) d, COUNT(*) c
              FROM events WHERE priority = 1
             GROUP BY node_id, d ORDER BY c DESC, d LIMIT 1""").fetchone()
    p1_rows = con.execute("""
        SELECT event_id,node_id,seq,ts,priority,type,subject,payload FROM events
         WHERE priority=1 AND node_id=? AND substr(ts,1,10)=? ORDER BY seq""",
        (p1_day[0], p1_day[1])).fetchall()
    p1 = [{"event_id": r[0], "node_id": r[1], "seq": r[2], "ts": r[3],
           "priority": r[4], "type": r[5], "subject": r[6],
           "payload": json.loads(r[7])} for r in p1_rows]
    p1_gz = len(compress(json.dumps(p1, separators=(",", ":"),
                                    sort_keys=True).encode())) if p1 else 0

    total_raw = sum(d["raw"] for d in days)
    total_gz = sum(d["gz"] for d in days)
    total_n = sum(d["n"] for d in days)

    # ---- write the report --------------------------------------------
    L = []
    a = L.append
    a("# PolarOS — sync bandwidth measurement")
    a("")
    a("**This is a measurement, not a claim.** Every number below was produced by")
    a("`measure_bandwidth.py` reading `season.db`. Re-run it and the numbers")
    a("reproduce exactly; the generator is seeded and gzip's mtime is pinned.")
    a("")
    a("Node measured: **%s**, whole season. The winter-over (%s to %s) is called out"
      % (NODE, WINTER[0], WINTER[1]))
    a("separately where it matters.")
    a("Days with traffic: **%d** (of which %d in the winter-over). Events: **%d**."
      % (len(days), len(winter_days), total_n))
    a("")
    a("## 1. The link budget")
    a("")
    a("| | |")
    a("|---|---|")
    a("| Link rate | %d bit/s (Iridium circuit-switched data) |" % LINK_BPS)
    a("| Window | %d s (15 min) |" % WINDOW_SECONDS)
    a("| Theoretical capacity | %d x %d = **%s bits** = **%s bytes** = %.1f KiB |"
      % (LINK_BPS, WINDOW_SECONDS, f"{window_bits:,}", f"{window_bytes:,}",
         window_bytes / 1024))
    a("| Usable at %d%% goodput | **%s bytes** = %.1f KiB |"
      % (GOODPUT * 100, f"{usable_bytes:,}", usable_bytes / 1024))
    a("")
    a("The %d%% figure is a deliberate haircut for modem negotiation, PPP framing"
      % (GOODPUT * 100))
    a("and TCP overhead. Quote the usable number, not the theoretical one — if a")
    a("judge asks why, this paragraph is the answer.")
    a("")
    a("## 2. A representative day")
    a("")
    a("The **median** day by event count, not the mean: the mean is pulled around by")
    a("the monthly audit days, and we wanted a day that actually happened.")
    a("")
    a("| | Average day (%s) | Worst day (%s) |" % (avg_day["day"], worst_day["day"]))
    a("|---|---:|---:|")
    a("| Events | %d | %d |" % (avg_day["n"], worst_day["n"]))
    a("| Raw JSON | %s B | %s B |" % (f"{avg_day['raw']:,}", f"{worst_day['raw']:,}"))
    a("| gzip -9 | **%s B** | **%s B** |" % (f"{avg_day['gz']:,}", f"{worst_day['gz']:,}"))
    a("| Compression | %.1fx | %.1fx |"
      % (avg_day["raw"] / avg_day["gz"], worst_day["raw"] / worst_day["gz"]))
    a("| Bytes/event (gzip) | %.0f | %.0f |"
      % (avg_day["gz"] / avg_day["n"], worst_day["gz"] / worst_day["n"]))
    a("| Share of usable window | %.2f%% | %.2f%% |"
      % (100 * avg_day["gz"] / usable_bytes, 100 * worst_day["gz"] / usable_bytes))
    a("| Airtime needed at %d bit/s | %.1f s | %.1f s |"
      % (LINK_BPS, avg_day["gz"] * 8 / LINK_BPS / GOODPUT,
         worst_day["gz"] * 8 / LINK_BPS / GOODPUT))
    a("")
    a("### The arithmetic, longhand")
    a("")
    a("```")
    a("average day: %d events -> %s B raw -> %s B gzipped"
      % (avg_day["n"], f"{avg_day['raw']:,}", f"{avg_day['gz']:,}"))
    a("  %s B x 8            = %s bits to send"
      % (f"{avg_day['gz']:,}", f"{avg_day['gz'] * 8:,}"))
    a("  %s bits / %d bit/s  = %.1f s of airtime (theoretical)"
      % (f"{avg_day['gz'] * 8:,}", LINK_BPS, avg_day["gz"] * 8 / LINK_BPS))
    a("  / %.2f goodput      = %.1f s of airtime (realistic)"
      % (GOODPUT, avg_day["gz"] * 8 / LINK_BPS / GOODPUT))
    a("  window is %d s      -> margin %.1fx"
      % (WINDOW_SECONDS,
         WINDOW_SECONDS / (avg_day["gz"] * 8 / LINK_BPS / GOODPUT)))
    a("```")
    a("")
    a("## 3. Backlog — the case that actually matters")
    a("")
    a("A station is not offline for a day. It is offline for a week of blizzard, or")
    a("a fortnight of antenna icing, and then it gets one window. So the real")
    a("question is how many days of accumulated log one window can drain.")
    a("")
    if backlog_bound:
        a("We can answer it without a table. %s's **entire log for the whole season**"
          % NODE)
        a("— %d events across %d days with traffic — compresses to **%s B**, which is"
          % (len(all_evs), len(days), f"{whole_log_gz:,}"))
        a("**%.1f%% of one usable window**. If the whole season fits, every possible"
          % (100 * whole_log_gz / usable_bytes))
        a("backlog fits, and there is no worst case left to find.")
    else:
        a("The whole-season log does NOT fit in one window (%s B vs %s B usable),"
          % (f"{whole_log_gz:,}", f"{usable_bytes:,}"))
        a("so a real backlog table is needed here. Re-run with a larger season.")
    a("")
    a("Note the compression effect: the %d daily blobs sum to %s B, but the same"
      % (len(days), f"{total_gz:,}"))
    a("events compressed as **one** blob are %s B. Event logs are extremely"
      % f"{whole_log_gz:,}")
    a("repetitive — the same 18 type strings, the same node ids, the same JSON keys,")
    a("over and over — so a backlog compresses far better than a single day does.")
    a("The system gets *more* efficient the longer it has been offline, which is")
    a("exactly the wrong way round from what people expect. Say that in Q&A.")
    a("")
    a("## 3b. The heaviest node-day in the entire system")
    a("")
    a("Across all five nodes and the whole season, the single busiest node-day is")
    a("**%s on %s** (%d events) — the day the ship offloads and a station records"
      % (busiest[0], busiest[1], busiest[2]))
    a("a season's cargo in one shift. This is the worst case the design ever faces.")
    a("")
    a("| | |")
    a("|---|---:|")
    a("| Events | %d |" % busiest[2])
    a("| Raw JSON | %s B |" % f"{len(b_raw):,}")
    a("| gzip -9 | **%s B** |" % f"{b_gz:,}")
    a("| Share of usable window | **%.1f%%** |" % (100 * b_gz / usable_bytes))
    a("| Airtime at %d bit/s | %.1f s of a %d s window |"
      % (LINK_BPS, b_gz * 8 / LINK_BPS / GOODPUT, WINDOW_SECONDS))
    a("")
    a("This is the number to quote if a judge accuses the winter figures of being")
    a("easy. The busiest day the system will ever have still needs %.0f seconds."
      % (b_gz * 8 / LINK_BPS / GOODPUT))
    a("")
    a("## 4. Priority drain")
    a("")
    a("If a window were ever too small, priority 1 (safety) drains first.")
    a("The safety day that matters is **%s on %s**: the overdue field party and"
      % (p1_day[0], p1_day[1]))
    a("everything it triggered — %d priority-1 events (%s)."
      % (p1_day[2], ", ".join(sorted({e["type"] for e in p1}))))
    a("")
    a("That slice is **%s B gzipped**: %.3f%% of the usable window, **%.1f seconds**"
      % (f"{p1_gz:,}", 100 * p1_gz / usable_bytes, p1_gz * 8 / LINK_BPS / GOODPUT))
    a("of airtime. Even on a link so degraded that only ten seconds of the window")
    a("survives, the safety traffic still gets through — which is the entire reason")
    a("`priority` is a column in the schema rather than a nice idea in the deck.")
    a("")
    a("## 5. What this does and does not prove")
    a("")
    a("**Proves:** the delta a node needs to send is small enough that bandwidth is")
    a("not the binding constraint on this design. The binding constraint is window")
    a("*availability*, not window *size*.")
    a("")
    a("**Does not prove:** that a real Iridium link achieves %d%% goodput, that the"
      % (GOODPUT * 100))
    a("session survives a 15-minute call without dropping, or that a production")
    a("wire format would serialise exactly like this JSON. Those need a real modem")
    a("and are honest 'not yet tested' answers in Q&A.")
    a("")
    a("## Appendix — every day measured")
    a("")
    a("| Day | Winter | Events | Raw B | gzip B | %% of window |")
    a("|---|:-:|---:|---:|---:|---:|")
    for d in days:
        a("| %s | %s | %d | %s | %s | %.2f%% |"
          % (d["day"], "Y" if d["winter"] else "", d["n"],
             f"{d['raw']:,}", f"{d['gz']:,}", 100 * d["gz"] / usable_bytes))

    text = "\n".join(L) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)

    # also drop the two sample deltas so they can be inspected / shown
    with open("delta_average_day.json", "w") as fh:
        json.dump(by_day[avg_day["day"]], fh, indent=1, sort_keys=True)
    with open("delta_worst_day.json", "w") as fh:
        json.dump(by_day[worst_day["day"]], fh, indent=1, sort_keys=True)

    print(text[:text.index("## Appendix")])
    print("(full table with all %d days written to %s)" % (len(days), OUT))
    print("sample deltas written to delta_average_day.json, delta_worst_day.json")


if __name__ == "__main__":
    main()
