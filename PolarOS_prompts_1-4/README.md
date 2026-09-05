# PolarOS — Prompts 1–4, built and verified

Reference implementation of the first four prompts in the pack. Everything here
was generated, run, and checked; every acceptance gate in the pack passes.

Use it the way the pack intends: as the thing you check the students' output
against, and as the source of the numbers the deck gets regenerated from.

---

## THE NUMBERS THE DECK NEEDS (Gate 1 condition)

| Deck currently says | Replace with | Where it comes from |
|---|---|---|
| "5,439 events" | **4,625 events** | `season_stats.txt`, TOTAL EVENTS |
| "2 Oct" | **2 Oct 2027** | `q_burnrate.sql`, MAITRI diesel, forecast as of 15 Sep 2027 |

Two numbers worth adding, because they are stronger than either of the above:

- **The alert fired on 29 March 2027** — 190 days before the tank would have
  run dry. Not a screen that goes red at the last minute; a warning with two
  seasons of lead time.
- **The forecast tightened as evidence arrived**: 26 Oct in March, 27 Sep by
  July, 2 Oct by mid-September. Actual crossing (with the airlift removed):
  5 Oct. That convergence is the single most persuasive exhibit in the project,
  and `check_gates.py` prints the table.

---

## Run it

```bash
sqlite3 --version          # any 3.38+; json_extract must be present
python3 --version          # 3.8+; stdlib only, nothing to install

python3 generate_season.py     # -> season.db, season_stats.txt
python3 measure_bandwidth.py   # -> bandwidth.md + two sample deltas
bash    run_queries.sh         # the three proof queries, in order
python3 check_gates.py         # every acceptance gate, mechanically
```

The hand-written fixture, independent of the generator:

```bash
sqlite3 sample.db < schema.sql
sqlite3 sample.db < sample_data.sql
sqlite3 sample.db < verify.sql
```

---

## Files

| File | Prompt | What it is |
|---|---|---|
| `schema.sql` | 1 | One table, 18 verbs, four replay views, append-only enforced by trigger |
| `sample_data.sql` | 1 | 17 hand-written events, staged so the audit re-base is visible |
| `verify.sql` | 1 | Runs all four views and asserts the answers |
| `generate_season.py` | 2 | Seeded simulation of one full season |
| `season_stats.txt` | 2 | The generation report — regenerate the deck from this, never by hand |
| `q_burnrate.sql` | 3 | Stock, 28-day burn rate, projected zero-date, RED/GREEN |
| `q_crate_trace.sql` | 3 | One crate's custody chain + the season-wide DG compliance check |
| `q_open_parties.sql` | 3 | Who is outside, and how late, at any instant you name |
| `measure_bandwidth.py` | 4 | Weighs real sync deltas against a real link budget |
| `bandwidth.md` | 4 | The measurement report |
| `check_gates.py` | — | 27 assertions covering every gate in the pack |
| `run_queries.sh` | — | Runs the three proof queries with the demo parameters |

---

## Gate results

**Prompt 1** — all four views correct on the hand-written fixture; a
`STOCK_COUNTED` insert visibly re-bases `v_stock` from 750 L to 650 L (and
*not* to 700 L, which is what a re-base that double-counts would give).
`UPDATE` and `DELETE` on `events` are both rejected by the database itself.

**Prompt 2** — two runs produce a byte-identical `season_stats.txt` *and* a
byte-identical `season.db`. All 18 types appear. 4,625 events, inside the
4,000–8,000 band. 400 manifest lines, category mix exact to the brief
(food 35.0%, fuel 20.0%, spares 20.0%, scientific 15.0%, medical 5.0%,
misc 5.0%), hazard rate 7.8%, 5.01 movement events per crate (min 4, max 6).
35 members with three clearances each; roster settles to 7 Maitri / 5 Bharati.

**Prompt 3** — Maitri diesel RED with a 2 Oct 2027 zero-date, Bharati diesel
GREEN, RED rows ordered first. The January overdue party reproduces exactly
when the clock is wound back to it, and disappears six hours later — same
query, same log, different question.

