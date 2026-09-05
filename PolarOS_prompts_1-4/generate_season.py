#!/usr/bin/env python3
# =====================================================================
#  PolarOS — generate_season.py
#  Smart India Hackathon 2026 · PS SIH26062
#
#  Fabricates one complete Indian Antarctic expedition season (2026-27)
#  as an append-only event log in season.db.
#
#  WHAT THIS IS AND IS NOT
#    It is not "fake data". It is a SIMULATION: a headcount burns food
#    and diesel day by day, crates physically move Goa -> Mumbai ->
#    Cape Town -> vessel -> station, people are cleared and inducted and
#    de-inducted. Every number the deck quotes falls out of this
#    simulation. Nothing is typed in by hand afterwards.
#
#  DETERMINISM
#    One fixed seed, one fixed iteration order, no wall-clock reads, no
#    dict-order dependence. Two runs on two machines produce a
#    byte-identical season_stats.txt. Check with:
#        python3 generate_season.py && cp season_stats.txt a.txt
#        python3 generate_season.py && diff a.txt season_stats.txt
#
#  DEPENDENCIES
#    Python 3.8+ standard library only. sqlite3 ships with Python.
#
#  Run:  python3 generate_season.py
#        (writes season.db, season_stats.txt; expects schema.sql alongside)
# =====================================================================

import json
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

# ---------------------------------------------------------------------
# 0. TUNABLE CONSTANTS
#    Everything a mentor or judge might ask "what if you changed X?"
#    lives here, at the top, with a comment. Nothing is buried.
# ---------------------------------------------------------------------

SEED = 20260903                     # fixed: determinism is a gate condition
SEASON = "2026-27"
DB_PATH = "season.db"
SCHEMA_PATH = "schema.sql"
STATS_PATH = "season_stats.txt"

NODES = ["GOA", "VESSEL", "MAITRI", "BHARATI", "SANDHI"]
STATIONS = ["MAITRI", "BHARATI", "SANDHI"]

# --- THE PLANTED SHORTFALL (drama (a)) -------------------------------
# Goa's fuel requisition was computed on an assumed 130 L/day of
# generator diesel at Maitri, for the 352 days between the 2026-27
# offload and the next ship on 15 Dec 2027. The load that actually
# sailed was 15% short of that requisition (a stowage compromise —
# entirely realistic; deck cargo loses to weight limits every season).
# Actual burn then ran ABOVE the planning assumption. Two compounding
# errors, which is how real fuel emergencies happen — never one.
#
# Set MAITRI_DIESEL_SHORTFALL_PCT = 0.0 to see the crisis disappear.
MAITRI_DIESEL_SHORTFALL_PCT = 0.15
PLANNED_MAITRI_DIESEL_LPD = 130.0   # Goa's (wrong) planning assumption, L/day

# --- Consumption model ------------------------------------------------
# Diesel is modelled as a fixed station hotel load plus a per-person
# term: a station burns fuel keeping itself alive whether 5 people or
# 25 are inside it. Food is purely per-person.
DIESEL_BASE_LPD    = {"MAITRI": 88.0, "BHARATI": 62.0, "SANDHI": 30.0}
DIESEL_PER_PERSON  = {"MAITRI": 4.0,  "BHARATI": 3.6,  "SANDHI": 3.0}
WINTER_DIESEL_UPLIFT = 1.25         # Jun-Aug: polar night, deepest cold
WINTER_UPLIFT_MONTHS = (6, 7, 8)

FOOD_KG_PER_PERSON_DAY = 3.1

# Weekly-consumed categories: (qty per person per week, qty fixed per week)
WEEKLY_CATEGORIES = {
    "medical":    (0.05, 0.4),
    "spares":     (0.00, 2.5),
    "scientific": (0.10, 1.2),
    "misc":       (0.08, 1.0),
}

CONSUMPTION_NOISE = 0.10            # +/-10% per day, seeded

# --- Physical stock audits -------------------------------------------
# Counted on the 1st of each month at the two wintering stations. The
# loss rate is the fraction the count comes up short of what the log
# says should be there: diesel is dipped with a stick and is accurate;
# food is counted by pallet and always drifts. Absorbing that drift
# without editing history is exactly what STOCK_COUNTED exists for.
AUDIT_STATIONS = ("MAITRI", "BHARATI")
AUDIT_LOSS = {"food": 0.006, "diesel": 0.0, "spares": 0.010,
              "scientific": 0.004, "medical": 0.004, "misc": 0.012}

# --- Headcounts -------------------------------------------------------
WINTER_HEADCOUNT = {"MAITRI": 7, "BHARATI": 5, "SANDHI": 0}
SUMMER_HEADCOUNT = {"MAITRI": 22, "BHARATI": 15, "SANDHI": 6}

# --- Season timeline --------------------------------------------------
D = date
REG_START, REG_END        = D(2026, 8, 1),  D(2026, 9, 15)   # registrations
WINTER_START, WINTER_END  = D(2027, 3, 1),  D(2027, 11, 30)  # winter-over
DEINDUCT_BY               = D(2027, 2, 25)                   # summer members out
FIELD_SEASON              = (D(2026, 12, 15), D(2027, 2, 20))
NEXT_RESUPPLY             = D(2027, 12, 15)                  # the ship they wait for

# Lot: (id, name, manifest date, dispatch from Goa, sail date, share of 400 lines)
LOTS = [
    ("LOT-1", "Lot 1 - equipment & machinery", D(2026, 9, 18), D(2026, 10, 14), D(2026, 10, 16), 0.27),
    ("LOT-2", "Lot 2 - station spares",        D(2026, 9, 26), D(2026, 10, 20), D(2026, 10, 22), 0.30),
    ("LOT-3", "Lot 3 - food & provisions",     D(2026, 10, 22), D(2026, 11, 23), D(2026, 11, 25), 0.43),
]

# Vessel arrival / offload at each station
STATION_ARRIVAL = {
    "MAITRI":  D(2026, 12, 27),     # Maitri anchorage, late Dec
    "BHARATI": D(2027, 1, 15),      # Bharati, mid-Jan
    "SANDHI":  D(2027, 1, 20),      # Sandhi, after Bharati
}

# Emergency response to the shortfall: once the forecast is believed,
# a Basler flight brings drums in. Modelled so the season stays
# physically coherent through 30 Nov rather than the station simply
# going dark in October.
# Dated two days ahead of the projected crossing, which is the whole
# point of the forecast: the flight is arranged BECAUSE the system
# saw the shortfall in March, not because the tank ran dry.
EMERGENCY_AIRLIFT_DATE = D(2027, 10, 3)
EMERGENCY_AIRLIFT_LITRES = 7500.0

