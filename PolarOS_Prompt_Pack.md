# PolarOS — Prompt Pack (run in order, one at a time)
**Mentor's note to team:** These are copy-paste prompts for Claude (or any coding AI). Rules of use:
1. Run them **in order** — each builds on the previous output.
2. Start each prompt in a **fresh chat**, and paste in the files it asks for as context. Don't assume the AI remembers.
3. **You are the engineer, the AI is the intern.** Read every line it produces; run it yourself; if you can't explain a line in Q&A, delete it or learn it.
4. Whatever the code actually outputs becomes the truth for the deck. Never edit numbers by hand.

---

## PROMPT 1 — Schema (Owner: C)

> I'm building "PolarOS" for Smart India Hackathon PS SIH26062 — an offline-first logistics system for India's Antarctic expeditions (NCPOR). Architecture: one append-only event log, synced between disconnected nodes (GOA HQ, VESSEL, MAITRI, BHARATI, SANDHI stations). State is never stored — it's computed by replaying events.
>
> Write `schema.sql` for SQLite with:
> 1. One table `events(event_id TEXT PK, node_id TEXT, seq INTEGER, ts TEXT, priority INTEGER, type TEXT, subject TEXT, payload TEXT)` with UNIQUE(node_id, seq). priority: 1=safety, 2=personnel, 3=cargo, 4=inventory, 5=admin.
> 2. A CHECK or documented convention restricting `type` to exactly these 18: MANIFEST_CREATED, CRATE_PACKED, CRATE_SCANNED, CUSTODY_TRANSFERRED, HAZARD_DECLARED, LOT_DISPATCHED, LOT_SAILED, MEMBER_REGISTERED, CLEARANCE_RECORDED, MEMBER_MOVED, PARTY_DEPARTED, PARTY_RETURNED, PARTY_OVERDUE, STOCK_RECEIVED, STOCK_CONSUMED, STOCK_COUNTED, SOP_TRIGGERED, ALERT_RAISED.
> 3. Four VIEWS computed only from events: `v_stock` (per station × item category: received − consumed, re-based at the most recent STOCK_COUNTED audit for that station+category), `v_crate_location` (last scan/custody event per crate), `v_roster` (last MEMBER_MOVED location per person), `v_open_parties` (PARTY_DEPARTED without matching PARTY_RETURNED).
> 4. Comments on every view explaining the replay logic.
> Constraints: pure SQLite (no extensions), no UPDATE/DELETE anywhere in the design — corrections are new events. Also give me 10 hand-written sample INSERTs that exercise every view, and the SELECTs to verify them.

**Accept when:** views return correct results on the 10 samples; a STOCK_COUNTED insert visibly re-bases v_stock.

---

## PROMPT 2 — Season generator (Owner: E, pair with C)

> Context: paste `schema.sql` from Prompt 1. Same project (PolarOS, SIH26062).
>
> Write `generate_season.py` (Python 3, stdlib + sqlite3 only, fixed random seed, deterministic) that fabricates one full Indian Antarctic expedition season into `season.db`:
> - Timeline: Lot 1 (equipment) leaves GOA mid-Oct; Lot 2 (station spares) sails 22 Oct; Lot 3 (food/provisions) sails 25 Nov; vessel at Maitri anchorage late Dec, Bharati mid-Jan; field season Dec–Feb; winter-over 1 Mar–30 Nov with 7 members at MAITRI, 5 at BHARATI.
> - ~400 manifest lines across the lots. Category mix: food 35%, fuel 20% (Jet A1 + diesel), spares 20%, scientific 15%, medical 5%, misc 5%. Each line: weight_kg, volume_m3, hazard flag (~8%), destination, needed_by.
> - Every crate: 4–6 CRATE_SCANNED/CUSTODY_TRANSFERRED events along GOA → MUMBAI → CAPETOWN → VESSEL → station.
> - 35 members: MEMBER_REGISTERED + CLEARANCE_RECORDED (medical, training, passport) + MEMBER_MOVED chain; 23 summer members de-inducted by Feb.
> - Daily STOCK_CONSUMED per station per category through winter-over, scaled to headcount, ±10% noise, +25% diesel uplift Jun–Aug.
> - Planted drama: (a) MAITRI diesel loaded ~15% short so the projection crosses zero in early October — expose the shortfall as a tunable constant; (b) one BHARATI field party in January overdue by 6h → PARTY_OVERDUE then PARTY_RETURNED; (c) one hazardous crate gets HAZARD_DECLARED only after CRATE_PACKED.
> - Ends by printing: total events, events per node, per type — and writes the same to `season_stats.txt`.
> Style: small functions, no classes needed, heavy comments — a 3rd-year student must be able to walk a judge through it.

**Accept when:** two runs give identical `season_stats.txt`; all 18 types appear; count is in the 4,000–8,000 range. **Then update the deck's "5,439 events" to the real number.**

---

## PROMPT 3 — The three proof queries (Owner: C)