**Prompt 4** — `bandwidth.md` reads as a measurement report. Average
winter day: 218 B gzipped, 1.2 s of airtime against a 900 s window.
Busiest node-day in the entire season (offload day, 198 events): 2,321 B,
12.9 s. Maitri's *whole season* compresses to 16.6 kB — 10.2% of one
window — which closes the backlog question without needing a table.

---

## Three things to understand before you defend this

**1. `:as_of` is the whole argument.** Because state is replayed rather than
stored, any view can be evaluated at any past instant by refusing to look at
events after it. `q_burnrate.sql` run as of 15 September is genuinely blind to
the airlift that arrives on 3 October — not because we filtered it out for the
demo, but because an append-only log cannot see its own future. That is why the
forecast on the screen is the forecast the duty officer would really have had.
`check_gates.py` asserts that the same query with a far-future `:as_of` returns
*exactly* what `v_stock` returns, to the decimal.

**2. The system refuses to forecast across a regime change.** The 28-day
trailing mean is only computed once the whole window sits inside the
winter-over. A window straddling de-induction averages 22 people against 7 and
would flag every category in January. That guard is why the season produces
**one** burn-rate alert instead of two hundred. If a judge asks about false
positives, this is the answer, and it is in the code, not the deck.

**3. Compression improves with backlog.** The 339 daily blobs sum to 86 kB;
the same events compressed as one blob are 16.6 kB. Event logs are enormously
repetitive — the same 18 type strings, node ids and JSON keys, over and over —
so a node that has been offline for a month sends proportionally *less* than
one that syncs daily. That is the opposite of what people expect, and it is
worth saying out loud.

---

## Honest limitations — say these before a judge finds them

- **The sync protocol itself is not implemented.** The schema is built for it
  (per-node `seq`, deterministic `event_id`, priority column) and the bandwidth
  report measures what it would send, but no two nodes have actually exchanged
  a delta. That is the obvious next prompt.
- **Conflict resolution is asserted, not stress-tested.** Last-writer-wins on
  `(ts, event_id)` is deterministic by construction, but nobody has run two
  divergent replicas and compared them. Worth building: it is a 40-line test
  and it converts the strongest claim in the deck from argument to evidence.
- **The consumption model is plausible, not sourced.** 3.1 kg of food per
  person per day and Maitri's 88 L base hotel load are reasonable figures, not
  NCPOR figures. If anyone on the team can get real ones, substitute them — the
  constants are all at the top of `generate_season.py` and nothing else changes.
- **2.4 kbps is a nameplate rate.** The report applies a 60% goodput haircut and
  says so. Nobody has tested a real Iridium session.
- **Journal mode is probed, not assumed.** Running from a synced or
  sandboxed folder (Dropbox, OneDrive, a VM mount) can forbid file deletion,
  which breaks both WAL and DELETE journalling with a bare "disk I/O error"
  that looks like corruption. `generate_season.py` tries WAL, then TRUNCATE,
  then PERSIST, committing a real row in each, and says which it settled on.
  This was found by running the pack from a mounted Downloads folder — worth
  knowing before a teammate loses an evening to it.
- **`json_extract` is used throughout.** It is core SQLite since 3.38, not an
  extension, but it is worth checking on the judging machine:
  `SELECT json_valid('{}');` should return 1.

---

## Where the drama lives, for the demo script (Prompt 7)

| Beat | Where it is in the data |
|---|---|
| Hazardous crate declared late | `CR-0005`, packed 10 Oct, declared 19 Oct — 223 hours, after it left Goa |
| Diesel loaded short | `MAITRI_DIESEL_SHORTFALL_PCT = 0.15` in `generate_season.py`; set it to 0.0 and the crisis vanishes |
| Forecast catches it | `ALERT_RAISED` / `BURN_RATE` on Maitri diesel, 29 Mar 2027 |
| Forecast tightens | the sweep table in `check_gates.py` |
| Field party overdue | `FP-07`, Bharati, departed 25 Jan 07:00Z, ETA 18:00Z, home at 00:00Z — six hours late |
| The system worked | emergency airlift 3 Oct, two days before the counterfactual crossing on 5 Oct |