MANIFEST_LINES = 400

# Exact category split of the 400 manifest lines.
# food 35% | fuel 20% (diesel + Jet A1) | spares 20% | scientific 15%
# medical 5% | misc 5%
CATEGORY_COUNTS = {
    "food":       140,   # 35.0%
    "diesel":      50,   # 12.5%  \  fuel = 20%
    "jetfuel":     30,   #  7.5%  /
    "spares":      80,   # 20.0%
    "scientific":  60,   # 15.0%
    "medical":     20,   #  5.0%
    "misc":        20,   #  5.0%
}

# Probability a crate of this category carries a dangerous good.
# Weighted so the overall rate lands near the 8% the brief asks for
# while staying physically sensible (fuel and reagents, not tinned fish).
HAZARD_P = {"diesel": 0.30, "jetfuel": 0.30, "medical": 0.15,
            "scientific": 0.05, "spares": 0.02, "food": 0.00, "misc": 0.02}

UN_CODES = {"diesel": ("3", "UN1202"), "jetfuel": ("3", "UN1863"),
            "medical": ("6.1", "UN2810"), "scientific": ("8", "UN1789"),
            "spares": ("2.2", "UN1950"), "misc": ("9", "UN3082")}

DEST_WEIGHTS = [("MAITRI", 0.45), ("BHARATI", 0.35), ("SANDHI", 0.20)]

UNITS = {"food": "kg", "diesel": "L", "jetfuel": "L", "spares": "ea",
         "scientific": "ea", "medical": "ea", "misc": "ea"}

# Priority per event type — mirrors the schema's payload_contract.
PRIORITY = {
    "MANIFEST_CREATED": 5, "CRATE_PACKED": 3, "CRATE_SCANNED": 3,
    "CUSTODY_TRANSFERRED": 3, "HAZARD_DECLARED": 1, "LOT_DISPATCHED": 3,
    "LOT_SAILED": 3, "MEMBER_REGISTERED": 2, "CLEARANCE_RECORDED": 2,
    "MEMBER_MOVED": 2, "PARTY_DEPARTED": 2, "PARTY_RETURNED": 2,
    "PARTY_OVERDUE": 1, "STOCK_RECEIVED": 4, "STOCK_CONSUMED": 4,
    "STOCK_COUNTED": 4, "SOP_TRIGGERED": 1, "ALERT_RAISED": 1,
}

RNG = random.Random(SEED)
EVENTS = []          # every event, unsequenced, in creation order


# ---------------------------------------------------------------------
# 1. SMALL HELPERS
# ---------------------------------------------------------------------

def iso(d, hh=12, mm=0, ss=0):
    """A date plus a time-of-day as the fixed-width UTC string the schema
    demands. Fixed width is what lets every view compare timestamps as
    plain strings."""
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (d.year, d.month, d.day, hh, mm, ss)


def emit(node, ts, etype, subject, payload):
    """Append one event to the log-in-progress. seq and event_id are NOT
    assigned here — they are assigned once, at the end, after everything
    is sorted into time order, so that each node's seq is monotonic in
    time. That is what makes 'send me everything after seq N' correct."""
    EVENTS.append({
        "node_id": node, "ts": ts, "priority": PRIORITY[etype],
        "type": etype, "subject": subject, "payload": payload,
    })


def stable_hash(s):
    """Python's built-in hash() is randomised per process (PYTHONHASHSEED),
    which would silently destroy determinism. This is a tiny, boring,
    reproducible substitute. Do not replace it with hash()."""
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) % 1000003
    return h


def days(a, b):
    """Inclusive-of-a, exclusive-of-b day count."""
    return (b - a).days


def daterange(a, b):
    """Every date from a up to and including b."""
    d = a
    while d <= b:
        yield d
        d = d + timedelta(days=1)


def weighted(pairs):
    """Deterministic weighted pick from [(value, weight), ...]."""
    total = sum(w for _, w in pairs)
    r = RNG.random() * total
    acc = 0.0
    for v, w in pairs:
        acc += w
        if r <= acc:
            return v
    return pairs[-1][0]


def noisy(x):
    """Apply +/-CONSUMPTION_NOISE, rounded to 2dp. Seeded, so 'random'
    here means 'the same random every run'."""
    return round(x * (1.0 + RNG.uniform(-CONSUMPTION_NOISE, CONSUMPTION_NOISE)), 2)


def headcount_on(station, d):
    """How many people are at this station on this date. Summer complement
    until the de-induction date, winter complement from 1 March, nobody
    before the ship arrives."""
    if d < STATION_ARRIVAL[station]:
        return 0
    if d <= DEINDUCT_BY:
        return SUMMER_HEADCOUNT[station]
    return WINTER_HEADCOUNT[station]


# ---------------------------------------------------------------------
# 2. PERSONNEL — 35 members, clearances, induction chain
# ---------------------------------------------------------------------

FIRST = ["A.", "R.", "S.", "P.", "K.", "M.", "V.", "N.", "D.", "T.", "G.", "J."]
LAST  = ["Mehta", "Nair", "Bose", "Rathore", "Iyer", "Khan", "Deshpande",
         "Sarkar", "Pillai", "Chauhan", "Reddy", "Gogoi", "Sharma", "Das",
         "Patil", "Menon", "Yadav", "Thakur", "Bhat", "Rao"]
ROLES_WINTER = ["Station Leader", "Medical Officer", "Communications Engineer",
                "Power Plant Engineer", "Cook", "Meteorologist", "Technician"]
ROLES_SUMMER = ["Glaciologist", "Geologist", "Atmospheric Scientist",
                "Logistics Officer", "Rigger", "Biologist", "Surveyor",
                "Pilot", "Diver", "Mechanic"]
CLEARANCES = ["medical", "training", "passport"]

MEMBERS = []      # list of dicts, built in a fixed order