> Context: paste `schema.sql` + `season_stats.txt`; attach or describe `season.db` from Prompt 2.
>
> Write three standalone SQL files against my events table:
> 1. `q_burnrate.sql` — per station × category: current stock (from v_stock), trailing 28-day average daily consumption, projected zero-stock date, next resupply date (parameter — default 15 Dec), status RED if zero-date < resupply else GREEN. Order RED first.
> 2. `q_crate_trace.sql` — for a :crate_id parameter: full chronological custody chain (node, ts, event type, location from payload).
> 3. `q_open_parties.sql` — parties currently out: party_id, members, departed ts, ETA, minutes overdue (negative if not yet due).
> Also give me the one-line `sqlite3` shell commands to run each. Explain any date arithmetic — I must defend it in judging Q&A.

**Accept when:** q_burnrate shows the MAITRI diesel row RED with an early-October date and BHARATI GREEN; q_open_parties reproduces the January overdue party when run "as of" that timestamp. **Then update the deck's "2 Oct" to the real date.**

---

## PROMPT 4 — Bandwidth measurement (Owner: C)

> Context: same project; paste schema. I have `season.db`.
>
> Write `measure_bandwidth.py`: pick an average winter-over day for MAITRI, export that day's events as JSON (the exact delta a sync would send), report: event count, raw bytes, gzip bytes; then compute the ceiling of a 2.4 kbps × 15-minute Iridium window and print the margin. Also do the worst day. Write results to `bandwidth.md` as a small table with the arithmetic shown, so a judge can check it by hand.

**Accept when:** gzip size is comfortably under the window; `bandwidth.md` reads as a measurement report, not a claim.

---

## PROMPT 5 — Mockup brief for screens 1–5 (Owner: D; one prompt per screen is fine)

> I'm designing mobile-first mockup screens (360×760) for PolarOS — an offline-first PWA used at Indian Antarctic stations by non-technical staff wearing gloves, in low light. Design system: navy #0B3D66, ice #EAF2F8, red #B91C1C for alerts, green #14532D; min tap target 48px; max 2 actions per screen; every screen carries a sync chip showing either "OFFLINE — N events queued" or "Synced HH:MM".
>
> Screen to design now: [pick one]
> 1. SCAN CRATE — camera frame, crate id + contents + hazard badge + destination, one big CONFIRM HANDOVER.
> 2. STATION STOCK — category rows with qty and projected zero-date; RED rows first; a 2-minute daily consumption entry flow.
> 3. BURN-RATE FORECAST — one chart: stock declining to zero, resupply date marked, gap labelled in weeks. Here is the real query output to use for values: [paste q_burnrate result].
> 4. FIELD PARTIES — open parties with ETA countdown, one amber→red overdue, CHECK-IN button.
> 5. MEDEVAC CARD — nearest airstrip, flight window Y/N, ship distance, one-tap SOP; "works offline" stamp.
>
> Give me: a text wireframe (boxes/labels layout), the visual hierarchy top-to-bottom, exact copy for every label and button, empty/error/offline states, and what is deliberately left OUT and why. I will draw it in Figma myself — do not generate an image.

**Accept when:** a teammate who hasn't read the PS can look at the wireframe and say what question the screen answers.

---

## PROMPT 6 — HQ dashboard (Owner: D + B)

> Same design system as Prompt 5, but desktop (1440×900), user = NCPOR duty officer in Goa. Design the HQ DASHBOARD mockup: (a) a horizontal route strip Goa → Mumbai → Cape Town → Vessel → Maitri/Bharati/Sandhi with crate counts at each node, (b) per-node sync freshness ("MAITRI: last sync 22h ago"), (c) open alerts panel (RED burn-rate rows, overdue parties, hazard flags), (d) season countdown (days to next sailing / to winter-over). Text wireframe + label copy + hierarchy, same rules as before. Values must come from these query outputs: [paste].

---

## PROMPT 7 — Demo narration (Owner: F, after Gates 2–3)

> Here are our six mockup screens [attach images/wireframes] and our real query outputs [paste]. Write a 3-minute demo script (spoken word count ≤ 380) that walks a judge through one story: a barrel packed in Goa → scanned at Cape Town → link cut ("OFFLINE" chip) → station logs consumption → forecast screen shows MAITRI diesel crossing zero on [real date] vs ship on 15 Dec → a field party goes overdue → link restored → HQ dashboard shows everything, sync 'just now'. Mark [CLICK] cues, give exact first and last sentences, and include one deliberate 3-second pause on the forecast screen. Tone: calm, factual, zero buzzwords.

---

## PROMPT 8 — Red-team rehearsal (whole team, last)

> Here is our idea PPT text and our screens [paste]. Act as a hostile SIH jury with three members: an NCPOR operations officer, a distributed-systems professor, and a startup founder. Ask us the 15 hardest questions across feasibility, sync conflicts, adoption, synthetic-data realism, and solver claims — grouped by who asks. Don't answer them. After we reply in this chat, grade each answer harshly and show the stronger version.

---

### Sequencing map
Prompts 1→2→3→4 are strictly ordered (each consumes the previous artifact). Prompts 5/6 run in parallel after 3. Prompt 7 after screens exist. Prompt 8 in the final week. After Prompt 3, tell the mentor the real event count and zero-date so the deck gets regenerated — that update is a Gate 1 condition, not a formality.
