#!/usr/bin/env bash
# =====================================================================
#  PolarOS — run_queries.sh
#  Runs the three proof queries against season.db, in order.
#  Run:  bash run_queries.sh
#
#  The individual one-liners, if you want them separately:
#
#    sqlite3 season.db < q_burnrate.sql
#    sqlite3 season.db < q_crate_trace.sql
#    sqlite3 season.db < q_open_parties.sql
#
#  ...and with parameters:
#
#    sqlite3 season.db ".param set :as_of '2027-06-01T23:59:59Z'" \
#                      ".read q_burnrate.sql"
#    sqlite3 season.db ".param set :crate_id 'CR-0142'" \
#                      ".read q_crate_trace.sql"
#    sqlite3 season.db ".param set :as_of '2027-01-25T21:00:00Z'" \
#                      ".read q_open_parties.sql"
#
#  Gate assertions and the forecast-tightening sweep live in
#  check_gates.py — run that after this.
# =====================================================================
set -u
DB=${1:-season.db}

hr() { printf '\n======================================================================\n'; }

hr; echo "  1. BURN RATE — as of the demo moment (15 Sep 2027)"; hr
sqlite3 "$DB" < q_burnrate.sql

hr; echo "  2. CRATE TRACE — CR-0005, the late dangerous-goods declaration"; hr
sqlite3 "$DB" < q_crate_trace.sql

hr; echo "  3. OPEN PARTIES — 25 Jan 2027 21:00Z, three hours past ETA"; hr
sqlite3 "$DB" < q_open_parties.sql

hr; echo "  3b. OPEN PARTIES — same query six hours later; the party is home"; hr
sqlite3 "$DB" ".param set :as_of '2027-01-26T06:00:00Z'" ".read q_open_parties.sql"