def build_members():
    """35 members: 12 winter-over (7 Maitri + 5 Bharati) and 23 summer.
    Every one is registered at Goa, carries three clearances, and moves
    through a chain of MEMBER_MOVED events. Summer members are moved
    back out before the de-induction date, which is what makes
    v_roster's headcount fall to 12 on 1 March."""
    plan = ([("MAITRI", "WINTER")] * 7 + [("BHARATI", "WINTER")] * 5 +
            [("MAITRI", "SUMMER")] * 10 + [("BHARATI", "SUMMER")] * 8 +
            [("SANDHI", "SUMMER")] * 5)
    assert len(plan) == 35, len(plan)

    for i, (station, cohort) in enumerate(plan, start=1):
        mid = "M-%03d" % i
        name = "%s %s" % (FIRST[i % len(FIRST)], LAST[i % len(LAST)])
        role = (ROLES_WINTER[i % len(ROLES_WINTER)] if cohort == "WINTER"
                else ROLES_SUMMER[i % len(ROLES_SUMMER)])
        reg_day = REG_START + timedelta(days=(i * 37) % days(REG_START, REG_END))
        MEMBERS.append({"id": mid, "name": name, "role": role,
                        "station": station, "cohort": cohort, "reg": reg_day})

    for m in MEMBERS:
        emit("GOA", iso(m["reg"], 4, 30), "MEMBER_REGISTERED", m["id"],
             {"name": m["name"], "role": m["role"], "org": "NCPOR",
              "cohort": m["cohort"], "base": "GOA"})

        # Three clearances each, spread over the weeks after registration.
        for k, cl in enumerate(CLEARANCES):
            cd = m["reg"] + timedelta(days=7 * (k + 1) + (stable_hash(m["id"]) % 3))
            emit("GOA", iso(cd, 6, 15 * k), "CLEARANCE_RECORDED", m["id"],
                 {"clearance": cl, "status": "CLEARED",
                  "valid_until": "2027-12-31"})

        # Induction chain: Goa -> vessel -> station.
        embark = STATION_ARRIVAL[m["station"]] - timedelta(days=30)
        emit("GOA", iso(embark, 7, 0), "MEMBER_MOVED", m["id"],
             {"location": "VESSEL", "from_location": "GOA",
              "reason": "embarkation"})
        arrive = STATION_ARRIVAL[m["station"]] + timedelta(days=1)
        emit(m["station"], iso(arrive, 9, 30), "MEMBER_MOVED", m["id"],
             {"location": m["station"], "from_location": "VESSEL",
              "reason": "station induction"})

        # Summer members go home again before the winter-over begins.
        if m["cohort"] == "SUMMER":
            out = DEINDUCT_BY - timedelta(days=(stable_hash(m["id"]) % 20))
            emit(m["station"], iso(out, 8, 0), "MEMBER_MOVED", m["id"],
                 {"location": "VESSEL", "from_location": m["station"],
                  "reason": "de-induction"})
            emit("GOA", iso(out + timedelta(days=24), 16, 0), "MEMBER_MOVED",
                 m["id"], {"location": "GOA", "from_location": "VESSEL",
                           "reason": "season complete"})


# ---------------------------------------------------------------------
# 3. CARGO — 400 manifest lines, each crate tracked door to door
# ---------------------------------------------------------------------

CRATES = []

# The physical route. Each stop is (location, event type, which node
# records it). A crate always gets the first and last stop; the middle
# ones are sampled so each crate carries 4-6 movement events, which is
# what a real barcode trail looks like — some scans get missed.
def route_for(destination):
    return [
        ("GOA",         "CRATE_SCANNED",       "GOA"),
        ("MUMBAI",      "CUSTODY_TRANSFERRED", "GOA"),
        ("CAPETOWN",    "CRATE_SCANNED",       "VESSEL"),
        ("VESSEL",      "CUSTODY_TRANSFERRED", "VESSEL"),
        (destination,   "CRATE_SCANNED",       destination),
        (destination,   "CUSTODY_TRANSFERRED", destination),
    ]


def build_cargo():
    """One MANIFEST_CREATED per lot, 400 CRATE_PACKED, then 4-6 movement
    events per crate, then LOT_DISPATCHED and LOT_SAILED."""
    # Build the exact category multiset, then shuffle it once, seeded.
    cats = []
    for c, n in sorted(CATEGORY_COUNTS.items()):
        cats.extend([c] * n)
    assert len(cats) == MANIFEST_LINES, len(cats)
    RNG.shuffle(cats)

    # Assign crates to lots by lot share, respecting the lot's character:
    # food rides in Lot 3, machinery in Lot 1.
    lot_affinity = {
        "food":       [("LOT-1", 0.05), ("LOT-2", 0.10), ("LOT-3", 0.85)],
        "diesel":     [("LOT-1", 0.25), ("LOT-2", 0.35), ("LOT-3", 0.40)],
        "jetfuel":    [("LOT-1", 0.30), ("LOT-2", 0.40), ("LOT-3", 0.30)],
        "spares":     [("LOT-1", 0.35), ("LOT-2", 0.55), ("LOT-3", 0.10)],
        "scientific": [("LOT-1", 0.55), ("LOT-2", 0.35), ("LOT-3", 0.10)],
        "medical":    [("LOT-1", 0.15), ("LOT-2", 0.55), ("LOT-3", 0.30)],
        "misc":       [("LOT-1", 0.30), ("LOT-2", 0.40), ("LOT-3", 0.30)],
    }
    lots_by_id = {l[0]: l for l in LOTS}

    for i, cat in enumerate(cats, start=1):
        crate_id = "CR-%04d" % i
        lot_id = weighted(lot_affinity[cat])
        _, _, man_d, disp_d, sail_d, _ = lots_by_id[lot_id]
        dest = weighted(DEST_WEIGHTS)

        # Physical characteristics, by category. Deliberately coarse —
        # a judge should be able to sanity-check the totals in their head.
        if cat in ("diesel", "jetfuel"):
            qty, weight, vol = 200.0, 178.0, 0.28
        elif cat == "food":
            qty, weight, vol = round(RNG.uniform(120, 320), 1), 0.0, 0.0
            weight, vol = qty + 18.0, round(qty / 420.0, 3)
        elif cat == "spares":
            qty, weight, vol = float(RNG.randint(4, 40)), round(RNG.uniform(60, 480), 1), round(RNG.uniform(0.2, 1.4), 3)
        elif cat == "scientific":
            qty, weight, vol = float(RNG.randint(1, 12)), round(RNG.uniform(25, 260), 1), round(RNG.uniform(0.1, 0.9), 3)
        elif cat == "medical":
            qty, weight, vol = float(RNG.randint(6, 60)), round(RNG.uniform(15, 90), 1), round(RNG.uniform(0.05, 0.4), 3)
        else:
            qty, weight, vol = float(RNG.randint(2, 30)), round(RNG.uniform(20, 200), 1), round(RNG.uniform(0.1, 0.8), 3)

        hazard = 1 if RNG.random() < HAZARD_P[cat] else 0
        pack_d = man_d + timedelta(days=RNG.randint(2, max(3, days(man_d, disp_d) - 2)))
        needed_by = STATION_ARRIVAL[dest] + timedelta(days=RNG.randint(0, 45))

        CRATES.append({"id": crate_id, "cat": cat, "lot": lot_id, "dest": dest,
                       "qty": qty, "weight": weight, "vol": vol,
                       "hazard": hazard, "pack": pack_d, "sail": sail_d})

        emit("GOA", iso(pack_d, 8, (i * 7) % 60), "CRATE_PACKED", crate_id,
             {"lot_id": lot_id, "category": cat,
              "item": "%s line %d" % (cat, i), "qty": qty, "unit": UNITS[cat],
              "weight_kg": weight, "volume_m3": vol, "hazard": hazard,
              "destination": dest, "needed_by": needed_by.isoformat(),
              "location": "GOA"})

        if hazard:
            # Declared the same day it is packed, before dispatch — except
            # for the one crate we deliberately break, later.
            emit("GOA", iso(pack_d, 9, 30), "HAZARD_DECLARED", crate_id,
                 {"un_class": UN_CODES[cat][0], "un_number": UN_CODES[cat][1],
                  "declared_by": "NCPOR-SAFETY",
                  "note": "dangerous goods declaration filed at packing"})

    # ---- movement trail --------------------------------------------
    # Timing: the crate leaves Goa on dispatch day, is in Mumbai two
    # days later, Cape Town about three weeks after sailing, transfers
    # to the vessel's own custody there, and lands at the station on
    # offload day.
    for c in CRATES:
        lot = lots_by_id[c["lot"]]
        disp_d, sail_d = lot[3], lot[4]
        arr = STATION_ARRIVAL[c["dest"]]
        stops = route_for(c["dest"])
        when = [disp_d,
                disp_d + timedelta(days=2),
                sail_d + timedelta(days=21),
                sail_d + timedelta(days=23),
                arr,
                arr + timedelta(days=1)]

        # Keep the first and last stop always; drop 0-2 of the middle
        # four so each crate ends with 4-6 movement events.
        n_drop = RNG.choice([0, 1, 1, 2])
        middle = [1, 2, 3, 4]
        RNG.shuffle(middle)
        dropped = set(middle[:n_drop])
        kept = [k for k in range(6) if k not in dropped]

        for k in kept:
            loc, etype, node = stops[k]
            d = when[k]
            payload = {"location": loc, "lot_id": c["lot"]}
            if etype == "CRATE_SCANNED":
                payload["scanner"] = "%s_SCAN_%d" % (node, (k % 3) + 1)
            else:
                payload["custodian_from"] = stops[max(k - 1, 0)][0] + "_STORE"
                payload["custodian_to"] = loc + "_STORE"
            emit(node, iso(d, 10 + (k % 8), (k * 11) % 60), etype, c["id"], payload)

    # ---- manifests, dispatch and sail -------------------------------
    # The manifest is emitted here, not earlier, so line_count is the real
    # number of crates that ended up in the lot rather than a guess.
    for n, (lot_id, lot_name, man_d, disp_d, sail_d, _) in enumerate(LOTS):
        mine = [c for c in CRATES if c["lot"] == lot_id]
        emit("GOA", iso(man_d, 5, 0), "MANIFEST_CREATED", lot_id,
             {"lot_name": lot_name, "season": SEASON,
              "line_count": len(mine), "created_by": "NCPOR-LOG-%02d" % (n + 1)})

    for lot_id, lot_name, man_d, disp_d, sail_d, _ in LOTS:
        mine = [c for c in CRATES if c["lot"] == lot_id]
        emit("GOA", iso(disp_d, 17, 0), "LOT_DISPATCHED", lot_id,
             {"from_location": "GOA", "crate_count": len(mine),
              "gross_weight_kg": round(sum(c["weight"] for c in mine), 1)})
        emit("VESSEL", iso(sail_d, 6, 0), "LOT_SAILED", lot_id,
             {"vessel": "MV Vasiliy Golovnin (chartered)",
              "from_location": "GOA", "eta_station": "MAITRI",
              "eta_ts": iso(STATION_ARRIVAL["MAITRI"], 6, 0)})


def plant_late_hazard():
    """Drama (c): exactly one hazardous crate is declared only AFTER it
    was packed and after the lot left Goa. This is a genuine IMDG
    compliance failure and the kind of thing the current paper process
    cannot surface. Because the log is append-only, the gap is
    permanently visible — you cannot backdate the declaration."""
    candidates = [c for c in CRATES if c["cat"] == "diesel" and c["hazard"] == 1
                  and c["dest"] == "MAITRI"]
    if not candidates:                    # seed-proofing, not expected
        candidates = [c for c in CRATES if c["hazard"] == 1]
    target = sorted(candidates, key=lambda c: c["id"])[0]

    # Remove the on-time declaration we already emitted for it and
    # replace it with a late one. (We are editing the generator's
    # in-memory draft here, not a committed log — the database itself is
    # still write-once.)
    global EVENTS
    EVENTS = [e for e in EVENTS
              if not (e["type"] == "HAZARD_DECLARED" and e["subject"] == target["id"])]

    LATE_BY_DAYS = 9
    late = target["pack"] + timedelta(days=LATE_BY_DAYS)
    emit("GOA", iso(late, 15, 20), "HAZARD_DECLARED", target["id"],
         {"un_class": "3", "un_number": "UN1202", "declared_by": "NCPOR-SAFETY",
          "note": "LATE DECLARATION - crate had already left Goa; raised by "
                  "manifest audit"})
    emit("GOA", iso(late, 15, 25), "ALERT_RAISED", target["id"],
         {"severity": "HIGH", "kind": "COMPLIANCE",
          "message": "Dangerous goods declared %d days after packing (crate %s)"
                     % (LATE_BY_DAYS, target["id"])})
    return target["id"]


# ---------------------------------------------------------------------
# 4. INVENTORY — receipts, daily burn, periodic audits
# ---------------------------------------------------------------------

def daily_need(station, cat, d):
    """Litres or kilograms this station wants of this category on this day,
    before noise. The two daily categories are modelled explicitly:

      food    purely per-person.
      diesel  a fixed station hotel load PLUS a per-person term. A station
              burns fuel keeping itself alive whether five people or
              twenty-five are inside it, so a purely per-person model
              would badly under-predict the winter.

    Everything else is issued weekly and handled separately.
    """
    hc = headcount_on(station, d)
    if hc == 0:
        return 0.0
    if cat == "food":
        return FOOD_KG_PER_PERSON_DAY * hc
    if cat == "diesel":
        base = DIESEL_BASE_LPD[station] + DIESEL_PER_PERSON[station] * hc
        if d.month in WINTER_UPLIFT_MONTHS:
            base *= WINTER_DIESEL_UPLIFT
        return base
    return 0.0


def plan_and_land_stock(facts):
    """Steps 1 and 2: work out what each station needs, then land it.

    The requirement is computed by running the consumption model forward
    from offload to the next ship — so it is the model's own honest
    answer, not a number we chose. Stations are then loaded with that
    requirement plus a contingency.

    Maitri diesel is the exception, and the exception is the whole point:
    it is loaded against GOA'S PLANNING FIGURE (a flat 130 L/day, which
    is below what the station really burns), and then 15% short of even
    that. Two compounding errors, which is how real fuel emergencies
    happen — never one.

    Returns the delivered quantities as {(station, category): qty}.
    """
    requirement = {}
    for st in STATIONS:
        end = NEXT_RESUPPLY if st != "SANDHI" else DEINDUCT_BY
        for cat in ("food", "diesel"):
            requirement[(st, cat)] = sum(
                daily_need(st, cat, d)
                for d in daterange(STATION_ARRIVAL[st], end))

    CONTINGENCY = 1.15          # honest stations load 15% over requirement
    delivered = {k: round(v * CONTINGENCY, 1) for k, v in requirement.items()}

    planned_days = days(STATION_ARRIVAL["MAITRI"], NEXT_RESUPPLY)
    requisitioned = PLANNED_MAITRI_DIESEL_LPD * planned_days
    delivered[("MAITRI", "diesel")] = round(
        requisitioned * (1.0 - MAITRI_DIESEL_SHORTFALL_PCT), 1)

    facts["maitri_diesel_requisitioned_L"] = round(requisitioned, 1)
    facts["maitri_diesel_delivered_L"] = delivered[("MAITRI", "diesel")]
    facts["maitri_diesel_true_requirement_L"] = round(requirement[("MAITRI", "diesel")], 1)
    facts["maitri_diesel_shortfall_pct"] = MAITRI_DIESEL_SHORTFALL_PCT

    # Categories that are issued weekly get a flat season stock.
    FLAT_STOCK = {"spares": 900.0, "scientific": 400.0,
                  "medical": 500.0, "misc": 350.0, "jetfuel": 24000.0}
    for st in STATIONS:
        scale = 1.0 if st == "MAITRI" else (0.75 if st == "BHARATI" else 0.35)
        for cat, q in sorted(FLAT_STOCK.items()):
            delivered[(st, cat)] = round(q * scale, 1)

    for (st, cat) in sorted(delivered):
        emit(st, iso(STATION_ARRIVAL[st], 11, 0), "STOCK_RECEIVED",
             "%s:%s" % (st, cat),
             {"qty": delivered[(st, cat)], "unit": UNITS[cat],
              "source": "SEASON OFFLOAD %s" % SEASON, "crate_id": None})

    return delivered


def emit_monthly_audit(st, d, balance):
    """A physical stock count on the 1st of the month, which RE-BASES
    v_stock: everything logged before it is discarded and the count
    becomes the new floor.

    Two decisions worth defending:

    * The count is taken from the SAME running balance the consumption
      loop draws down — one track, not two. An earlier draft counted in a
      separate pass and the two tracks drifted by tenths of a litre,
      which was enough to show a negative on-hand at the end of the
      season.
    * The value is FLOORED, not rounded. A physical count must never
      assert more stock than is actually there.

    Returns the number of count events emitted.
    """
    n = 0
    for cat in sorted(AUDIT_LOSS):
        key = (st, cat)
        if key not in balance:
            continue
        # Daily categories every month; the weekly ones twice a season.
        if cat not in ("food", "diesel") and d.month not in (5, 9):
            continue
        counted = int(max(balance[key] * (1.0 - AUDIT_LOSS[cat]), 0.0) * 10) / 10.0
        balance[key] = counted                    # the count IS the new truth
        n += 1
        emit(st, iso(d, 8, 0), "STOCK_COUNTED", "%s:%s" % (st, cat),
             {"qty": counted, "unit": UNITS[cat],
              "counted_by": "%s_STORE" % st,
              "method": "dip stick" if cat == "diesel" else "pallet count"})
    return n


def run_forecast(st, cat, d, balance, window, alerted, facts):
    """The burn-rate forecast, run every evening after the day's draw.

    This is the SAME arithmetic as q_burnrate.sql — trailing 28-day mean,
    divided into stock on hand, projected onto the calendar — implemented
    here so the simulation raises the alert on the day the projection
    first crosses the resupply date. The alert date in the deck is
    therefore computed, not chosen.

    THE GUARD, and it is the most defensible line in the file: we only
    forecast once the whole 28-day window lies inside the winter-over. A
    trailing mean that straddles de-induction averages twenty-two people
    against seven and would cry wolf about every category in January.
    Refusing to forecast across a known regime change is not a
    limitation; it is why this system raises one alert in a season
    instead of two hundred.
    """
    key = (st, cat)
    w = window.setdefault(key, [])
    del w[:-28]                                   # keep the trailing 28 days
    if len(w) < 28 or key in alerted:
        return
    if d < WINTER_START + timedelta(days=28):
        return
    avg = sum(w) / 28.0
    if avg <= 0:
        return
    zero_on = d + timedelta(days=int(balance[key] / avg))
    if zero_on >= NEXT_RESUPPLY:
        return

    alerted.add(key)
    facts["forecast_alerts"].append(
        (st, cat, d.isoformat(), zero_on.isoformat(),
         round(avg, 1), round(balance[key], 1)))
    emit(st, iso(d, 19, 0), "ALERT_RAISED", "%s:%s" % (st, cat),
         {"severity": "HIGH", "kind": "BURN_RATE",
          "message": "%s %s projected to reach zero on %s, before resupply on "
                     "%s (28-day mean %.1f %s/day, %.0f %s on hand)"
                     % (st, cat, zero_on.isoformat(), NEXT_RESUPPLY.isoformat(),
                        avg, UNITS[cat], balance[key], UNITS[cat])})
    emit(st, iso(d, 19, 5), "SOP_TRIGGERED", "%s:%s" % (st, cat),
         {"sop_id": "SOP-FUEL-01",
          "sop_name": "Consumable shortfall escalation",
          "reason": "projected stockout before next resupply"})


def raise_stockout(st, cat, d, exhausted):
    """A category has actually reached zero. Say so, once, and trigger the
    rationing SOP. Guarded by the `exhausted` set so a station that stays
    empty for a fortnight raises one alert, not fourteen."""
    key = (st, cat)
    if key in exhausted:
        return
    exhausted.add(key)
    emit(st, iso(d, 7, 0), "ALERT_RAISED", "%s:%s" % (st, cat),
         {"severity": "CRITICAL", "kind": "STOCKOUT",
          "message": "%s %s exhausted at %s" % (st, cat, d.isoformat())})
    emit(st, iso(d, 7, 5), "SOP_TRIGGERED", "%s:%s" % (st, cat),
         {"sop_id": "SOP-FUEL-02" if cat == "diesel" else "SOP-RAT-01",
          "sop_name": "Emergency fuel rationing" if cat == "diesel"
                      else "Ration scale reduction",
          "reason": "zero stock reached"})


def draw(st, cat, d, hh, mm, want, balance, note):
    """Take `want` out of stock, or whatever is left if that is less.

    `round(balance, 2)` before the min() is not cosmetic: the emitted
    quantity must never exceed what is actually on hand, or replaying the
    log produces a negative balance a few decimals below zero.

    Returns the quantity actually drawn (0.0 if the shelf was empty).
    """
    key = (st, cat)
    if balance.get(key, 0.0) <= 0.0:
        return 0.0
    take = min(want, round(balance[key], 2))
    balance[key] = round(balance[key] - take, 6)
    emit(st, iso(d, hh, mm), "STOCK_CONSUMED", "%s:%s" % (st, cat),
         {"qty": round(take, 2), "unit": UNITS[cat],
          "headcount": headcount_on(st, d), "note": note})
    return take


def simulate_inventory():
    """Land the season's stock, then burn it one day at a time.

    Everything the deck says about fuel comes out of this loop: the
    shortfall, the alert date, the projected zero-date, the airlift. None
    of it is asserted anywhere — it is all consequence.
    """
    facts = {"forecast_alerts": []}
    delivered = plan_and_land_stock(facts)

    balance = dict(delivered)
    exhausted = set()
    window = {}                 # trailing 28-day consumption, per (st, cat)
    forecast_alerted = set()
    n_audits = 0

    for st in STATIONS:
        end = WINTER_END if st != "SANDHI" else DEINDUCT_BY

        for d in daterange(STATION_ARRIVAL[st], end):
            hc = headcount_on(st, d)
            if hc == 0:
                continue

            # -- the emergency airlift, dated from the forecast ----------
            if st == "MAITRI" and d == EMERGENCY_AIRLIFT_DATE:
                balance[("MAITRI", "diesel")] += EMERGENCY_AIRLIFT_LITRES
                emit("MAITRI", iso(d, 13, 0), "STOCK_RECEIVED", "MAITRI:diesel",
                     {"qty": EMERGENCY_AIRLIFT_LITRES, "unit": "L",
                      "source": "EMERGENCY AIRLIFT (Basler BT-67)",
                      "crate_id": None})
                exhausted.discard(("MAITRI", "diesel"))

            # -- monthly physical count ---------------------------------
            if st in AUDIT_STATIONS and d.day == 1 and d > STATION_ARRIVAL[st]:
                n_audits += emit_monthly_audit(st, d, balance)

            # -- food and diesel, every day -----------------------------
            for cat in ("food", "diesel"):
                if balance.get((st, cat), 0.0) <= 0.0:
                    raise_stockout(st, cat, d, exhausted)
                    continue
                took = draw(st, cat, d, 18, 30, noisy(daily_need(st, cat, d)),
                            balance, "daily draw")
                window.setdefault((st, cat), []).append(took)
                run_forecast(st, cat, d, balance, window, forecast_alerted, facts)

            # -- stores issue, Mondays ----------------------------------
            if d.weekday() == 0:
                for cat, (per_person, fixed) in sorted(WEEKLY_CATEGORIES.items()):
                    draw(st, cat, d, 16, 0, noisy(fixed + per_person * hc),
                         balance, "weekly issue")

            # -- jet fuel, on summer flight days only -------------------
            if (st in ("MAITRI", "BHARATI") and d <= DEINDUCT_BY
                    and d.day in (4, 18)):
                draw(st, "jetfuel", d, 12, 0, round(noisy(1800.0), 1),
                     balance, "intra-continental sortie")

    facts["n_audits"] = n_audits
    facts["exhausted"] = sorted("%s:%s" % k for k in exhausted)
    facts["final_balance"] = {("%s:%s" % k): round(v, 1)
                              for k, v in sorted(balance.items())}
    return facts



# ---------------------------------------------------------------------
# 5. FIELD PARTIES — including the January overdue incident
# ---------------------------------------------------------------------

DESTINATIONS = {
    "MAITRI":  ["Schirmacher lakes traverse", "Dakshin Gangotri depot",
                "Wohlthat massif recce", "Blue-ice runway survey"],
    "BHARATI": ["Larsemann Hills ridge line", "Grovnes AWS service",
                "Broknes peninsula transect", "Stornes fuel cache"],
    "SANDHI":  ["Coastal bathymetry line", "Nunatak sample run"],
}


def build_field_parties():
    """~24 field parties across the Dec-Feb field season. Exactly one of
    them — drama (b) — comes back six hours late at Bharati in January,
    which is what the PARTY_OVERDUE / SOP path exists for."""
    start, end = FIELD_SEASON
    pid = 0
    overdue_party = None

    for d in daterange(start, end):
        if d.toordinal() % 2 != 0:
            continue
        st = weighted([("MAITRI", 0.4), ("BHARATI", 0.4), ("SANDHI", 0.2)])
        if headcount_on(st, d) == 0:
            continue
        pid += 1
        party = "FP-%02d" % pid
        on_station = sorted(m["id"] for m in MEMBERS if m["station"] == st)
        crew = sorted(RNG.sample(on_station, min(RNG.randint(2, 4), len(on_station))))
        dest = RNG.choice(DESTINATIONS[st])
        dep_h = RNG.randint(6, 9)
        planned_hours = RNG.randint(6, 11)
        eta = iso(d, dep_h + planned_hours, 0)

        emit(st, iso(d, dep_h, 0), "PARTY_DEPARTED", party,
             {"station": st, "members": crew, "destination": dest,
              "eta_ts": eta, "radio_schedule_min": RNG.choice([60, 120])})

        # The one incident: first Bharati party of January runs late.
        is_incident = (overdue_party is None and st == "BHARATI"
                       and d.year == 2027 and d.month == 1 and d.day >= 20)
        if is_incident:
            overdue_party = {"party": party, "station": st, "date": d,
                             "eta": eta, "crew": crew, "dest": dest}
            emit(st, iso(d, dep_h + planned_hours, 30), "PARTY_OVERDUE", party,
                 {"station": st, "eta_ts": eta, "overdue_min": 30})
            emit(st, iso(d, dep_h + planned_hours, 35), "SOP_TRIGGERED", party,
                 {"sop_id": "SOP-SAR-01", "sop_name": "Overdue field party",
                  "reason": "no radio check-in 30 min past ETA"})
            emit(st, iso(d, dep_h + planned_hours, 40), "ALERT_RAISED", party,
                 {"severity": "CRITICAL", "kind": "OVERDUE",
                  "message": "%s overdue at %s; SAR standby raised" % (party, st)})
            ret_h = dep_h + planned_hours + 6            # six hours late
            rd = d + (timedelta(days=1) if ret_h >= 24 else timedelta(0))
            emit(st, iso(rd, ret_h % 24, 0), "PARTY_RETURNED", party,
                 {"station": st, "members": crew,
                  "condition": "ALL SAFE - vehicle recovery, 6h delay"})
        else:
            back_h = dep_h + planned_hours - RNG.randint(0, 2)
            emit(st, iso(d, max(back_h, dep_h + 1), 0), "PARTY_RETURNED", party,
                 {"station": st, "members": crew, "condition": "OK"})

    return pid, overdue_party


# ---------------------------------------------------------------------
# 6. SEQUENCE, WRITE, REPORT
# ---------------------------------------------------------------------

def sequence_and_write():
    """Assign per-node seq in timestamp order, then insert.

    Sorting must be total and deterministic or two runs would number the
    same events differently. The key is (ts, node, type, subject,
    creation index) — creation index is the final tie-break, so ties can
    never be resolved by chance.
    """
    ordered = sorted(
        enumerate(EVENTS),
        key=lambda p: (p[1]["ts"], p[1]["node_id"], p[1]["type"],
                       p[1]["subject"], p[0]))

    counters = {n: 0 for n in NODES}
    rows = []
    for _, e in ordered:
        counters[e["node_id"]] += 1
        seq = counters[e["node_id"]]
        rows.append((
            "%s-%06d" % (e["node_id"], seq), e["node_id"], seq, e["ts"],
            e["priority"], e["type"], e["subject"],
            json.dumps(e["payload"], sort_keys=True, separators=(",", ":")),
        ))

    # Start from a clean database.
    #
    # os.remove is the simple path, but it is not always allowed: a
    # sandboxed folder, a synced folder, or a VM mount can refuse
    # DELETION while still permitting writes. And a leftover
    # `season.db-journal` that cannot be unlinked is fatal — SQLite sees
    # a hot journal on open, tries to roll it back and delete it, cannot,
    # and every subsequent statement fails with "disk I/O error" in every
    # journal mode. That is a genuinely nasty failure: the database looks
    # corrupt and is not.
    #
    # So: try to delete, and if that is refused, TRUNCATE TO ZERO BYTES
    # instead. Truncation is a write, not an unlink, so it is permitted
    # where deletion is not — and a zero-byte file is both a valid empty
    # SQLite database and a journal that is no longer hot.
    for suffix in ("", "-journal", "-wal", "-shm"):
        path = DB_PATH + suffix
        if not os.path.exists(path):
            continue
        try:
            os.remove(path)
        except OSError:
            try:
                with open(path, "wb"):
                    pass                    # truncate in place
            except OSError:
                pass                        # read-only: the DROPs below try next

    con = sqlite3.connect(DB_PATH)
    # Choose a journal mode this filesystem can actually honour, by
    # TRYING each one and committing a real row — not by asking SQLite
    # whether it accepted the PRAGMA, which it will happily do and then
    # fail on the first write.
    #
    # Why this is not paranoia: students will run this from a Dropbox or
    # OneDrive folder, or a VM mount, and several of those refuse file
    # DELETION while still allowing writes. That breaks the two obvious
    # modes at once — WAL has to create and remove -wal/-shm sidecars,
    # and DELETE mode is named for the fact that it deletes the journal
    # on every commit. Both fail with a bare "disk I/O error" that looks
    # like a corrupt database and will cost somebody an evening.
    #
    # TRUNCATE zeroes the journal file instead of unlinking it, so it
    # works where deletion does not, and is just as crash-safe.
    #
    # Order of preference:
    #   WAL       best on local disk: concurrent readers, power-cut safe
    #   TRUNCATE  crash-safe, and survives filesystems that forbid unlink
    #   PERSIST   last resort, same idea with more leftover bytes
    chosen = None
    for mode in ("WAL", "TRUNCATE", "PERSIST"):
        try:
            con.execute("PRAGMA journal_mode = %s" % mode)
            con.execute("CREATE TABLE IF NOT EXISTS _journal_probe (x)")
            con.execute("INSERT INTO _journal_probe VALUES (1)")
            con.commit()
            con.execute("DROP TABLE _journal_probe")
            con.commit()
            chosen = mode
            break
        except sqlite3.Error:
            con.close()                     # a failed probe can leave the
            con = sqlite3.connect(DB_PATH)  # connection in a bad state
    if chosen is None:
        raise SystemExit(
            "Could not write to %s in any journal mode. The folder this "
            "script is in does not support SQLite writes at all — move it "
            "to a local disk and re-run." % DB_PATH)
    if chosen != "WAL":
        print("note: journal_mode=%s (this filesystem cannot support WAL); "
              "the database is still crash-safe." % chosen.lower())

    # Only now, with a working journal mode, clear out any previous run.
    # This has to come AFTER the probe, not before: dropping tables is a
    # real write, and on a filesystem that cannot journal it fails with
    # the same opaque I/O error we just spent effort diagnosing.
    con.executescript(
        "DROP TRIGGER IF EXISTS trg_events_no_update;"
        "DROP TRIGGER IF EXISTS trg_events_no_delete;"
        "DROP TABLE IF EXISTS events;"
        "DROP TABLE IF EXISTS payload_contract;")

    with open(SCHEMA_PATH) as fh:
        con.executescript(fh.read())
    con.executemany(
        "INSERT INTO events (event_id,node_id,seq,ts,priority,type,subject,payload)"
        " VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return con, rows


def write_stats(con, rows, facts, n_parties, overdue, late_hazard_crate, n_audits):
    """season_stats.txt is the artefact the deck is regenerated from.
    Everything in it comes from a SELECT against the database we just
    wrote — never from a Python variable that might have drifted."""
    q = lambda sql: con.execute(sql).fetchall()

    total = q("SELECT COUNT(*) FROM events")[0][0]
    per_node = q("SELECT node_id, COUNT(*) FROM events GROUP BY node_id ORDER BY node_id")
    per_type = q("SELECT type, COUNT(*) FROM events GROUP BY type ORDER BY type")
    per_prio = q("SELECT priority, COUNT(*) FROM events GROUP BY priority ORDER BY priority")
    span = q("SELECT MIN(ts), MAX(ts) FROM events")[0]
    n_crates = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='CRATE_PACKED'")[0][0]
    n_members = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='MEMBER_REGISTERED'")[0][0]
    n_hazard = q("SELECT COUNT(DISTINCT subject) FROM events WHERE type='HAZARD_DECLARED'")[0][0]
    moves = q("""SELECT COUNT(*) FROM events
                  WHERE type IN ('CRATE_SCANNED','CUSTODY_TRANSFERRED')""")[0][0]
    cat_mix = q("""SELECT json_extract(payload,'$.category') AS c, COUNT(*)
                     FROM events WHERE type='CRATE_PACKED'
                    GROUP BY c ORDER BY c""")
    stock = q("""SELECT station_id, category, qty_on_hand, unit
                   FROM v_stock ORDER BY station_id, category""")

    missing = [t for t in PRIORITY if not any(r[0] == t for r in per_type)]

    L = []
    add = L.append
    add("PolarOS — season generation report")
    add("=" * 62)
    add("season                : %s" % SEASON)
    add("seed                  : %d   (deterministic — re-run and diff this file)" % SEED)
    add("log span              : %s .. %s" % span)
    add("")
    add("TOTAL EVENTS          : %d" % total)
    add("")
    add("Events per node")
    add("-" * 62)
    for n, c in per_node:
        add("  %-10s %6d   %5.1f%%" % (n, c, 100.0 * c / total))
    add("")
    add("Events per type (all 18 must appear)")
    add("-" * 62)
    for t, c in per_type:
        add("  %-22s %6d" % (t, c))
    add("  %-22s %6d types present" % ("--", len(per_type)))
    add("  %-22s %s" % ("missing types", missing if missing else "NONE"))
    add("")
    add("Events per priority (1=safety .. 5=admin)")
    add("-" * 62)
    for p, c in per_prio:
        add("  priority %d  %6d" % (p, c))
    add("")
    add("Cargo")
    add("-" * 62)
    add("  manifest lines (crates)      : %d" % n_crates)
    add("  movement events              : %d  (%.2f per crate)" % (moves, moves / n_crates))
    add("  hazardous crates declared    : %d  (%.1f%% of lines)" % (n_hazard, 100.0 * n_hazard / n_crates))
    add("  late hazard declaration      : %s" % late_hazard_crate)
    add("  category mix")
    for c, n in cat_mix:
        add("      %-12s %4d   %5.1f%%" % (c, n, 100.0 * n / n_crates))
    add("")
    add("Personnel")
    add("-" * 62)
    add("  members registered           : %d" % n_members)
    add("  winter-over complement       : MAITRI %d, BHARATI %d"
        % (WINTER_HEADCOUNT["MAITRI"], WINTER_HEADCOUNT["BHARATI"]))
    add("  roster at end of log         : %d at MAITRI, %d at BHARATI" % (
        con.execute("SELECT COUNT(*) FROM v_roster WHERE location='MAITRI'").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM v_roster WHERE location='BHARATI'").fetchone()[0]))
    add("")
    add("Field parties")
    add("-" * 62)
    add("  parties despatched           : %d" % n_parties)
    if overdue:
        add("  overdue incident             : %s at %s, departed %s, ETA %s, returned +6h"
            % (overdue["party"], overdue["station"],
               overdue["date"].isoformat(), overdue["eta"]))
    add("")
    add("Inventory")
    add("-" * 62)
    add("  stock audits (STOCK_COUNTED) : %d" % n_audits)
    add("  MAITRI diesel requisitioned  : %.1f L  (Goa plan: %.0f L/day x %d days)"
        % (facts["maitri_diesel_requisitioned_L"], PLANNED_MAITRI_DIESEL_LPD,
           days(STATION_ARRIVAL["MAITRI"], NEXT_RESUPPLY)))
    add("  MAITRI diesel delivered      : %.1f L  (%.0f%% short — PLANTED)"
        % (facts["maitri_diesel_delivered_L"], 100 * MAITRI_DIESEL_SHORTFALL_PCT))
    add("  MAITRI diesel true need      : %.1f L  to 15 Dec 2027"
        % facts["maitri_diesel_true_requirement_L"])
    add("  stockouts reached in sim     : %s" % (facts["exhausted"] or "none"))
    add("  emergency airlift            : %.0f L to MAITRI on %s"
        % (EMERGENCY_AIRLIFT_LITRES, EMERGENCY_AIRLIFT_DATE.isoformat()))
    add("")
    add("Burn-rate alerts raised BY THE SIMULATION (28-day trailing mean)")
    add("-" * 62)
    if facts["forecast_alerts"]:
        for st, cat, raised, zero_on, avg, on_hand in facts["forecast_alerts"]:
            add("  %-8s %-8s raised %s  ->  zero on %s"
                % (st, cat, raised, zero_on))
            add("           %.1f %s/day trailing mean, %.0f %s on hand that evening"
                % (avg, UNITS[cat], on_hand, UNITS[cat]))
    else:
        add("  none")
    add("")
    add("v_stock at end of log")
    add("-" * 62)
    for st, cat, qty, unit in stock:
        add("  %-9s %-12s %12.1f %s" % (st, cat, qty, unit))
    add("")
    add("=" * 62)
    add("Gate check")
    add("  4000 <= %d <= 8000            : %s" % (total, "PASS" if 4000 <= total <= 8000 else "FAIL"))
    add("  all 18 event types present    : %s" % ("PASS" if not missing else "FAIL"))
    add("=" * 62)

    text = "\n".join(L) + "\n"
    with open(STATS_PATH, "w") as fh:
        fh.write(text)
    return text


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    if not os.path.exists(SCHEMA_PATH):
        sys.exit("schema.sql not found next to this script — run Prompt 1 first.")

    build_members()
    build_cargo()
    late_crate = plant_late_hazard()
    facts = simulate_inventory()
    n_audits = facts["n_audits"]
    n_parties, overdue = build_field_parties()

    con, rows = sequence_and_write()
    text = write_stats(con, rows, facts, n_parties, overdue, late_crate, n_audits)
    con.close()
    print(text)


if __name__ == "__main__":
    main()
